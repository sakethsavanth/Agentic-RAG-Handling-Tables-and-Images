"""
Main entry point for the Multimodal Agentic RAG Pipeline
Run this to execute all agents sequentially
"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from agents.document_parse_agent import DocumentParseAgent
from agents.document_embedder import DocumentEmbedderAgent
from agents.retrieval_agent import RetrievalAgent
from agents.reranking_agent import RerankingAgent
from utils.logging_utils import TeeLogger, get_log_filename


def main():
    """
    Main pipeline execution
    """
    # Set up logging to file
    log_filename = get_log_filename(prefix="main_pipeline")
    
    with TeeLogger(log_folder="query results", log_name=log_filename):
        print("\n" + "=" * 80)
        print("🚀 MULTIMODAL AGENTIC RAG PIPELINE")
        print("=" * 80)
        print("\nThis pipeline will:")
        print("  1. Parse and chunk documents (Agent 1)")
        print("  2. Generate embeddings (Agent 2)")
        print("  3. Retrieve relevant chunks (Agent 3)")
        print("  4. Rerank results (Agent 4)")
        print("\n" + "=" * 80 + "\n")
        
        # ==================== AGENT 1: DOCUMENT PARSING ====================
        print("\n🤖 STARTING AGENT 1: DOCUMENT PARSE AGENT\n")
        
        try:
            parse_agent = DocumentParseAgent(data_folder="data")
            parse_result = parse_agent.run()
            
            if parse_result.get('error'):
                print(f"\n⚠️ Warning: Agent 1 completed with errors: {parse_result['error']}")
            else:
                print("\n✅ Agent 1 completed successfully!")
            
            # Close database connection
            parse_agent.db_manager.close()
            
        except Exception as e:
            print(f"\n❌ Agent 1 failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            print("Pipeline terminated.")
            return
        
        # ==================== AGENT 2: DOCUMENT EMBEDDING ====================
        print("\n" + "=" * 80)
        print("\n🤖 STARTING AGENT 2: DOCUMENT EMBEDDER AGENT\n")
        
        try:
            embedder_agent = DocumentEmbedderAgent(chunks_folder="chunks")
            embedder_result = embedder_agent.run_all_documents()
            
            print("\n✅ Agent 2 completed successfully!")
            
            # Close database connection
            embedder_agent.db_manager.close()
            
        except Exception as e:
            print(f"\n❌ Agent 2 failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            print("Pipeline terminated.")
            return
        
        # ==================== AGENT 3: RETRIEVAL ====================
        print("\n" + "=" * 80)
        print("\n🤖 STARTING AGENT 3: RETRIEVAL AGENT\n")
        
        # Example query for demonstration
        test_query = "What are the key pillars of business readiness and governance performance?"
        
        try:
            retrieval_agent = RetrievalAgent(top_k=10)
            retrieval_result = retrieval_agent.retrieve(test_query)
            
            print("\n✅ Agent 3 completed successfully!")
            
            # Close database connection
            retrieval_agent.db_manager.close()
            
        except Exception as e:
            print(f"\n❌ Agent 3 failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            print("Continuing to Agent 4 demo with empty results...")
            retrieval_result = {'results': [], 'query': test_query}
        
        # ==================== AGENT 4: RERANKING ====================
        print("\n" + "=" * 80)
        print("\n🤖 STARTING AGENT 4: RERANKING AGENT\n")
        
        try:
            reranking_agent = RerankingAgent(top_k=5)
            
            if retrieval_result.get('results'):
                reranking_result = reranking_agent.rerank(
                    query=test_query,
                    retrieved_chunks=retrieval_result['results']
                )
                
                print("\n✅ Agent 4 completed successfully!")
                
                # Display final reranked results
                print("\n" + "=" * 80)
                print("🏆 FINAL RERANKED RESULTS")
                print("=" * 80 + "\n")
                
                for i, chunk in enumerate(reranking_result['reranked_chunks'], 1):
                    print(f"{i}. [{chunk['chunk_type'].upper()}] {chunk['chunk_id']}")
                    print(f"   Score: {chunk['final_score']:.4f}")
                    print(f"   Source: {chunk['source_document']}")
                    print(f"   Preview: {chunk.get('content', '')[:100]}...")
                    print()
            else:
                print("⚠️ No results to rerank. Skipping Agent 4.")
                reranking_result = {'reranked_chunks': []}
            
        except Exception as e:
            print(f"\n❌ Agent 4 failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            reranking_result = {'reranked_chunks': []}
        
        # ==================== PIPELINE COMPLETE ====================
        print("\n" + "=" * 80)
        print("✅ MULTIMODAL AGENTIC RAG PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        print("\n📊 FINAL SUMMARY:")
        print(f"   Documents processed: {len(parse_result.get('documents', []))}")
        print(f"   Text chunks created: {len(parse_result.get('text_chunks', []))}")
        print(f"   Image chunks created: {len(parse_result.get('image_chunks', []))}")
        print(f"   Table chunks created: {len(parse_result.get('table_chunks', []))}")
        print(f"   Embeddings generated: {len(embedder_result)}")
        print(f"   JSONL files created: {len(embedder_result)}")
        print(f"\n   Sample Query: \"{test_query}\"")
        print(f"   Retrieved chunks: {retrieval_result.get('num_results', 0)}")
        print(f"   Reranked top results: {len(reranking_result.get('reranked_chunks', []))}")
        
        print("\n📁 Output files saved in: chunks/")
        print("💾 Data stored in PostgreSQL database")
        
        print("\n" + "=" * 80)
        print("🎉 Ready for Agent 5 (Text-to-SQL) and Streamlit UI")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
