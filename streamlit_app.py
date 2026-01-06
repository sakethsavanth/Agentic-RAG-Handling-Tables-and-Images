"""
Streamlit Chatbot UI
Interactive chatbot interface for the Multimodal Agentic RAG system
"""
import streamlit as st
import sys
from pathlib import Path
import json
from datetime import datetime
import shutil
import os

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from chatbot_orchestrator import ChatbotOrchestrator
from agents.document_parse_agent import DocumentParseAgent
from agents.document_embedder import DocumentEmbedderAgent


# Page configuration
st.set_page_config(
    page_title="Multimodal RAG Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    
    .user-message {
        background-color: #e3f2fd;
        border-left: 5px solid #2196f3;
    }
    
    .assistant-message {
        background-color: #f3e5f5;
        border-left: 5px solid #9c27b0;
    }
    
    .confidence-high {
        color: #4caf50;
        font-weight: bold;
    }
    
    .confidence-medium {
        color: #ff9800;
        font-weight: bold;
    }
    
    .confidence-low {
        color: #f44336;
        font-weight: bold;
    }
    
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
    }
    
    .process-step {
        background-color: #ffffff;
        padding: 0.5rem 1rem;
        margin: 0.25rem 0;
        border-radius: 0.25rem;
        border-left: 3px solid #667eea;
    }
    
    .success-step {
        border-left-color: #4caf50;
    }
    
    .failed-step {
        border-left-color: #f44336;
    }
    
    .skipped-step {
        border-left-color: #9e9e9e;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
if 'orchestrator' not in st.session_state:
    st.session_state.orchestrator = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'processing' not in st.session_state:
    st.session_state.processing = False


def initialize_orchestrator():
    """Initialize the orchestrator if not already done"""
    if st.session_state.orchestrator is None:
        with st.spinner("🔄 Initializing AI agents..."):
            st.session_state.orchestrator = ChatbotOrchestrator(
                retrieval_top_k=10,
                rerank_top_k=5
            )
        st.success("✅ AI agents initialized!")


def process_document(file_path: str, file_name: str):
    """Process a newly uploaded document"""
    try:
        # Step 1: Parse document
        with st.spinner(f"📄 Parsing {file_name}..."):
            parse_agent = DocumentParseAgent(data_folder="data")
            # The parse agent will process all files in the data folder
            parse_result = parse_agent.run()
            parse_agent.db_manager.close()
        
        st.success(f"✅ Parsed: {parse_result.get('total_chunks', 0)} chunks created")
        
        # Step 2: Generate embeddings
        with st.spinner(f"🔢 Generating embeddings..."):
            embedder_agent = DocumentEmbedderAgent(chunks_folder="chunks")
            embedder_result = embedder_agent.run_all_documents()
            embedder_agent.db_manager.close()
        
        st.success(f"✅ Embeddings generated: {len(embedder_result)} documents processed")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Error processing document: {str(e)}")
        return False


def get_confidence_class(confidence: float) -> str:
    """Get CSS class based on confidence score"""
    if confidence >= 0.85:
        return "confidence-high"
    elif confidence >= 0.70:
        return "confidence-medium"
    else:
        return "confidence-low"


def render_process_log(process_log: list):
    """Render the process log in an expandable section"""
    with st.expander("🔍 View Processing Details", expanded=False):
        st.markdown("### Agent Execution Timeline")
        
        for log_entry in process_log:
            status = log_entry.get('status', 'unknown')
            
            # Determine CSS class based on status
            if status == 'completed':
                step_class = 'success-step'
                icon = '✅'
            elif status == 'failed':
                step_class = 'failed-step'
                icon = '❌'
            elif status == 'skipped':
                step_class = 'skipped-step'
                icon = '⏭️'
            else:
                step_class = ''
                icon = '🔄'
            
            # Render step
            st.markdown(f"""
            <div class="process-step {step_class}">
                <strong>{icon} {log_entry.get('step', 'Unknown Step')}</strong><br/>
                <small>Agent: {log_entry.get('agent', 'N/A')} | Time: {log_entry.get('timestamp', 'N/A')}</small><br/>
                {f"<small>{log_entry.get('output', log_entry.get('error', ''))}</small>" if log_entry.get('output') or log_entry.get('error') else ''}
            </div>
            """, unsafe_allow_html=True)


def render_sources(sources: list):
    """Render source chunks in an expandable section"""
    if not sources:
        return
    
    with st.expander(f"📚 View {len(sources)} Source Chunks", expanded=False):
        for i, source in enumerate(sources, 1):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Source {i}:** {source.get('chunk_id', 'Unknown')}")
                st.markdown(f"*{source.get('chunk_type', 'unknown').upper()} from {source.get('source_document', 'Unknown')}*")
                st.text(source.get('content', '')[:300] + "...")
            
            with col2:
                st.metric("Score", f"{source.get('final_score', 0):.3f}")
            
            st.divider()


def render_sql_details(sql_queries: list, sql_answer: str):
    """Render SQL execution details"""
    if not sql_queries:
        return
    
    with st.expander("💾 View SQL Execution Details", expanded=False):
        st.markdown("### Generated SQL Queries")
        
        for i, query in enumerate(sql_queries, 1):
            st.markdown(f"**Query {i}:**")
            st.code(query, language="sql")
        
        st.markdown("### SQL Results")
        st.markdown(sql_answer)


def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<div class="main-header">🤖 Multimodal Agentic RAG Chatbot</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Initialize button
        if st.button("🚀 Initialize AI Agents", use_container_width=True):
            initialize_orchestrator()
        
        st.markdown("---")
        
        # Document Management
        st.header("📁 Document Management")
        
        # View existing documents
        st.subheader("Current Documents")
        data_folder = Path("data")
        if data_folder.exists():
            documents = list(data_folder.glob("*.pdf"))
            if documents:
                for doc in documents:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.text(f"📄 {doc.name}")
                    with col2:
                        if st.button("🗑️", key=f"delete_{doc.name}", help="Delete document"):
                            doc.unlink()
                            st.success(f"Deleted {doc.name}")
                            st.rerun()
            else:
                st.info("No documents found")
        else:
            st.warning("Data folder not found")
        
        st.markdown("---")
        
        # Upload new document
        st.subheader("Upload New Document")
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Upload a PDF document to add to the knowledge base"
        )
        
        if uploaded_file is not None:
            if st.button("📤 Process Document", use_container_width=True):
                # Save uploaded file
                data_folder.mkdir(exist_ok=True)
                file_path = data_folder / uploaded_file.name
                
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                st.info(f"Saved {uploaded_file.name} to data folder")
                
                # Process document
                if process_document(str(file_path), uploaded_file.name):
                    st.balloons()
                    st.success("🎉 Document processed successfully!")
        
        st.markdown("---")
        
        # Statistics
        st.header("📊 Statistics")
        if st.session_state.chat_history:
            st.metric("Total Queries", len(st.session_state.chat_history))
            
            # Average confidence
            confidences = [msg.get('confidence_score', 0) for msg in st.session_state.chat_history if 'confidence_score' in msg]
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
                st.metric("Avg Confidence", f"{avg_confidence:.1%}")
        
        st.markdown("---")
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    
    # Main chat interface
    st.header("💬 Chat Interface")
    
    # Display chat history
    chat_container = st.container()
    
    with chat_container:
        for i, message in enumerate(st.session_state.chat_history):
            if message['role'] == 'user':
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>👤 You</strong><br/>
                    {message['content']}
                </div>
                """, unsafe_allow_html=True)
            else:
                # Assistant message
                confidence = message.get('confidence_score', 0)
                confidence_class = get_confidence_class(confidence)
                
                st.markdown(f"""
                <div class="chat-message assistant-message">
                    <strong>🤖 Assistant</strong> 
                    <span class="{confidence_class}">
                        (Confidence: {confidence:.0%})
                    </span>
                    <br/><br/>
                </div>
                """, unsafe_allow_html=True)
                
                # Display final answer
                st.markdown(message.get('final_answer', message.get('content', '')))
                
                # Metrics row
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Retrieved", message.get('retrieved_chunks_count', 0))
                with col2:
                    st.metric("Reranked", message.get('reranked_chunks_count', 0))
                with col3:
                    st.metric("SQL Executed", "Yes" if message.get('sql_executed') else "No")
                with col4:
                    st.metric("Duration", f"{message.get('duration_seconds', 0):.1f}s")
                
                # Expandable sections
                render_process_log(message.get('process_log', []))
                render_sources(message.get('rag_sources', []))
                
                if message.get('sql_executed'):
                    render_sql_details(
                        message.get('sql_queries', []),
                        message.get('sql_answer', '')
                    )
                
                st.markdown("---")
    
    # Chat input
    st.markdown("### Ask a Question")
    
    # Create columns for input and button
    col1, col2 = st.columns([5, 1])
    
    with col1:
        user_input = st.text_input(
            "Type your question here...",
            key="user_input",
            placeholder="e.g., What is the pillar score for Indonesia?",
            label_visibility="collapsed"
        )
    
    with col2:
        send_button = st.button("Send 🚀", use_container_width=True)
    
    # Process user input
    if send_button and user_input:
        if st.session_state.orchestrator is None:
            st.error("⚠️ Please initialize the AI agents first using the sidebar button!")
        else:
            # Add user message to history
            st.session_state.chat_history.append({
                'role': 'user',
                'content': user_input
            })
            
            # Process query
            with st.spinner("🤔 Processing your question..."):
                try:
                    result = st.session_state.orchestrator.process_user_query(user_input)
                    
                    # Add assistant message to history
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        **result
                    })
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error processing query: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666;">
        <small>Powered by LangGraph, AWS Bedrock, and PostgreSQL | 
        Agents: Document Parser • Document Embedder • Retrieval • Reranking • Text-to-SQL</small>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
