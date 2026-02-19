#!/usr/bin/env python3
"""
Supabase RAG Implementation

Replaces ChromaDB with Supabase PostgreSQL + pgvector for vector storage and retrieval.
"""

import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class SupabaseVectorStore:
    """Vector store implementation using Supabase pgvector"""
    
    def __init__(self, collection_name: str = "default"):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')  # Use anon key for app
        self.openai_key = os.getenv('OPENAI_API_KEY')
        
        if not all([self.supabase_url, self.supabase_key, self.openai_key]):
            raise ValueError("Missing required environment variables")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.embeddings = OpenAIEmbeddings(openai_api_key=self.openai_key)
        self.collection_name = collection_name
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """
        Perform similarity search using pgvector.
        
        Args:
            query: Search query text
            k: Number of results to return
            filter_dict: Optional metadata filters
        
        Returns:
            List of Document objects with content and metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Build RPC call for similarity search
            # Note: This requires a custom RPC function in Supabase
            rpc_params = {
                'query_embedding': query_embedding,
                'match_count': k,
                'match_collection_name': self.collection_name
            }
            
            # Add metadata filters if provided
            if filter_dict:
                rpc_params['filter_metadata'] = filter_dict
            
            # Call RPC function
            result = self.supabase.rpc('match_semantic_memory', rpc_params).execute()
            
            # Convert to Document objects
            documents = []
            for row in result.data:
                doc = Document(
                    page_content=row['content'],
                    metadata=row.get('metadata', {})
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Similarity search error: {e}")
            # Fallback to basic query if RPC not available
            return self._fallback_search(query, k, filter_dict)
    
    def _fallback_search(
        self,
        query: str,
        k: int = 4,
        filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """
        Fallback search using basic text matching when RPC function is not available.
        This is less accurate than vector similarity but provides basic functionality.
        """
        logger.warning("⚠️  Using fallback search - RPC function 'match_semantic_memory' not found")
        logger.warning("⚠️  Run 'complete_memory_schema.sql' in Supabase SQL Editor to create the RPC function")
        
        try:
            # Split query into keywords for better matching
            keywords = query.lower().split()
            
            # Build query with multiple keyword matches
            query_builder = self.supabase.table('semantic_memory') \
                .select('content, metadata') \
                .eq('collection_name', self.collection_name)
            
            # Try to match any of the keywords
            if keywords:
                # Use OR logic for multiple keywords
                or_conditions = ' OR '.join([f'content.ilike.%{kw}%' for kw in keywords[:5]])  # Limit to 5 keywords
                query_builder = query_builder.or_(or_conditions)
            
            # Apply metadata filters if provided
            if filter_dict:
                for key, value in filter_dict.items():
                    query_builder = query_builder.eq(f'metadata->{key}', value)
            
            # Order by importance score and limit results
            result = query_builder.order('importance_score', desc=True).limit(k).execute()
            
            documents = []
            for row in result.data:
                doc = Document(
                    page_content=row['content'],
                    metadata=row.get('metadata', {})
                )
                documents.append(doc)
            
            if documents:
                logger.info(f"✅ Fallback search returned {len(documents)} results")
            else:
                logger.warning("⚠️  Fallback search returned no results")
            
            return documents
            
        except Exception as e:
            logger.error(f"❌ Fallback search error: {e}")
            return []
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to Supabase"""
        try:
            rows = []
            for doc in documents:
                # Generate embedding
                embedding = self.embeddings.embed_query(doc.page_content)
                
                # Calculate importance score
                priority_map = {'critical': 1.0, 'high': 0.8, 'medium': 0.5, 'low': 0.3}
                priority = doc.metadata.get('retrieval_priority', 'medium').lower()
                importance_score = priority_map.get(priority, 0.5)
                
                row = {
                    'collection_name': self.collection_name,
                    'content': doc.page_content,
                    'embedding': embedding,
                    'metadata': doc.metadata,
                    'chunk_type': doc.metadata.get('chunk_type'),
                    'semantic_unit': doc.metadata.get('semantic_unit'),
                    'retrieval_priority': doc.metadata.get('retrieval_priority'),
                    'importance_score': importance_score
                }
                rows.append(row)
            
            result = self.supabase.table('semantic_memory').insert(rows).execute()
            return [row['id'] for row in result.data]
            
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return []
    
    def delete_collection(self):
        """Delete all documents in this collection"""
        try:
            self.supabase.table('semantic_memory') \
                .delete() \
                .eq('collection_name', self.collection_name) \
                .execute()
            logger.info(f"Deleted collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
    
    def as_retriever(self, search_kwargs: Optional[Dict] = None):
        """
        Return a retriever interface compatible with LangChain.
        
        Args:
            search_kwargs: Optional search parameters (k, filter, etc.)
        
        Returns:
            SupabaseRetriever instance
        """
        return SupabaseRetriever(
            vectorstore=self,
            search_kwargs=search_kwargs or {}
        )


class SupabaseRetriever:
    """LangChain-compatible retriever for SupabaseVectorStore"""
    
    def __init__(self, vectorstore: SupabaseVectorStore, search_kwargs: Dict):
        self.vectorstore = vectorstore
        self.search_kwargs = search_kwargs
    
    def get_relevant_documents(self, query: str, **kwargs) -> List[Document]:
        """Retrieve relevant documents for a query"""
        k = self.search_kwargs.get('k', 4)
        filter_dict = self.search_kwargs.get('filter')
        return self.vectorstore.similarity_search(query, k=k, filter_dict=filter_dict)
    
    def invoke(self, query: str, config: Optional[Dict] = None, **kwargs) -> List[Document]:
        """Invoke the retriever (LangChain interface)"""
        return self.get_relevant_documents(query)
    
    async def ainvoke(self, query: str, config: Optional[Dict] = None, **kwargs) -> List[Document]:
        """Async invoke (LangChain interface)"""
        return self.get_relevant_documents(query)


def create_supabase_rpc_function():
    """
    SQL function for vector similarity search.
    Run this in Supabase SQL Editor to enable similarity search.
    """
    sql = """
    CREATE OR REPLACE FUNCTION match_semantic_memory(
        query_embedding VECTOR(1536),
        match_count INT DEFAULT 4,
        collection_name TEXT DEFAULT NULL,
        filter_metadata JSONB DEFAULT NULL
    )
    RETURNS TABLE (
        id UUID,
        content TEXT,
        metadata JSONB,
        similarity FLOAT
    )
    LANGUAGE plpgsql
    AS $$
    BEGIN
        RETURN QUERY
        SELECT
            sm.id,
            sm.content,
            sm.metadata,
            1 - (sm.embedding <=> query_embedding) AS similarity
        FROM semantic_memory sm
        WHERE
            (collection_name IS NULL OR sm.collection_name = collection_name)
            AND (filter_metadata IS NULL OR sm.metadata @> filter_metadata)
        ORDER BY sm.embedding <=> query_embedding
        LIMIT match_count;
    END;
    $$;
    """
    
    print("=" * 80)
    print("NOTE: This RPC function is included in complete_memory_schema.sql")
    print("=" * 80)
    print("\nTo create the function:")
    print("1. Go to Supabase SQL Editor")
    print("2. Run complete_memory_schema.sql")
    print("\nAlternatively, run this SQL directly:")
    print(sql)
    print("\n" + "=" * 80)


# Compatibility layer for existing code
class SupabaseChroma:
    """Drop-in replacement for Chroma using Supabase"""
    
    def __init__(self, collection_name: str, embedding_function, persist_directory: str = None):
        self.vectorstore = SupabaseVectorStore(collection_name=collection_name)
        self.embedding_function = embedding_function
    
    def similarity_search(self, query: str, k: int = 4, filter: Dict = None) -> List[Document]:
        return self.vectorstore.similarity_search(query, k, filter)
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        return self.vectorstore.add_documents(documents)
    
    def delete_collection(self):
        return self.vectorstore.delete_collection()


if __name__ == "__main__":
    # Generate RPC function SQL
    create_supabase_rpc_function()
    
    # Test connection
    try:
        store = SupabaseVectorStore("test_collection")
        print("✅ Supabase connection successful")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
