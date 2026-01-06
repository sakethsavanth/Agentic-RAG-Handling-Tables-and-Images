"""
Chatbot Orchestrator
Coordinates all agents for the chatbot pipeline: retrieval, reranking, LLM response, 
and parallel Text-to-SQL execution with answer comparison
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import concurrent.futures
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from agents.retrieval_agent import RetrievalAgent
from agents.reranking_agent import RerankingAgent
from agents.text_to_sql_agent import TextToSQLAgent
from utils import AWSBedrockClient

# Load environment variables
load_dotenv()


class ChatbotOrchestrator:
    """
    Orchestrates the complete chatbot pipeline:
    1. Retrieval → Reranking → LLM Response
    2. Parallel: Text-to-SQL → SQL Execution
    3. Answer Comparison & Confidence Scoring
    """
    
    def __init__(self, retrieval_top_k: int = 10, rerank_top_k: int = 5):
        """Initialize all agents and components"""
        print("\n" + "=" * 80)
        print("🤖 INITIALIZING CHATBOT ORCHESTRATOR")
        print("=" * 80 + "\n")
        
        self.retrieval_agent = RetrievalAgent(top_k=retrieval_top_k)
        self.reranking_agent = RerankingAgent(top_k=rerank_top_k)
        self.text_to_sql_agent = TextToSQLAgent()
        self.aws_client = AWSBedrockClient()
        
        print("✅ Chatbot Orchestrator initialized successfully!\n")
    
    def process_user_query(self, user_query: str) -> Dict[str, Any]:
        """
        Process a user query through the complete pipeline
        
        Args:
            user_query: User's natural language question
            
        Returns:
            Dictionary containing all results, process logs, and confidence scores
        """
        start_time = datetime.now()
        process_log = []
        
        print("\n" + "=" * 80)
        print("💬 PROCESSING USER QUERY")
        print("=" * 80)
        print(f"Query: {user_query}\n")
        
        # ==================================================================
        # PARALLEL EXECUTION: RAG Path + SQL Path
        # ==================================================================
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both paths concurrently
            rag_future = executor.submit(self._rag_pipeline, user_query, process_log)
            sql_future = executor.submit(self._sql_pipeline, user_query, process_log)
            
            # Wait for both to complete
            rag_result = rag_future.result()
            sql_result = sql_future.result()
        
        # ==================================================================
        # ANSWER COMPARISON & CONFIDENCE SCORING
        # ==================================================================
        
        comparison_result = self._compare_answers(
            user_query, 
            rag_result, 
            sql_result, 
            process_log
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # ==================================================================
        # FINAL RESULT ASSEMBLY
        # ==================================================================
        
        final_result = {
            'query': user_query,
            'timestamp': start_time.isoformat(),
            'duration_seconds': duration,
            
            # RAG Path Results
            'rag_answer': rag_result['answer'],
            'rag_sources': rag_result['sources'],
            'retrieved_chunks_count': rag_result['retrieved_count'],
            'reranked_chunks_count': rag_result['reranked_count'],
            
            # SQL Path Results
            'sql_executed': sql_result['executed'],
            'sql_answer': sql_result['answer'],
            'sql_queries': sql_result['queries'],
            'sql_reasoning': sql_result['reasoning'],
            
            # Comparison Results
            'confidence_score': comparison_result['confidence'],
            'agreement_level': comparison_result['agreement'],
            'comparison_analysis': comparison_result['analysis'],
            'final_answer': comparison_result['final_answer'],
            
            # Process Transparency
            'process_log': process_log,
            'errors': rag_result.get('errors', []) + sql_result.get('errors', [])
        }
        
        print("\n" + "=" * 80)
        print("✅ QUERY PROCESSING COMPLETED")
        print("=" * 80)
        print(f"Duration: {duration:.2f}s")
        print(f"Confidence: {comparison_result['confidence']:.2%}\n")
        
        return final_result
    
    def _rag_pipeline(self, query: str, process_log: List) -> Dict[str, Any]:
        """Execute the RAG pipeline: Retrieval → Reranking → LLM"""
        try:
            # Step 1: Retrieval
            process_log.append({
                'step': 'Retrieval',
                'agent': 'RetrievalAgent',
                'status': 'started',
                'timestamp': datetime.now().isoformat()
            })
            
            retrieval_result = self.retrieval_agent.retrieve(query)
            
            process_log.append({
                'step': 'Retrieval',
                'agent': 'RetrievalAgent',
                'status': 'completed',
                'timestamp': datetime.now().isoformat(),
                'output': f"Retrieved {retrieval_result['num_results']} chunks"
            })
            
            # Step 2: Reranking
            process_log.append({
                'step': 'Reranking',
                'agent': 'RerankingAgent',
                'status': 'started',
                'timestamp': datetime.now().isoformat()
            })
            
            reranking_result = self.reranking_agent.rerank(
                query=query,
                retrieved_chunks=retrieval_result['results']
            )
            
            process_log.append({
                'step': 'Reranking',
                'agent': 'RerankingAgent',
                'status': 'completed',
                'timestamp': datetime.now().isoformat(),
                'output': f"Reranked to top {len(reranking_result['reranked_chunks'])} chunks"
            })
            
            # Step 3: LLM Generation
            process_log.append({
                'step': 'LLM Response Generation',
                'agent': 'AWSBedrockClient (Nova)',
                'status': 'started',
                'timestamp': datetime.now().isoformat()
            })
            
            llm_answer = self._generate_llm_response(
                query, 
                reranking_result['reranked_chunks']
            )
            
            process_log.append({
                'step': 'LLM Response Generation',
                'agent': 'AWSBedrockClient (Nova)',
                'status': 'completed',
                'timestamp': datetime.now().isoformat(),
                'output': f"Generated response ({len(llm_answer)} characters)"
            })
            
            return {
                'answer': llm_answer,
                'sources': reranking_result['reranked_chunks'],
                'retrieved_count': retrieval_result['num_results'],
                'reranked_count': len(reranking_result['reranked_chunks']),
                'errors': []
            }
            
        except Exception as e:
            process_log.append({
                'step': 'RAG Pipeline',
                'agent': 'Multiple',
                'status': 'failed',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            })
            
            return {
                'answer': f"Error in RAG pipeline: {str(e)}",
                'sources': [],
                'retrieved_count': 0,
                'reranked_count': 0,
                'errors': [str(e)]
            }
    
    def _sql_pipeline(self, query: str, process_log: List) -> Dict[str, Any]:
        """Execute the SQL pipeline: Classification → SQL Generation → Execution"""
        try:
            process_log.append({
                'step': 'SQL Processing',
                'agent': 'TextToSQLAgent',
                'status': 'started',
                'timestamp': datetime.now().isoformat()
            })
            
            sql_result = self.text_to_sql_agent.process_query(query)
            
            if sql_result['requires_sql']:
                process_log.append({
                    'step': 'SQL Processing',
                    'agent': 'TextToSQLAgent',
                    'status': 'completed',
                    'timestamp': datetime.now().isoformat(),
                    'output': f"Generated and executed {len(sql_result['sql_queries'])} SQL quer{'y' if len(sql_result['sql_queries']) == 1 else 'ies'}"
                })
                
                return {
                    'executed': True,
                    'answer': sql_result['formatted_result'],
                    'queries': sql_result['sql_queries'],
                    'reasoning': sql_result['reasoning'],
                    'errors': [sql_result['error']] if sql_result['error'] else []
                }
            else:
                process_log.append({
                    'step': 'SQL Processing',
                    'agent': 'TextToSQLAgent',
                    'status': 'skipped',
                    'timestamp': datetime.now().isoformat(),
                    'output': f"SQL not required: {sql_result['reasoning']}"
                })
                
                return {
                    'executed': False,
                    'answer': '',
                    'queries': [],
                    'reasoning': sql_result['reasoning'],
                    'errors': []
                }
                
        except Exception as e:
            process_log.append({
                'step': 'SQL Processing',
                'agent': 'TextToSQLAgent',
                'status': 'failed',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            })
            
            return {
                'executed': False,
                'answer': '',
                'queries': [],
                'reasoning': f"Error: {str(e)}",
                'errors': [str(e)]
            }
    
    def _generate_llm_response(self, query: str, reranked_chunks: List[Dict]) -> str:
        """Generate LLM response from reranked chunks"""
        # Build context from reranked chunks
        context_parts = []
        for i, chunk in enumerate(reranked_chunks[:5], 1):  # Top 5 chunks
            context_parts.append(f"[Source {i} - {chunk['chunk_type']}]")
            context_parts.append(f"Document: {chunk['source_document']}")
            context_parts.append(f"Content: {chunk['content'][:500]}...")
            context_parts.append("")
        
        context = "\n".join(context_parts)
        
        # Create prompt
        prompt = f"""You are a helpful AI assistant. Answer the user's question based on the provided context.

