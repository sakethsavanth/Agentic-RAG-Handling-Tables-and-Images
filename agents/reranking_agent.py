"""
Agent 4: Reranking Agent
This agent reranks retrieved chunks using multiple strategies including
cross-encoder scoring, reciprocal rank fusion, and chunk type weighting
"""
import os
import sys
from pathlib import Path
import numpy as np
from typing import List, Dict, Any, Tuple
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from dotenv import load_dotenv
from collections import defaultdict

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils import AWSBedrockClient

# Load environment variables
load_dotenv()


class RerankingState(TypedDict):
    """State for reranking workflow"""
    query: str
    retrieved_chunks: List[Dict[str, Any]]
    reranked_chunks: List[Dict[str, Any]]
    top_k: int
    error: str


class RerankingAgent:
    """
    Agent 4: Reranking Agent
    Reranks retrieved chunks using hybrid scoring combining:
    1. Initial retrieval scores
    2. LLM-based relevance scoring
    3. Chunk type weighting
    4. Diversity-based reranking
    """
    
    def __init__(self, top_k: int = 10):
        """
        Initialize the Reranking Agent
        
        Args:
            top_k: Number of top chunks to return after reranking
        """
        print("\n" + "=" * 80)
        print("🤖 INITIALIZING AGENT 4: RERANKING AGENT")
        print("=" * 80 + "\n")
        
        self.top_k = top_k
        self.aws_client = AWSBedrockClient()
        
        # Chunk type weights (can be tuned based on your use case)
        self.chunk_type_weights = {
            'text': 1.0,      # Baseline weight
            'image': 0.9,     # Slightly lower as summaries may be less precise
            'table': 1.1      # Slightly higher as tables contain structured data
        }
        
        # Initialize Cohere MCP client (lazy initialization)
        self.cohere_client = None
        
        # Build LangGraph workflow
        self.workflow = self._build_workflow()
        
        print("✅ Reranking Agent initialized successfully!\n")
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for reranking"""
        workflow = StateGraph(RerankingState)
        
        # Add nodes
        workflow.add_node("apply_type_weights", self.apply_type_weights)
        workflow.add_node("llm_relevance_scoring", self.llm_relevance_scoring)
        workflow.add_node("diversity_reranking", self.diversity_reranking)
        workflow.add_node("final_ranking", self.final_ranking)
        
        # Define edges
        workflow.set_entry_point("apply_type_weights")
        workflow.add_edge("apply_type_weights", "llm_relevance_scoring")
        workflow.add_edge("llm_relevance_scoring", "diversity_reranking")
        workflow.add_edge("diversity_reranking", "final_ranking")
        workflow.add_edge("final_ranking", END)
        
        return workflow.compile()
    
    def apply_type_weights(self, state: RerankingState) -> RerankingState:
        """Apply chunk type weights to initial retrieval scores"""
        print("\n" + "-" * 80)
        print("⚖️ STEP 1: APPLYING CHUNK TYPE WEIGHTS")
        print("-" * 80)
        
        chunks = state.get('retrieved_chunks', [])
        
        if not chunks:
            print("⚠️ No chunks to rerank\n")
            return state
        
        print(f"📊 Processing {len(chunks)} chunks...\n")
        
        # Apply type weights to similarity scores
        for chunk in chunks:
            chunk_type = chunk.get('chunk_type', 'text')
            weight = self.chunk_type_weights.get(chunk_type, 1.0)
            
            original_score = chunk.get('similarity_score', 0.0)
            weighted_score = original_score * weight
            
            chunk['weighted_score'] = weighted_score
            chunk['type_weight'] = weight
        
        # Sort by weighted score
        chunks.sort(key=lambda x: x['weighted_score'], reverse=True)
        
        print(f"✅ Applied type weights:")
        for chunk_type, weight in self.chunk_type_weights.items():
            count = sum(1 for c in chunks if c.get('chunk_type') == chunk_type)
            if count > 0:
                print(f"   {chunk_type}: weight={weight:.2f}, count={count}")
        print()
        
        state['retrieved_chunks'] = chunks
        return state
    
    def llm_relevance_scoring(self, state: RerankingState) -> RerankingState:
        """Use LLM to score relevance of each chunk to the query"""
        print("\n" + "-" * 80)
        print("🤖 STEP 2: LLM-BASED RELEVANCE SCORING")
        print("-" * 80)
        
        query = state.get('query', '')
        chunks = state.get('retrieved_chunks', [])
        
        if not query or not chunks:
            print("⚠️ Missing query or chunks\n")
            return state
        
        print(f"📝 Query: {query[:100]}{'...' if len(query) > 100 else ''}")
        print(f"🔍 Scoring {len(chunks)} chunks with Nova...\n")
        
        # Score top candidates only (to save API calls)
        top_candidates = chunks[:min(15, len(chunks))]
        
        for i, chunk in enumerate(top_candidates, 1):
            content = chunk.get('content', '')[:500]  # Limit content length
            chunk_type = chunk.get('chunk_type', 'unknown')
            
            # Create relevance scoring prompt
            prompt = f"""You are a relevance scoring expert. Score how relevant this content is to the user's query.

