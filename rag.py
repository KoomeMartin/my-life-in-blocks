import json
import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter # <--- NEW IMPORT

load_dotenv()

# 1. Load the JSON "Brain"
def load_strategic_json(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    documents = []
    for key, value in data.items():
        # Convert to string
        content = json.dumps(value, indent=2)
        doc = Document(
            page_content=f"{key}: {content}",
            metadata={"category": key, "source": "profile"}
        )
        documents.append(doc)
    return documents

# 2. SPLIT the Documents (The New Layer)
def split_documents(docs):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,       # Characters per chunk
        chunk_overlap=200,     # Overlap to preserve context between chunks
        separators=["\n\n", "\n", "},", "],", " ", ""] # Smart splitters for JSON
    )
    return text_splitter.split_documents(docs)

# 3. Initialize Vector Store
def build_vector_store(splits):
    return Chroma.from_documents(
        documents=splits,
        collection_name="agentic_career_brain",
        embedding=OpenAIEmbeddings(),
        persist_directory="./chroma_db"
    )

# --- EXECUTION FLOW ---

# A. Load Raw Docs
raw_docs = load_strategic_json("profile.json")
print(f"📄 Loaded {len(raw_docs)} parent documents.")

# B. Split into Chunks
final_splits = split_documents(raw_docs)
print(f"✂️  Split into {len(final_splits)} granular chunks for better retrieval.")

# C. Index
vectorstore = build_vector_store(final_splits)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

print("✅ Knowledge Base Indexed & Ready!")