Context from Retrieved Documents:
{context}

User Question: {query}

Instructions:
- Provide a clear, accurate answer based on the context
- If the context doesn't contain enough information, say so
- Cite sources when possible (e.g., "According to Business Ready 2025...")
- Be concise but comprehensive

Answer:"""

        # Call LLM
        result = self.aws_client.get_nova_response(
            prompt=prompt,
            model_id="us.amazon.nova-pro-v1:0"
        )
        
        if result['success']:
            return result['response']
        else:
            return f"Error generating response: {result.get('error', 'Unknown error')}"
    
    def _compare_answers(self, query: str, rag_result: Dict, sql_result: Dict, 
                        process_log: List) -> Dict[str, Any]:
        """Compare RAG and SQL answers to determine confidence and agreement"""
        
        process_log.append({
            'step': 'Answer Comparison',
            'agent': 'Orchestrator',
            'status': 'started',
            'timestamp': datetime.now().isoformat()
        })
        
        # If SQL wasn't executed, RAG answer is the final answer
        if not sql_result['executed']:
            process_log.append({
                'step': 'Answer Comparison',
                'agent': 'Orchestrator',
                'status': 'completed',
                'timestamp': datetime.now().isoformat(),
                'output': 'Only RAG answer available (SQL not required)'
            })
            
            return {
                'confidence': 0.85,  # Default confidence for RAG-only
                'agreement': 'N/A',
                'analysis': 'SQL processing was not required for this query. Answer is based solely on RAG pipeline.',
                'final_answer': rag_result['answer']
            }
        
        # Both RAG and SQL answers available - compare them
        comparison_prompt = f"""You are an answer quality evaluator. Compare two answers to the same question and assess their agreement.