User Query: "{query}"

Content Type: {chunk_type}
Content: "{content}"

Instructions:
1. Analyze if the content directly addresses the query
2. Consider semantic relevance, not just keyword matching
3. For tables: assess if the data structure is relevant
4. For images: evaluate if the summary relates to the query

Provide ONLY a relevance score between 0.0 and 1.0, where:
- 1.0 = Highly relevant, directly answers the query
- 0.7-0.9 = Relevant, provides useful information
- 0.4-0.6 = Somewhat relevant, tangentially related
- 0.0-0.3 = Not relevant

Score (0.0-1.0):"""
            
            # Get LLM score
            result = self.aws_client.get_nova_response(prompt)
            
            if result['success']:
                try:
                    # Extract score from response
                    score_text = result['response'].strip()
                    # Try to parse the score
                    llm_score = float(score_text.split()[0].replace(',', '.'))
                    llm_score = max(0.0, min(1.0, llm_score))  # Clamp to [0, 1]
                    
                    chunk['llm_relevance_score'] = llm_score
                    print(f"   [{i}/{len(top_candidates)}] {chunk['chunk_id'][:30]}... → {llm_score:.3f}")
                    
                except (ValueError, IndexError):
                    # Fallback to weighted score if parsing fails
                    chunk['llm_relevance_score'] = chunk.get('weighted_score', 0.5)
                    print(f"   [{i}/{len(top_candidates)}] {chunk['chunk_id'][:30]}... → Failed (using weighted)")
            else:
                # Fallback to weighted score
                chunk['llm_relevance_score'] = chunk.get('weighted_score', 0.5)
        
        # For chunks not scored by LLM, use weighted score
        for chunk in chunks[len(top_candidates):]:
            chunk['llm_relevance_score'] = chunk.get('weighted_score', 0.5)
        
        print(f"\n✅ Completed LLM relevance scoring\n")
        
        state['retrieved_chunks'] = chunks
        return state
    
    def diversity_reranking(self, state: RerankingState) -> RerankingState:
        """Apply Maximal Marginal Relevance (MMR) for diversity"""
        print("\n" + "-" * 80)
        print("🎯 STEP 3: DIVERSITY-BASED RERANKING (MMR)")
        print("-" * 80)
        
        chunks = state.get('retrieved_chunks', [])
        
        if not chunks:
            print("⚠️ No chunks to rerank\n")
            return state
        
        print(f"🔄 Applying MMR to {len(chunks)} chunks...\n")
        
        # MMR parameters
        lambda_param = 0.7  # Balance between relevance (1.0) and diversity (0.0)
        
        # Calculate final MMR score
        # MMR = λ * relevance - (1-λ) * max_similarity_to_selected
        
        # For simplicity, we'll use source document and section diversity
        selected_chunks = []
        selected_sources = set()
        selected_sections = set()
        
        # Sort by LLM relevance first
        chunks.sort(key=lambda x: x.get('llm_relevance_score', 0), reverse=True)
        
        for chunk in chunks:
            relevance = chunk.get('llm_relevance_score', 0)
            source = chunk.get('source_document', '')
            section = chunk.get('section_id', '')
            
            # Diversity penalty based on already selected sources/sections
            diversity_penalty = 0.0
            if source in selected_sources:
                diversity_penalty += 0.2
            if section in selected_sections:
                diversity_penalty += 0.1
            
            # Calculate MMR score
            mmr_score = lambda_param * relevance - (1 - lambda_param) * diversity_penalty
            chunk['mmr_score'] = mmr_score
            
            selected_chunks.append(chunk)
            selected_sources.add(source)
            selected_sections.add(section)
        
        # Sort by MMR score
        selected_chunks.sort(key=lambda x: x['mmr_score'], reverse=True)
        
        print(f"✅ Applied MMR reranking (λ={lambda_param})")
        print(f"   Unique sources: {len(selected_sources)}")
        print(f"   Unique sections: {len(selected_sections)}\n")
        
        state['retrieved_chunks'] = selected_chunks
        return state
    
    def final_ranking(self, state: RerankingState) -> RerankingState:
        """Combine all scores and produce final ranking"""
        print("\n" + "-" * 80)
        print("🏆 STEP 4: FINAL RANKING")
        print("-" * 80)
        
        chunks = state.get('retrieved_chunks', [])
        top_k = state.get('top_k', self.top_k)
        
        if not chunks:
            print("⚠️ No chunks to rank\n")
            state['reranked_chunks'] = []
            return state
        
        print(f"🎯 Combining scores for final ranking...\n")
        
        # Combine scores with weights
        score_weights = {
            'weighted_score': 0.2,      # Initial retrieval
            'llm_relevance_score': 0.5, # LLM relevance (most important)
            'mmr_score': 0.3            # Diversity
        }
        
        for chunk in chunks:
            final_score = 0.0
            for score_name, weight in score_weights.items():
                final_score += chunk.get(score_name, 0.0) * weight
            
            chunk['final_score'] = final_score
        
        # Sort by final score
        chunks.sort(key=lambda x: x['final_score'], reverse=True)
        
        # Take top-k
        reranked_chunks = chunks[:top_k]
        
        print(f"📊 Final Ranking (Top {top_k}):")
        for i, chunk in enumerate(reranked_chunks[:5], 1):
            print(f"   {i}. [{chunk['chunk_type'].upper()}] {chunk['chunk_id'][:40]}")
            print(f"      Final Score: {chunk['final_score']:.4f}")
            print(f"      (Retrieval: {chunk.get('similarity_score', 0):.3f}, "
                  f"LLM: {chunk.get('llm_relevance_score', 0):.3f}, "
                  f"MMR: {chunk.get('mmr_score', 0):.3f})")
        
        if len(reranked_chunks) > 5:
            print(f"   ... and {len(reranked_chunks) - 5} more")
        
        print()
        
        state['reranked_chunks'] = reranked_chunks
        return state
    
    def rerank(self, query: str, retrieved_chunks: List[Dict[str, Any]], 
               top_k: int = None, use_cohere: bool = False) -> Dict[str, Any]:
        """
        Execute the reranking workflow
        
        Args:
            query: User query string
            retrieved_chunks: List of chunks from retrieval agent
            top_k: Number of top chunks to return
            use_cohere: Whether to use Cohere API for reranking
            
        Returns:
            Dictionary with reranked results
        """
        print("\n" + "=" * 80)
        print("🚀 STARTING RERANKING WORKFLOW")
        print("=" * 80)
        
        # Check if Cohere reranking is requested
        if use_cohere:
            return self._rerank_with_cohere(query, retrieved_chunks, top_k)
        
        # Otherwise, use standard LLM-based reranking
        # Initial state
        initial_state = {
            'query': query,
            'retrieved_chunks': retrieved_chunks.copy(),
            'reranked_chunks': [],
            'top_k': top_k if top_k else self.top_k,
            'error': ''
        }
        
        # Run workflow
        final_state = self.workflow.invoke(initial_state)
        
        print("\n" + "=" * 80)
        print("✅ RERANKING WORKFLOW COMPLETED")
        print("=" * 80)
        
        reranked = final_state.get('reranked_chunks', [])
        
        # Summary
        print("\n📊 RERANKING SUMMARY:")
        print(f"   Query: {query[:100]}{'...' if len(query) > 100 else ''}")
        print(f"   Input chunks: {len(retrieved_chunks)}")
        print(f"   Output chunks: {len(reranked)}")
        
        if reranked:
            print(f"   Score range: {reranked[-1]['final_score']:.4f} - {reranked[0]['final_score']:.4f}")
            
            # Type distribution
            from collections import Counter
            type_counts = Counter([c['chunk_type'] for c in reranked])
            print(f"   Type distribution: {dict(type_counts)}")
        
        if final_state.get('error'):
            print(f"   ⚠️ Errors encountered: {final_state['error']}")
        
        print("\n")
        
        return {
            'query': query,
            'reranked_chunks': reranked,
            'num_results': len(reranked)
        }
    
    def _rerank_with_cohere(self, query: str, retrieved_chunks: List[Dict[str, Any]], 
                           top_k: int = None) -> Dict[str, Any]:
        """
        Rerank using Cohere API via MCP
        
        Args:
            query: User query string
            retrieved_chunks: List of chunks from retrieval agent
            top_k: Number of top chunks to return
            
        Returns:
            Dictionary with reranked results
        """
        print("\n🤖 USING COHERE API FOR RERANKING")
        print("-" * 80 + "\n")
        
        if not retrieved_chunks:
            print("⚠️ No chunks to rerank\n")
            return {
                'query': query,
                'reranked_chunks': [],
                'num_results': 0
            }
        
        # Initialize Cohere client if needed
        if self.cohere_client is None:
            try:
                from cohere_mcp import CohereMCPClient
                self.cohere_client = CohereMCPClient()
                print("✅ Cohere MCP client initialized")
            except Exception as e:
                print(f"❌ Failed to initialize Cohere client: {str(e)}")
                print("⚠️ Falling back to standard LLM-based reranking\n")
                return self.rerank(query, retrieved_chunks, top_k, use_cohere=False)
        
        # Check if Cohere is available
        status = self.cohere_client.check_status()
        if status.get('status') != 'operational':
            print(f"⚠️ Cohere API not available: {status.get('message', 'Unknown error')}")
            print("⚠️ Falling back to standard LLM-based reranking\n")
            return self.rerank(query, retrieved_chunks, top_k, use_cohere=False)
        
        print(f"📝 Query: {query[:100]}{'...' if len(query) > 100 else ''}")
        print(f"🔍 Reranking {len(retrieved_chunks)} chunks with Cohere...\n")
        
        # Call Cohere MCP for reranking
        result = self.cohere_client.rerank(
            query=query,
            documents=retrieved_chunks,
            top_k=top_k if top_k else self.top_k
        )
        
        if result.get('success'):
            reranked_docs = result.get('reranked_documents', [])
            
            # Convert Cohere results to our format
            reranked_chunks = []
            for doc in reranked_docs:
                # Preserve original chunk structure and add Cohere score
                chunk = {
                    'chunk_id': doc.get('chunk_id', ''),
                    'chunk_type': doc.get('chunk_type', 'text'),
                    'content': doc.get('content', ''),
                    'source_document': doc.get('source_document', ''),
                    'cohere_score': doc.get('cohere_score', 0.0),
                    'final_score': doc.get('cohere_score', 0.0),  # Use Cohere score as final score
                    'metadata': doc.get('metadata', {})
                }
                
                # Add original retrieval score if available
                original = next((c for c in retrieved_chunks if c.get('chunk_id') == doc.get('chunk_id')), None)
                if original:
                    chunk['similarity_score'] = original.get('similarity_score', 0.0)
                    chunk['section_id'] = original.get('section_id', '')
                
                reranked_chunks.append(chunk)
            
            print(f"✅ Cohere reranking completed")
            print(f"   Model: {result.get('model_used', 'unknown')}")
            print(f"   Output chunks: {len(reranked_chunks)}")
            
            if reranked_chunks:
                print(f"   Score range: {reranked_chunks[-1]['cohere_score']:.4f} - {reranked_chunks[0]['cohere_score']:.4f}")
                
                # Type distribution
                from collections import Counter
                type_counts = Counter([c['chunk_type'] for c in reranked_chunks])
                print(f"   Type distribution: {dict(type_counts)}")
            
            print()
            
            return {
                'query': query,
                'reranked_chunks': reranked_chunks,
                'num_results': len(reranked_chunks),
                'reranking_method': 'cohere'
            }
        else:
            print(f"❌ Cohere reranking failed: {result.get('error', 'Unknown error')}")
            print("⚠️ Falling back to standard LLM-based reranking\n")
            return self.rerank(query, retrieved_chunks, top_k, use_cohere=False)


def main():
    """Main entry point for Agent 4"""
    # Initialize agent
    agent = RerankingAgent(top_k=5)
    
    # Example: Create dummy retrieved chunks
    dummy_chunks = [
        {
            'chunk_id': 'doc1_chunk_1',
            'chunk_type': 'text',
            'content': 'Business readiness framework focuses on regulatory environment...',
            'similarity_score': 0.85,
            'source_document': 'Business Ready 2025',
            'section_id': 'intro'
        },
        {
            'chunk_id': 'doc1_table_1',
            'chunk_type': 'table',
            'content': 'Table: governance_performance with country rankings...',
            'similarity_score': 0.78,
            'source_document': 'Business Ready 2025',
            'section_id': 'appendix'
        },
        {
            'chunk_id': 'doc1_img_1',
            'chunk_type': 'image',
            'content': 'Construction workers collaborating on a project...',
            'similarity_score': 0.72,
            'source_document': 'Business Ready 2025',
            'section_id': 'chapter1'
        }
    ]
    
    test_query = "What are the governance factors for business readiness?"
    
    # Run reranking
    results = agent.rerank(test_query, dummy_chunks)
    
    return results


if __name__ == "__main__":
    main()
