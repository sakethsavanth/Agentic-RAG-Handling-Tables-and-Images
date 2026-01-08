"""
Quick start script for the Multimodal Agentic RAG Chatbot
Run this to launch the Streamlit UI
"""
import subprocess
import sys
from pathlib import Path

def main():
    """Launch the Streamlit chatbot"""
    print("\n" + "=" * 80)
    print("🤖 STARTING MULTIMODAL AGENTIC RAG CHATBOT")
    print("=" * 80)
    print("\nFeatures:")
    print("  ✓ Multi-modal retrieval (text, images, tables)")
    print("  ✓ Parallel RAG + SQL execution")
    print("  ✓ Answer comparison & confidence scoring")
    print("  ✓ Document management")
    print("  ✓ Process transparency")
    print("\n" + "=" * 80 + "\n")
    
    # Get the streamlit app path
    app_path = Path(__file__).parent / "streamlit_app.py"
    
    # Check if streamlit is installed
    try:
        import streamlit
        print("✅ Streamlit found")
    except ImportError:
        print("❌ Streamlit not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
        print("✅ Streamlit installed")
    
    # Launch streamlit
    print("\n🚀 Launching chatbot UI...")
    print("   The browser should open automatically.")
    print("   If not, navigate to: http://localhost:8501\n")
    print("   Press Ctrl+C to stop the server\n")
    print("=" * 80 + "\n")
    
    try:
        subprocess.run([
            sys.executable, 
            "-m", 
            "streamlit", 
            "run", 
            str(app_path),
            "--server.headless=false"
        ])
    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print("🛑 Chatbot stopped")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
