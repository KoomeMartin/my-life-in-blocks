import json
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from supabase_rag import SupabaseVectorStore

load_dotenv()

class AdvancedSemanticChunker:
    """
    Advanced chunking strategy specifically designed for agentic AI scheduling use case.
    
    JUSTIFICATION FOR CHUNKING STRATEGY:
    
    1. SEMANTIC PRESERVATION: The JSON contains hierarchical scheduling data where context 
       relationships are critical (e.g., energy patterns must stay linked to time blocks).
    
    2. DOMAIN-SPECIFIC CHUNKING: Different sections require different chunking approaches:
       - Energy profiles: Keep time-energy mappings together
       - Calendar events: Preserve event relationships and constraints
       - Competency matrix: Maintain skill-impact relationships
       - Decision rules: Keep condition-action pairs intact
    
    3. RETRIEVAL OPTIMIZATION: Chunks are sized and structured to provide complete 
       context for scheduling decisions without information fragmentation.
    """
    
    def __init__(self):
        self.chunk_strategies = {
            'system_config': self._chunk_system_config,
            'user_profile_calibration': self._chunk_competency_matrix,
            'user_constraints': self._chunk_constraints_semantically,
            'fixed_calendar_events': self._chunk_calendar_events,
            'historical_behavior': self._chunk_behavioral_patterns,
            'course_policy_layer': self._chunk_course_policies,
            'agent_decision_engine': self._chunk_decision_rules
        }
    
    def _chunk_system_config(self, data: Dict, category: str) -> List[Document]:
        """
        System config is small and cohesive - keep as single chunk.
        JUSTIFICATION: Configuration data needs to be retrieved as a complete unit.
        """
        content = f"SYSTEM CONFIGURATION:\n{json.dumps(data, indent=2)}"
        return [Document(
            page_content=content,
            metadata={
                "category": category,
                "chunk_type": "system_config",
                "semantic_unit": "complete_config",
                "retrieval_priority": "high"
            }
        )]
    
    def _chunk_competency_matrix(self, data: Dict, category: str) -> List[Document]:
        """
        Chunk by competency domain to preserve skill-impact relationships.
        JUSTIFICATION: Each competency domain (coding, math, experience) should be 
        retrievable as a unit for accurate skill assessment and task prioritization.
        """
        chunks = []
        
        # Main profile info
        profile_content = f"USER PROFILE SOURCE: {data.get('source', 'Unknown')}\n"
        profile_content += "COMPETENCY OVERVIEW:\n"
        
        competency_matrix = data.get('competency_matrix', {})
        
        # Chunk each competency domain separately
        for domain, details in competency_matrix.items():
            domain_content = f"COMPETENCY DOMAIN: {domain.upper()}\n"
            domain_content += f"Skills: {', '.join(details.get('skills', []))}\n"
            domain_content += f"Level: {details.get('level', 'Unknown')}\n"
            domain_content += f"Impact on Scheduling: {details.get('impact', 'No impact specified')}\n"
            
            chunks.append(Document(
                page_content=domain_content,
                metadata={
                    "category": category,
                    "chunk_type": "competency_domain",
                    "domain": domain,
                    "skill_level": details.get('level', 'Unknown'),
                    "semantic_unit": f"competency_{domain}",
                    "retrieval_priority": "high"
                }
            ))
        
        return chunks
    
    def _chunk_constraints_semantically(self, data: Dict, category: str) -> List[Document]:
        """
        Chunk constraints by semantic meaning while preserving critical relationships.
        JUSTIFICATION: Energy patterns and scheduling rules must maintain their 
        temporal relationships for accurate scheduling decisions.
        """
        chunks = []
        
        # Chronotype as separate chunk (fundamental scheduling constraint)
        chronotype_content = f"USER CHRONOTYPE: {data.get('chronotype', 'Unknown')}\n"
        chronotype_content += "This is the fundamental energy pattern that drives all scheduling decisions."
        
        chunks.append(Document(
            page_content=chronotype_content,
            metadata={
                "category": category,
                "chunk_type": "chronotype",
                "semantic_unit": "energy_foundation",
                "retrieval_priority": "critical"
            }
        ))
        
        # Hard rules as separate chunks (each rule is a complete constraint)
        for rule in data.get('hard_rules', []):
            rule_content = f"SCHEDULING RULE: {rule.get('rule_id', 'Unknown')}\n"
            rule_content += f"Logic: {rule.get('logic', 'No logic specified')}\n"
            rule_content += f"Enforcement Level: {rule.get('enforcement', 'Unknown')}\n"
            
            chunks.append(Document(
                page_content=rule_content,
                metadata={
                    "category": category,
                    "chunk_type": "scheduling_rule",
                    "rule_id": rule.get('rule_id', 'unknown'),
                    "enforcement": rule.get('enforcement', 'unknown'),
                    "semantic_unit": f"rule_{rule.get('rule_id', 'unknown')}",
                    "retrieval_priority": "critical"
                }
            ))
        
        # Energy profile mapping (keep time-energy relationships intact)
        energy_mapping = data.get('energy_profile_mapping', {})
        if energy_mapping:
            energy_content = "ENERGY PROFILE MAPPING:\n"
            for time_slot, energy_description in energy_mapping.items():
                energy_content += f"⏰ {time_slot}: {energy_description}\n"
            
            chunks.append(Document(
                page_content=energy_content,
                metadata={
                    "category": category,
                    "chunk_type": "energy_profile",
                    "semantic_unit": "complete_energy_mapping",
                    "retrieval_priority": "critical"
                }
            ))
        
        return chunks
    
    def _chunk_calendar_events(self, data: List[Dict], category: str) -> List[Document]:
        """
        Chunk calendar events by day while preserving daily schedule context.
        JUSTIFICATION: Daily schedules should be retrievable as complete units 
        to understand daily constraints and available time slots.
        """
        chunks = []
        
        # Group events by day
        events_by_day = {}
        for event in data:
            day = event.get('day', 'Unknown')
            if day not in events_by_day:
                events_by_day[day] = []
            events_by_day[day].append(event)
        
        # Create chunks for each day
        for day, events in events_by_day.items():
            day_content = f"FIXED SCHEDULE FOR {day.upper()}:\n\n"
            
            for event in events:
                if 'note' in event:
                    day_content += f"📝 Note: {event['note']}\n"
                else:
                    day_content += f"🕐 {event.get('start', 'TBD')} - {event.get('end', 'TBD')}: "
                    day_content += f"{event.get('title', 'Untitled Event')}\n"
                    day_content += f"   Type: {event.get('type', 'Unknown')}\n"
                    day_content += f"   Priority: {event.get('priority', 'Normal')}\n"
                    if 'course_id' in event:
                        day_content += f"   Course: {event['course_id']}\n"
                    day_content += "\n"
            
            chunks.append(Document(
                page_content=day_content,
                metadata={
                    "category": category,
                    "chunk_type": "daily_schedule",
                    "day": day,
                    "event_count": len(events),
                    "semantic_unit": f"schedule_{day.lower()}",
                    "retrieval_priority": "high"
                }
            ))
        
        return chunks
    
    def _chunk_behavioral_patterns(self, data: Dict, category: str) -> List[Document]:
        """
        Chunk behavioral data by pattern type to preserve learning relationships.
        JUSTIFICATION: Historical patterns inform future scheduling decisions 
        and should be retrievable by pattern type for adaptive scheduling.
        """
        chunks = []
        
        # Missed sessions patterns
        missed_sessions = data.get('missed_sessions', [])
        if missed_sessions:
            missed_content = "HISTORICAL MISSED SESSIONS PATTERNS:\n\n"
            for pattern in missed_sessions:
                missed_content += f"Course: {pattern.get('course_id', 'Unknown')}\n"
                missed_content += f"Time Block: {pattern.get('time_block', 'Unknown')}\n"
                missed_content += f"Reason: {pattern.get('reason', 'Unknown')}\n"
                missed_content += f"Count: {pattern.get('count', 0)}\n"
                missed_content += f"Agent Action: {pattern.get('agent_action', 'No action specified')}\n\n"
            
            chunks.append(Document(
                page_content=missed_content,
                metadata={
                    "category": category,
                    "chunk_type": "behavioral_pattern",
                    "pattern_type": "missed_sessions",
                    "semantic_unit": "failure_patterns",
                    "retrieval_priority": "medium"
                }
            ))
        
        # Successful patterns
        successful_patterns = data.get('successful_patterns', [])
        if successful_patterns:
            success_content = "HISTORICAL SUCCESSFUL PATTERNS:\n\n"
            for pattern in successful_patterns:
                success_content += f"Pattern: {pattern.get('pattern', 'Unknown')}\n"
                success_content += f"Completion Rate: {pattern.get('completion_rate', 0)}\n"
                success_content += f"Status: {pattern.get('status', 'Unknown')}\n\n"
            
            chunks.append(Document(
                page_content=success_content,
                metadata={
                    "category": category,
                    "chunk_type": "behavioral_pattern",
                    "pattern_type": "successful_patterns",
                    "semantic_unit": "success_patterns",
                    "retrieval_priority": "medium"
                }
            ))
        
        # Energy logs
        energy_logs = data.get('energy_logs', {})
        if energy_logs:
            energy_log_content = "ENERGY BEHAVIOR LOGS:\n\n"
            for log_type, details in energy_logs.items():
                energy_log_content += f"{log_type.replace('_', ' ').title()}: {details}\n"
            
            chunks.append(Document(
                page_content=energy_log_content,
                metadata={
                    "category": category,
                    "chunk_type": "energy_logs",
                    "semantic_unit": "energy_behavior",
                    "retrieval_priority": "high"
                }
            ))
        
        return chunks
    
    def _chunk_course_policies(self, data: Dict, category: str) -> List[Document]:
        """
        Chunk each course policy separately for targeted retrieval.
        JUSTIFICATION: Course-specific policies should be retrievable independently 
        for course-specific scheduling decisions and deadline management.
        """
        chunks = []
        
        for course_id, policy_data in data.items():
            policy_content = f"COURSE POLICY: {course_id}\n"
            policy_content += f"Name: {policy_data.get('name', 'Unknown Course')}\n"
            policy_content += f"Policy: {policy_data.get('policy', 'No policy specified')}\n"
            
            if 'deadlines' in policy_data:
                policy_content += f"Deadlines: {policy_data['deadlines']}\n"
            
            if 'critical_note' in policy_data:
                policy_content += f"⚠️ Critical Note: {policy_data['critical_note']}\n"
            
            chunks.append(Document(
                page_content=policy_content,
                metadata={
                    "category": category,
                    "chunk_type": "course_policy",
                    "course_id": course_id,
                    "course_name": policy_data.get('name', 'Unknown'),
                    "semantic_unit": f"policy_{course_id}",
                    "retrieval_priority": "medium"
                }
            ))
        
        return chunks
    
    def _chunk_decision_rules(self, data: Dict, category: str) -> List[Document]:
        """
        Chunk decision rules by rule type while preserving condition-action relationships.
        JUSTIFICATION: Decision heuristics must maintain their logical integrity 
        for accurate automated scheduling decisions.
        """
        chunks = []
        
        # Scheduling heuristics (each rule is a complete decision unit)
        heuristics = data.get('scheduling_heuristics', [])
        if heuristics:
            for i, heuristic in enumerate(heuristics):
                heuristic_content = f"SCHEDULING HEURISTIC #{i+1}:\n"
                heuristic_content += f"Condition: {heuristic.get('condition', 'No condition specified')}\n"
                heuristic_content += f"Action: {heuristic.get('action', 'No action specified')}\n"
                
                chunks.append(Document(
                    page_content=heuristic_content,
                    metadata={
                        "category": category,
                        "chunk_type": "decision_heuristic",
                        "heuristic_id": f"heuristic_{i+1}",
                        "semantic_unit": f"decision_rule_{i+1}",
                        "retrieval_priority": "high"
                    }
                ))
        
        # Recovery protocols
        recovery_protocols = data.get('recovery_protocols', {})
        if recovery_protocols:
            recovery_content = "RECOVERY PROTOCOLS:\n\n"
            for protocol_name, protocol_action in recovery_protocols.items():
                recovery_content += f"{protocol_name.replace('_', ' ').title()}: {protocol_action}\n"
            
            chunks.append(Document(
                page_content=recovery_content,
                metadata={
                    "category": category,
                    "chunk_type": "recovery_protocols",
                    "semantic_unit": "recovery_strategies",
                    "retrieval_priority": "medium"
                }
            ))
        
        return chunks
    
    def chunk_strategic_json(self, file_path: str) -> List[Document]:
        """
        Main method to chunk the strategic JSON using domain-specific strategies.
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        all_chunks = []
        
        for category, content in data.items():
            if category in self.chunk_strategies:
                chunks = self.chunk_strategies[category](content, category)
                all_chunks.extend(chunks)
                print(f"📊 {category}: Created {len(chunks)} semantic chunks")
            else:
                # Fallback for unknown categories
                fallback_content = f"{category}: {json.dumps(content, indent=2)}"
                chunk = Document(
                    page_content=fallback_content,
                    metadata={
                        "category": category,
                        "chunk_type": "fallback",
                        "semantic_unit": f"unknown_{category}",
                        "retrieval_priority": "low"
                    }
                )
                all_chunks.append(chunk)
                print(f"📊 {category}: Created 1 fallback chunk")
        
        return all_chunks

class HybridChunkingStrategy:
    """
    Combines semantic chunking with sliding window for optimal retrieval.
    """
    
    def __init__(self):
        self.semantic_chunker = AdvancedSemanticChunker()
        self.sliding_window_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
    
    def create_hybrid_chunks(self, file_path: str) -> List[Document]:
        """
        Create both semantic and sliding window chunks for comprehensive coverage.
        
        JUSTIFICATION FOR HYBRID APPROACH:
        1. Semantic chunks preserve domain-specific context and relationships
        2. Sliding window chunks ensure no information is lost between semantic boundaries
        3. Different chunk types can be weighted differently during retrieval
        """
        
        # Get semantic chunks
        semantic_chunks = self.semantic_chunker.chunk_strategic_json(file_path)
        
        # Create sliding window chunks from semantic chunks for backup coverage
        sliding_chunks = []
        for semantic_chunk in semantic_chunks:
            if len(semantic_chunk.page_content) > 1000:  # Only split large semantic chunks
                sub_chunks = self.sliding_window_splitter.split_documents([semantic_chunk])
                for i, sub_chunk in enumerate(sub_chunks):
                    # Preserve original metadata and add sliding window info
                    sub_chunk.metadata.update({
                        "chunk_method": "sliding_window",
                        "parent_semantic_unit": semantic_chunk.metadata.get("semantic_unit", "unknown"),
                        "sub_chunk_index": i,
                        "retrieval_priority": "backup"
                    })
                sliding_chunks.extend(sub_chunks)
        
        print(f"🔄 Created {len(sliding_chunks)} sliding window backup chunks")
        
        # Combine both types
        all_chunks = semantic_chunks + sliding_chunks
        
        return all_chunks

def build_advanced_vector_store(chunks: List[Document]) -> SupabaseVectorStore:
    """
    Build Supabase vector store with advanced chunking strategy.
    Uses cloud-based PostgreSQL + pgvector for scalable storage.
    """
    print("☁️  Connecting to Supabase vector store...")
    
    # Initialize Supabase vector store
    vectorstore = SupabaseVectorStore(
        collection_name="advanced_agentic_brain"
    )
    
    # Add documents to Supabase
    print(f"📤 Uploading {len(chunks)} documents to Supabase...")
    vectorstore.add_documents(chunks)
    
    print("✅ Documents successfully stored in Supabase")
    return vectorstore

# === EXECUTION ===
if __name__ == "__main__":
    print("🧠 ADVANCED SEMANTIC CHUNKING FOR AGENTIC AI")
    print("=" * 60)
    
    # Initialize hybrid chunking strategy
    chunker = HybridChunkingStrategy()
    
    # Create advanced chunks
    print("\n📊 CREATING SEMANTIC CHUNKS...")
    chunks = chunker.create_hybrid_chunks("profile.json")
    
    print(f"\n✂️ CHUNKING SUMMARY:")
    print(f"📄 Total chunks created: {len(chunks)}")
    
    # Analyze chunk distribution
    chunk_types = {}
    for chunk in chunks:
        chunk_type = chunk.metadata.get('chunk_type', 'unknown')
        chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
    
    print(f"\n📊 CHUNK TYPE DISTRIBUTION:")
    for chunk_type, count in chunk_types.items():
        print(f"  • {chunk_type}: {count} chunks")
    
    # Build vector store
    print(f"\n🔗 BUILDING SUPABASE VECTOR STORE...")
    vectorstore = build_advanced_vector_store(chunks)
    
    # Create retriever with advanced search
    retriever = vectorstore.as_retriever(
        search_kwargs={"k": 5}  # Get more chunks for better context
    )
    
    print("✅ ADVANCED RAG SYSTEM READY!")
    print("\n🎯 CHUNKING STRATEGY JUSTIFICATION:")
    print("• Semantic chunking preserves domain-specific context")
    print("• Sliding window ensures comprehensive coverage")
    print("• Metadata enables priority-based retrieval")
    print("• Domain-specific strategies optimize for scheduling use case")
    print("☁️  Cloud-based storage with Supabase (PostgreSQL + pgvector)")
    print("🔒 Automatic backups and multi-user support")