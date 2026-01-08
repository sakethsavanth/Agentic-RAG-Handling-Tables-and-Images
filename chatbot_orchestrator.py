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
from utils.logging_utils import TeeLogger, get_log_filename

# Load environment variables
load_dotenv()


class ChatbotOrchestrator:
    """
    Orchestrates the complete chatbot pipeline:
    1. Retrieval → Reranking → LLM Response
    2. Parallel: Text-to-SQL → SQL Execution
    3. Answer Comparison & Confidence Scoring
    """
    
    def __init__(self, retrieval_top_k: int = 10, rerank_top_k: int = 5, enable_logging: bool = True):
        """Initialize all agents and components"""
        print("\n" + "=" * 80)
        print("🤖 INITIALIZING CHATBOT ORCHESTRATOR")
        print("=" * 80 + "\n")
        
        self.retrieval_agent = RetrievalAgent(top_k=retrieval_top_k)
        self.reranking_agent = RerankingAgent(top_k=rerank_top_k)
        self.text_to_sql_agent = TextToSQLAgent()
        self.aws_client = AWSBedrockClient()
        self.enable_logging = enable_logging
        
        print("✅ Chatbot Orchestrator initialized successfully!\n")
    
    def process_user_query(self, user_query: str, use_cohere_rerank: bool = False) -> Dict[str, Any]:
        """
        Process a user query through the complete pipeline
        
        Args:
            user_query: User's natural language question
            use_cohere_rerank: Whether to use Cohere for reranking (default: False)
            
        Returns:
            Dictionary containing all results, process logs, and confidence scores
        """
        # Set up logging if enabled
        if self.enable_logging:
            log_filename = get_log_filename(prefix="query", query=user_query)
            tee_logger = TeeLogger(log_folder="query results", log_name=log_filename)
            tee_logger.__enter__()  # Start capturing stdout
        else:
            tee_logger = None
        
        try:
            return self._process_query_internal(user_query, use_cohere_rerank)
        finally:
            # Clean up logger
            if tee_logger:
                tee_logger.__exit__(None, None, None)
    
    def _process_query_internal(self, user_query: str, use_cohere_rerank: bool = False) -> Dict[str, Any]:
        """Internal query processing with logging already set up"""
        start_time = datetime.now()
        process_log = []
        
        print("\n" + "=" * 80)
        print("💬 PROCESSING USER QUERY")
        print("=" * 80)
        print(f"Query: {user_query}")
        print(f"Reranking Method: {'Cohere API' if use_cohere_rerank else 'LLM-based'}\n")
        
        # ==================================================================
        # PARALLEL EXECUTION: RAG Path + SQL Path
        # ==================================================================
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both paths concurrently
            rag_future = executor.submit(self._rag_pipeline, user_query, process_log, use_cohere_rerank)
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
            'reranking_method': 'Cohere API' if use_cohere_rerank else 'LLM-based',
            
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
    
    def _rag_pipeline(self, query: str, process_log: List, use_cohere: bool = False) -> Dict[str, Any]:
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
            rerank_method = 'Cohere API' if use_cohere else 'LLM-based'
            process_log.append({
                'step': 'Reranking',
                'agent': f'RerankingAgent ({rerank_method})',
                'status': 'started',
                'timestamp': datetime.now().isoformat()
            })
            
            reranking_result = self.reranking_agent.rerank(
                query=query,
                retrieved_chunks=retrieval_result['results'],
                use_cohere=use_cohere
            )
            
            process_log.append({
                'step': 'Reranking',
                'agent': f'RerankingAgent ({rerank_method})',
                'status': 'completed',
                'timestamp': datetime.now().isoformat(),
                'output': f"Reranked to top {len(reranking_result['reranked_chunks'])} chunks using {rerank_method}"
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
        # Build context from reranked chunks with more content
        context_parts = []
        
        # Separate chunks by type for better organization
        text_chunks = [c for c in reranked_chunks if c['chunk_type'] == 'text']
        table_chunks = [c for c in reranked_chunks if c['chunk_type'] == 'table']
        image_chunks = [c for c in reranked_chunks if c['chunk_type'] == 'image']
        
        # Add text chunks (full content for top 3, then truncated)
        if text_chunks:
            context_parts.append("=== TEXT CONTENT ===")
            for i, chunk in enumerate(text_chunks[:5], 1):
                context_parts.append(f"\n[Text Source {i}]")
                context_parts.append(f"Document: {chunk['source_document']}")
                # Use more content for top chunks
                content_limit = 1000 if i <= 3 else 500
                content = chunk['content'][:content_limit]
                context_parts.append(f"Content: {content}")
                if len(chunk['content']) > content_limit:
                    context_parts.append("[Content continues...]")
        
        # Add table chunks (tables are often key data)
        if table_chunks:
            context_parts.append("\n=== TABLE DATA ===")
            for i, chunk in enumerate(table_chunks[:5], 1):
                context_parts.append(f"\n[Table Source {i}]")
                context_parts.append(f"Document: {chunk['source_document']}")
                # Tables should show full content up to 1500 chars
                content = chunk['content'][:1500]
                context_parts.append(f"Table Content:\n{content}")
                if len(chunk['content']) > 1500:
                    context_parts.append("[Table continues...]")
        
        # Add image descriptions
        if image_chunks:
            context_parts.append("\n=== IMAGE DESCRIPTIONS ===")
            for i, chunk in enumerate(image_chunks[:3], 1):
                context_parts.append(f"\n[Image Source {i}]")
                context_parts.append(f"Document: {chunk['source_document']}")
                context_parts.append(f"Description: {chunk['content'][:800]}")
        
        context = "\n".join(context_parts)
        
        # Create improved prompt
        prompt = f"""You are an expert analyst with access to retrieved documents. Your task is to answer the question using the information provided in the context below.

📄 RETRIEVED CONTEXT:
{context}

❓ USER QUESTION: {query}

📋 INSTRUCTIONS:
1. CAREFULLY READ all the provided context including text, tables, and image descriptions
2. EXTRACT and SYNTHESIZE relevant information from the context to answer the question
3. For quantitative questions, look for numbers, statistics, and data in the tables and text
4. For qualitative questions, look for descriptions, explanations, and narrative content
5. If multiple sources mention the topic, combine the information coherently
6. CITE specific sources when providing information (e.g., "According to the WHO 2025 document...")
7. If the exact answer isn't in the context BUT related information exists:
   - Provide the related information
   - Explain what information is available and what is missing
   - Suggest what additional information would be needed
8. ONLY say information is unavailable if:
   - The context is completely unrelated to the question
   - After thorough review, no relevant information exists

⚠️ IMPORTANT:
- DO NOT give up easily - examine tables, text, and descriptions thoroughly
- TABLES often contain key numerical data - read them carefully
- Image descriptions may contain visual data representations
- Look for partial answers or related information before saying "not found"

💬 YOUR ANSWER:"""

        # Call LLM
        result = self.aws_client.get_nova_response(
            prompt=prompt,
            model_id="us.amazon.nova-pro-v1:0"
        )
        
        if result['success']:
            response = result['response']
            
            # Check if response is too generic or unhelpful
            unhelpful_phrases = [
                "does not contain",
                "doesn't contain", 
                "not provide",
                "does not provide",
                "cannot find",
                "unable to find",
                "no information",
                "no specific",
                "would be required",
                "please provide",
                "additional documents",
                "different source"
            ]
            
            # Count how many unhelpful phrases appear
            unhelpful_count = sum(1 for phrase in unhelpful_phrases if phrase.lower() in response.lower())
            
            # If response seems unhelpful but we have chunks, try a second pass with stronger prompt
            if unhelpful_count >= 2 and len(reranked_chunks) > 0:
                print("⚠️ First response was generic, attempting focused retry...")
                
                # Build a more focused context with ALL content from top chunks
                focused_context = []
                for i, chunk in enumerate(reranked_chunks[:8], 1):
                    focused_context.append(f"\n{'='*60}")
                    focused_context.append(f"SOURCE {i}: {chunk['source_document']} ({chunk['chunk_type']})")
                    focused_context.append(f"{'='*60}")
                    focused_context.append(chunk['content'])  # Full content, no truncation
                
                retry_prompt = f"""You previously said information was unavailable, but you have retrieved documents. Let's try again more carefully.

QUESTION: {query}

FULL CONTEXT FROM RETRIEVED DOCUMENTS:
{chr(10).join(focused_context)}

CRITICAL INSTRUCTIONS:
1. Read EVERY piece of the context above thoroughly
2. Look for ANY information related to: {query}
3. Even if you can't answer exactly, provide what IS available in the documents
4. List ALL relevant facts, numbers, or descriptions you find
5. DO NOT say information is missing unless you've examined everything

What information can you find related to the question?"""
                
                retry_result = self.aws_client.get_nova_response(
                    prompt=retry_prompt,
                    model_id="us.amazon.nova-pro-v1:0"
                )
                
                if retry_result['success']:
                    return retry_result['response']
            
            return response
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
