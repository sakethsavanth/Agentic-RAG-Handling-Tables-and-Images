"""
Main entry point for the Multimodal Agentic RAG Pipeline
Run this to execute both Agent 1 and Agent 2 sequentially
"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from agents.document_parse_agent import DocumentParseAgent
from agents.document_embedder import DocumentEmbedderAgent


def main():
    """
    Main pipeline execution
    """
    print("\n" + "=" * 80)
    print("🚀 MULTIMODAL AGENTIC RAG PIPELINE")
    print("=" * 80)
    print("\nThis pipeline will:")
    print("  1. Parse and chunk documents (Agent 1)")
    print("  2. Generate embeddings (Agent 2)")
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
        print("Pipeline terminated.")
        return
    
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
    
    print("\n📁 Output files saved in: chunks/")
    print("💾 Data stored in PostgreSQL database")
    
    print("\n" + "=" * 80)
    print("🎉 Ready for Agent 3 (Retrieval), Agent 4 (Reranker), Agent 5 (Text-to-SQL)")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
