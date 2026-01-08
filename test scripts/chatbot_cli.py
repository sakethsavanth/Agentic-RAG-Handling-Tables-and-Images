"""
Standalone Chatbot Script with Logging
Run this for a simple command-line chatbot with full logging to file
"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from chatbot_orchestrator import ChatbotOrchestrator


def main():
    """
    Run an interactive chatbot session with logging
    """
    print("\n" + "=" * 80)
    print("🤖 MULTIMODAL AGENTIC RAG CHATBOT (Command Line)")
    print("=" * 80)
    print("\nAll queries and results will be logged to 'query results' folder")
    print("Type 'exit' or 'quit' to end the session\n")
    print("=" * 80 + "\n")
    
    # Initialize orchestrator with logging enabled
    orchestrator = ChatbotOrchestrator(
        retrieval_top_k=10,
        rerank_top_k=5,
        enable_logging=True  # Enable file logging for each query
    )
    
    print("\n" + "=" * 80)
    print("💬 Ready for your questions!")
    print("=" * 80 + "\n")
    
    # Interactive loop
    while True:
        try:
            # Get user input
            user_query = input("\n🧑 You: ").strip()
            
            # Check for exit commands
            if user_query.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!\n")
                break
            
            if not user_query:
                print("⚠️ Please enter a question.")
                continue
            
            # Process the query (logging happens automatically)
            print()  # Add spacing
            result = orchestrator.process_user_query(user_query)
            
            # Display the final answer
            print("\n" + "=" * 80)
            print("🤖 FINAL ANSWER")
            print("=" * 80)
            print(f"\n{result['final_answer']}\n")
            print(f"Confidence: {result['confidence_score']:.1%}")
            print(f"Duration: {result['duration_seconds']:.2f}s")
            print("\n" + "=" * 80)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