Question: {query}

Answer 1 (from RAG - Document Retrieval):
{rag_result['answer']}

Answer 2 (from SQL - Database Query):
{sql_result['answer']}

Analyze:
1. Do both answers provide consistent information?
2. Are there any contradictions?
3. Which answer is more precise/reliable?
4. What is the confidence level that the answers agree?

Respond in this exact format:
AGREEMENT_LEVEL: [FULL/PARTIAL/CONFLICT]
CONFIDENCE_SCORE: [0.0-1.0]
ANALYSIS: [Brief explanation of agreement/disagreement]
RECOMMENDED_ANSWER: [Which answer to prioritize or how to combine them]"""

        try:
            result = self.aws_client.get_nova_response(
                prompt=comparison_prompt,
                model_id="us.amazon.nova-pro-v1:0"
            )
            
            if result['success']:
                response = result['response']
                
                # Parse response
                import re
                
                # Extract agreement level
                agreement_match = re.search(r'AGREEMENT_LEVEL:\s*(\w+)', response, re.IGNORECASE)
                agreement = agreement_match.group(1).upper() if agreement_match else 'UNKNOWN'
                
                # Extract confidence score
                confidence_match = re.search(r'CONFIDENCE_SCORE:\s*([\d.]+)', response, re.IGNORECASE)
                confidence = float(confidence_match.group(1)) if confidence_match else 0.75
                
                # Extract analysis
                analysis_match = re.search(r'ANALYSIS:\s*(.+?)(?:RECOMMENDED_ANSWER:|$)', response, re.IGNORECASE | re.DOTALL)
                analysis = analysis_match.group(1).strip() if analysis_match else "No analysis provided"
                
                # Extract recommended answer
                recommended_match = re.search(r'RECOMMENDED_ANSWER:\s*(.+)', response, re.IGNORECASE | re.DOTALL)
                recommended = recommended_match.group(1).strip() if recommended_match else ""
                
                # Build final answer
                if agreement == 'FULL':
                    final_answer = f"**Answer (High Confidence: {confidence:.0%}):**\n\n{rag_result['answer']}\n\n**SQL Verification:**\n{sql_result['answer']}"
                elif agreement == 'PARTIAL':
                    final_answer = f"**Answer (Moderate Confidence: {confidence:.0%}):**\n\n{rag_result['answer']}\n\n**Additional Data from Database:**\n{sql_result['answer']}\n\n*Note: {analysis}*"
                else:  # CONFLICT
                    final_answer = f"**Multiple Answers Found (Confidence: {confidence:.0%}):**\n\n**From Documents:**\n{rag_result['answer']}\n\n**From Database:**\n{sql_result['answer']}\n\n*Note: {analysis}*"
                
                process_log.append({
                    'step': 'Answer Comparison',
                    'agent': 'Orchestrator',
                    'status': 'completed',
                    'timestamp': datetime.now().isoformat(),
                    'output': f'Agreement: {agreement}, Confidence: {confidence:.0%}'
                })
                
                return {
                    'confidence': confidence,
                    'agreement': agreement,
                    'analysis': analysis,
                    'final_answer': final_answer
                }
            else:
                raise Exception(result.get('error', 'Comparison failed'))
                
        except Exception as e:
            process_log.append({
                'step': 'Answer Comparison',
                'agent': 'Orchestrator',
                'status': 'failed',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            })
            
            # Fallback: combine both answers
            return {
                'confidence': 0.70,
                'agreement': 'UNKNOWN',
                'analysis': f'Could not compare answers: {str(e)}',
                'final_answer': f"**From Documents:**\n{rag_result['answer']}\n\n**From Database:**\n{sql_result['answer']}"
            }
    
    def cleanup(self):
        """Close all database connections"""
        self.retrieval_agent.db_manager.close()
        self.text_to_sql_agent.db_manager.close()


def main():
    """Test the orchestrator"""
    orchestrator = ChatbotOrchestrator(retrieval_top_k=10, rerank_top_k=5)
    
    # Test queries
    test_queries = [
        "What is the pillar score for Indonesia?",
        "Explain the role of business readiness",
        "What are the top 3 countries by pillar I score?"
    ]
    
    for query in test_queries:
        print("\n" + "=" * 80)
        print(f"TEST: {query}")
        print("=" * 80)
        
        result = orchestrator.process_user_query(query)
        
        print(f"\n📊 Final Answer (Confidence: {result['confidence_score']:.0%}):")
        print(result['final_answer'])
        print()
    
    orchestrator.cleanup()


if __name__ == "__main__":
    main()
