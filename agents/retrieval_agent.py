"""
Agent 3: Retrieval Agent
This agent retrieves relevant chunks from both vector and relational databases
using hybrid search combining semantic similarity and keyword matching
"""
import os
import sys
from pathlib import Path
import numpy as np
from typing import List, Dict, Any, Tuple
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils import DatabaseManager, AWSBedrockClient

# Load environment variables
load_dotenv()


class RetrievalState(TypedDict):
    """State for retrieval workflow"""
    query: str
    query_embedding: List[float]
    text_results: List[Dict[str, Any]]
    image_results: List[Dict[str, Any]]
    table_results: List[Dict[str, Any]]
    all_results: List[Dict[str, Any]]
    top_k: int
    error: str


class RetrievalAgent:
    """
    Agent 3: Retrieval Agent
    Performs hybrid retrieval using vector similarity and keyword matching
    """
    
    def __init__(self, top_k: int = 10):
        """
        Initialize the Retrieval Agent
        
        Args:
            top_k: Number of top results to retrieve per chunk type
        """
        print("\n" + "=" * 80)
        print("🤖 INITIALIZING AGENT 3: RETRIEVAL AGENT")
        print("=" * 80 + "\n")
        
        self.top_k = top_k
        self.db_manager = DatabaseManager()
        self.aws_client = AWSBedrockClient()
        
        # Initialize database connection
        if self.db_manager.connect():
            print("✅ Database connection established")
        
        # Build LangGraph workflow
        self.workflow = self._build_workflow()
        
        print("✅ Retrieval Agent initialized successfully!\n")
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for retrieval"""
        workflow = StateGraph(RetrievalState)
        
        # Add nodes
        workflow.add_node("embed_query", self.embed_query)
        workflow.add_node("retrieve_text_chunks", self.retrieve_text_chunks)
        workflow.add_node("retrieve_image_chunks", self.retrieve_image_chunks)
        workflow.add_node("retrieve_table_chunks", self.retrieve_table_chunks)
        workflow.add_node("combine_results", self.combine_results)
        
        # Define edges
        workflow.set_entry_point("embed_query")
        workflow.add_edge("embed_query", "retrieve_text_chunks")
        workflow.add_edge("retrieve_text_chunks", "retrieve_image_chunks")
        workflow.add_edge("retrieve_image_chunks", "retrieve_table_chunks")
        workflow.add_edge("retrieve_table_chunks", "combine_results")
        workflow.add_edge("combine_results", END)
        
        return workflow.compile()
    
    def embed_query(self, state: RetrievalState) -> RetrievalState:
        """Generate embedding for the user query"""
        print("\n" + "-" * 80)
        print("🔤 STEP 1: EMBEDDING USER QUERY")
        print("-" * 80)
        
        query = state.get('query', '')
        
        if not query:
            print("⚠️ No query provided\n")
            state['query_embedding'] = []
            return state
        
        print(f"📝 Query: {query[:100]}{'...' if len(query) > 100 else ''}\n")
        
        # Generate embedding using Titan
        result = self.aws_client.get_titan_embeddings(query)
        
        if result['success']:
            state['query_embedding'] = result['embedding']
            print(f"✅ Generated {result['dimension']}-dimensional query embedding\n")
        else:
            print(f"❌ Failed to generate query embedding: {result.get('error', 'Unknown error')}\n")
            state['query_embedding'] = []
            state['error'] = result.get('error', 'Failed to embed query')
        
        return state
    
    def retrieve_text_chunks(self, state: RetrievalState) -> RetrievalState:
        """Retrieve relevant text chunks using vector similarity"""
        print("\n" + "-" * 80)
        print("📄 STEP 2: RETRIEVING RELEVANT TEXT CHUNKS")
        print("-" * 80)
        
        query_embedding = state.get('query_embedding', [])
        top_k = state.get('top_k', self.top_k)
        
        if not query_embedding:
            print("⚠️ No query embedding available\n")
            state['text_results'] = []
            return state
        
        try:
            # Vector similarity search using cosine similarity
            # Calculate: (embedding <#> query_embedding) as cosine_distance
            # Lower distance = higher similarity
            
            self.db_manager.cursor.execute("""
                SELECT 
                    chunk_id,
                    chunk_type,
                    section_id,
                    source_document,
                    content,
                    metadata,
                    embedding,
                    1 - (embedding <=> %s::vector) as similarity_score
                FROM text_chunks
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
            """, (query_embedding, query_embedding, top_k))
            
            rows = self.db_manager.cursor.fetchall()
            
            text_results = []
            for row in rows:
                text_results.append({
                    'chunk_id': row['chunk_id'],
                    'chunk_type': row['chunk_type'],
                    'section_id': row['section_id'],
                    'source_document': row['source_document'],
                    'content': row['content'],
                    'metadata': row['metadata'] if row['metadata'] else {},
                    'similarity_score': float(row['similarity_score']),
                    'retrieval_method': 'vector_similarity'
                })
            
            print(f"✅ Retrieved {len(text_results)} text chunks")
            if text_results:
                print(f"   Top similarity score: {text_results[0]['similarity_score']:.4f}")
                print(f"   Preview: {text_results[0]['content'][:100]}...\n")
            
            state['text_results'] = text_results
            
        except Exception as e:
            print(f"❌ Error retrieving text chunks: {str(e)}\n")
            state['text_results'] = []
            state['error'] = str(e)
        
        return state
    
    def retrieve_image_chunks(self, state: RetrievalState) -> RetrievalState:
        """Retrieve relevant image chunks using vector similarity on summaries"""
        print("\n" + "-" * 80)
        print("🖼️ STEP 3: RETRIEVING RELEVANT IMAGE CHUNKS")
        print("-" * 80)
        
        query_embedding = state.get('query_embedding', [])
        top_k = state.get('top_k', self.top_k)
        
        if not query_embedding:
            print("⚠️ No query embedding available\n")
            state['image_results'] = []
            return state
        
        try:
            # Vector similarity search on image summary embeddings
            self.db_manager.cursor.execute("""
                SELECT 
                    chunk_id,
                    chunk_type,
                    section_id,
                    source_document,
                    image_type,
                    image_summary,
                    metadata,
                    embedding,
                    1 - (embedding <=> %s::vector) as similarity_score
                FROM image_chunks
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
            """, (query_embedding, query_embedding, top_k))
            
            rows = self.db_manager.cursor.fetchall()
            
            image_results = []
            for row in rows:
                image_results.append({
                    'chunk_id': row['chunk_id'],
                    'chunk_type': row['chunk_type'],
                    'section_id': row['section_id'],
                    'source_document': row['source_document'],
                    'image_type': row['image_type'],
                    'image_summary': row['image_summary'],
                    'content': row['image_summary'],  # Use summary as content for consistency
                    'metadata': row['metadata'] if row['metadata'] else {},
                    'similarity_score': float(row['similarity_score']),
                    'retrieval_method': 'vector_similarity'
                })
            
            print(f"✅ Retrieved {len(image_results)} image chunks")
            if image_results:
                print(f"   Top similarity score: {image_results[0]['similarity_score']:.4f}")
                print(f"   Image type: {image_results[0]['image_type']}")
                print(f"   Preview: {image_results[0]['image_summary'][:100]}...\n")
            
            state['image_results'] = image_results
            
        except Exception as e:
            print(f"❌ Error retrieving image chunks: {str(e)}\n")
            state['image_results'] = []
        
        return state
    
    def retrieve_table_chunks(self, state: RetrievalState) -> RetrievalState:
        """Retrieve relevant table chunks using keyword matching on SQL and metadata"""
        print("\n" + "-" * 80)
        print("📊 STEP 4: RETRIEVING RELEVANT TABLE CHUNKS")
        print("-" * 80)
        
        query = state.get('query', '')
        top_k = state.get('top_k', self.top_k)
        
        if not query:
            print("⚠️ No query available\n")
            state['table_results'] = []
            return state
        
        try:
            # Keyword-based search on table metadata and SQL queries
            # Using PostgreSQL ILIKE for case-insensitive pattern matching
            query_terms = query.lower().split()
            
            if not query_terms:
                print("⚠️ No query terms extracted\n")
                state['table_results'] = []
                return state
            
            # Build parameterized query to avoid SQL injection and % character issues
            # Use ILIKE for each term across table_name, sql_query, and metadata
            search_conditions = []
            params = []
            
            for term in query_terms:
                search_term = f'%{term}%'
                search_conditions.append(
                    "(LOWER(table_name) ILIKE %s OR "
                    "LOWER(sql_query) ILIKE %s OR "
                    "LOWER(metadata::text) ILIKE %s)"
                )
                params.extend([search_term, search_term, search_term])
            
            # Combine with OR
            where_clause = " OR ".join(search_conditions)
            params.append(top_k)
            
            self.db_manager.cursor.execute(f"""
                SELECT 
                    chunk_id,
                    chunk_type,
                    section_id,
                    source_document,
                    table_name,
                    sql_query,
                    metadata
                FROM table_chunks
                WHERE {where_clause}
                LIMIT %s;
            """, tuple(params))
            
            rows = self.db_manager.cursor.fetchall()
            
            table_results = []
            for i, row in enumerate(rows, 1):
                # Calculate a simple relevance score based on term frequency
                relevance_score = 0
                text_to_search = f"{row['table_name']} {row['sql_query']} {row['metadata']}".lower()
                for term in query_terms:
                    relevance_score += text_to_search.count(term)
                
                # Normalize score
                relevance_score = min(1.0, relevance_score / (len(query_terms) * 3))
                
                table_results.append({
                    'chunk_id': row['chunk_id'],
                    'chunk_type': row['chunk_type'],
                    'section_id': row['section_id'],
                    'source_document': row['source_document'],
                    'table_name': row['table_name'],
                    'sql_query': row['sql_query'],
                    'content': f"Table: {row['table_name']}\nSQL: {row['sql_query'][:200]}...",
                    'metadata': row['metadata'] if row['metadata'] else {},
                    'similarity_score': relevance_score,
                    'retrieval_method': 'keyword_matching'
                })
            
            # Sort by relevance score
            table_results.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            print(f"✅ Retrieved {len(table_results)} table chunks")
            if table_results:
                print(f"   Top relevance score: {table_results[0]['similarity_score']:.4f}")
                print(f"   Table name: {table_results[0]['table_name']}\n")
            
            state['table_results'] = table_results
            
        except Exception as e:
            print(f"❌ Error retrieving table chunks: {str(e)}\n")
            import traceback
            traceback.print_exc()
            state['table_results'] = []
        
        return state
    
    def combine_results(self, state: RetrievalState) -> RetrievalState:
        """Combine all retrieved results and normalize scores"""
        print("\n" + "-" * 80)
        print("🔀 STEP 5: COMBINING AND NORMALIZING RESULTS")
        print("-" * 80)
        
        text_results = state.get('text_results', [])
        image_results = state.get('image_results', [])
        table_results = state.get('table_results', [])
        
        # Combine all results
        all_results = text_results + image_results + table_results
        
        print(f"📦 Total results retrieved: {len(all_results)}")
        print(f"   Text chunks: {len(text_results)}")
        print(f"   Image chunks: {len(image_results)}")
        print(f"   Table chunks: {len(table_results)}\n")
        
        if all_results:
            # Sort by similarity score (descending)
            all_results.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            print(f"📊 Score distribution:")
            print(f"   Highest: {all_results[0]['similarity_score']:.4f}")
            print(f"   Lowest: {all_results[-1]['similarity_score']:.4f}")
            print(f"   Average: {np.mean([r['similarity_score'] for r in all_results]):.4f}\n")
        
        state['all_results'] = all_results
        
        return state
    
    def retrieve(self, query: str, top_k: int = None) -> Dict[str, Any]:
        """
        Execute the retrieval workflow for a given query
        
        Args:
            query: User query string
            top_k: Number of results to retrieve per chunk type
            
        Returns:
            Dictionary with retrieval results
        """
        print("\n" + "=" * 80)
        print("🚀 STARTING RETRIEVAL WORKFLOW")
        print("=" * 80)
        
        # Initial state
        initial_state = {
            'query': query,
            'query_embedding': [],
            'text_results': [],
            'image_results': [],
            'table_results': [],
            'all_results': [],
            'top_k': top_k if top_k else self.top_k,
            'error': ''
        }
        
        # Run workflow
        final_state = self.workflow.invoke(initial_state)
        
        print("\n" + "=" * 80)
        print("✅ RETRIEVAL WORKFLOW COMPLETED")
        print("=" * 80)
        
        # Summary
        all_results = final_state.get('all_results', [])
        print("\n📊 RETRIEVAL SUMMARY:")
        print(f"   Query: {query[:100]}{'...' if len(query) > 100 else ''}")
        print(f"   Total results: {len(all_results)}")
        
        if all_results:
            print(f"   Chunk type distribution:")
            from collections import Counter
            type_counts = Counter([r['chunk_type'] for r in all_results])
            for chunk_type, count in type_counts.items():
                print(f"      {chunk_type}: {count}")
        
        if final_state.get('error'):
            print(f"   ⚠️ Errors encountered: {final_state['error']}")
        
        print("\n")
        
        return {
            'query': query,
            'results': all_results,
            'text_results': final_state.get('text_results', []),
            'image_results': final_state.get('image_results', []),
            'table_results': final_state.get('table_results', []),
            'num_results': len(all_results)
        }


def main():
    """Main entry point for Agent 3"""
    # Initialize agent
    agent = RetrievalAgent(top_k=5)
    
    # Example query
    test_query = "What are the key factors for business readiness and job creation?"
    
    # Run retrieval
    results = agent.retrieve(test_query)
    
    # Display results
    print("\n" + "=" * 80)
    print("🔍 RETRIEVED RESULTS")
    print("=" * 80 + "\n")
    
    for i, result in enumerate(results['results'][:5], 1):
        print(f"{i}. [{result['chunk_type'].upper()}] {result['chunk_id']}")
        print(f"   Score: {result['similarity_score']:.4f}")
        print(f"   Source: {result['source_document']}")
        print(f"   Preview: {result['content'][:150]}...")
        print()
    
    return results


if __name__ == "__main__":
    main()
