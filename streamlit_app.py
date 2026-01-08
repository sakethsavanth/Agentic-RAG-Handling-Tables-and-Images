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
import requests
import time
import re

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from chatbot_orchestrator import ChatbotOrchestrator
from agents.document_parse_agent import DocumentParseAgent
from agents.document_embedder import DocumentEmbedderAgent
from utils.logging_utils import TeeLogger, get_log_filename
from utils.mcp_client import SQLMCPClient


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
if 'mcp_client' not in st.session_state:
    st.session_state.mcp_client = None
if 'mcp_status' not in st.session_state:
    st.session_state.mcp_status = 'disconnected'
if 'processing_jobs' not in st.session_state:
    st.session_state.processing_jobs = []
if 'use_cohere_rerank' not in st.session_state:
    st.session_state.use_cohere_rerank = False
if 'webhook_server_url' not in st.session_state:
    st.session_state.webhook_server_url = 'http://localhost:8080'
if 'streaming_api_url' not in st.session_state:
    st.session_state.streaming_api_url = 'http://localhost:8090'
if 'cohere_mcp_url' not in st.session_state:
    st.session_state.cohere_mcp_url = 'http://localhost:8100'


def check_mcp_status():
    """Check MCP server status"""
    if st.session_state.mcp_client is None:
        st.session_state.mcp_client = SQLMCPClient()
    
    try:
        if st.session_state.mcp_client.is_connected():
            st.session_state.mcp_status = 'connected'
        else:
            # Try to connect
            if st.session_state.mcp_client.connect():
                st.session_state.mcp_status = 'connected'
            else:
                st.session_state.mcp_status = 'disconnected'
    except:
        st.session_state.mcp_status = 'error'
    
    return st.session_state.mcp_status


def initialize_orchestrator():
    """Initialize the orchestrator if not already done"""
    if st.session_state.orchestrator is None:
        with st.spinner("🔄 Initializing AI agents..."):
            st.session_state.orchestrator = ChatbotOrchestrator(
                retrieval_top_k=10,
                rerank_top_k=5,
                enable_logging=True  # Enable file logging
            )
        st.success("✅ AI agents initialized!")
        st.info("💾 Query logs will be saved to 'query results' folder")


def process_document(file_path: str, file_name: str):
    """Process a newly uploaded document using webhook server (async processing)"""
    try:
        # Upload to webhook server for async processing
        with open(file_path, 'rb') as f:
            files = {"file": (file_name, f, "application/pdf")}
            
            response = requests.post(
                f"{st.session_state.webhook_server_url}/api/v1/documents/upload",
                files=files,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                job_id = result["job_id"]
                
                # Add job to tracking
                if 'processing_jobs' not in st.session_state:
                    st.session_state.processing_jobs = []
                
                st.session_state.processing_jobs.append({
                    "job_id": job_id,
                    "file_name": file_name,
                    "started_at": time.time(),
                    "status": "pending"
                })
                
                st.success(f"✅ Document uploaded! Job ID: `{job_id}`")
                st.info(f"⏱️ Estimated processing time: {result['estimated_time']}")
                st.info("📊 Check the 'Document Processing Jobs' section below for progress")
                
                return True
            else:
                st.error(f"❌ Upload failed: {response.text}")
                return False
                
    except requests.exceptions.ConnectionError:
        st.error("❌ Webhook server not available. Starting local processing...")
        # Fallback to local processing
        try:
            # Step 1: Parse document
            with st.spinner(f"📄 Parsing {file_name}..."):
                parse_agent = DocumentParseAgent(data_folder="data")
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
    except Exception as e:
        st.error(f"❌ Error uploading document: {str(e)}")
        return False


def get_confidence_class(confidence: float) -> str:
    """Get CSS class based on confidence score"""
    if confidence >= 0.85:
        return "confidence-high"
    elif confidence >= 0.70:
        return "confidence-medium"
    else:
        return "confidence-low"


def render_cohere_monitoring():
    """Render Cohere reranking monitoring dashboard"""
    st.markdown("### 🎯 Cohere Reranking Monitor")
    
    try:
        # Check Cohere MCP status
        status_response = requests.get("http://localhost:8100/api/v1/status", timeout=2)
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            
            # Status indicator
            if status_data.get("configured"):
                st.success("✅ Cohere API is configured and ready")
            else:
                st.warning(f"⚠️ {status_data.get('message', 'Not configured')}")
                st.info(f"Get your free API key: {status_data.get('setup_url', 'https://dashboard.cohere.com/api-keys')}")
                
                # Instructions
                with st.expander("📖 How to Setup Cohere API Key"):
                    st.markdown("""
                    **Step 1:** Go to [Cohere Dashboard](https://dashboard.cohere.com/api-keys)
                    
                    **Step 2:** Sign up for a free account (no credit card required)
                    
                    **Step 3:** Create a new API key (Trial Key - 1000 requests/month)
                    
                    **Step 4:** Add to your `.env` file:
                    ```
                    COHERE_API_KEY=your_key_here
                    ```
                    
                    **Step 5:** Restart the Cohere MCP server
                    """)
        else:
            st.error("❌ Cohere MCP server not responding")
            return
        
        # Get statistics
        stats_response = requests.get("http://localhost:8100/api/v1/stats", timeout=2)
        
        if stats_response.status_code == 200 and status_data.get("configured"):
            stats_data = stats_response.json()
            
            if stats_data.get("total_requests", 0) > 0:
                # Display metrics
                st.markdown("#### 📊 Usage Statistics")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Requests", stats_data["total_requests"])
                
                with col2:
                    st.metric("Avg Duration", f"{stats_data['avg_duration_seconds']:.2f}s")
                
                with col3:
                    st.metric("Avg Input Docs", f"{stats_data['avg_input_documents']:.1f}")
                
                with col4:
                    st.metric("Avg Score", f"{stats_data.get('avg_relevance_score', 0):.3f}")
                
                # Recent history
                st.markdown("#### 📜 Recent Reranking Operations")
                
                history_response = requests.get("http://localhost:8100/api/v1/history?limit=10", timeout=2)
                
                if history_response.status_code == 200:
                    history_data = history_response.json()
                    
                    if history_data.get("history"):
                        for entry in reversed(history_data["history"]):
                            with st.expander(f"🔄 {entry['timestamp'][:19]} - Query: {entry['query'][:50]}..."):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.write(f"**Request ID:** `{entry['request_id']}`")
                                    st.write(f"**Query:** {entry['query']}")
                                    st.write(f"**Model:** {entry['model']}")
                                
                                with col2:
                                    st.write(f"**Input Documents:** {entry['input_count']}")
                                    st.write(f"**Output Documents:** {entry['output_count']}")
                                    st.write(f"**Duration:** {entry['duration_seconds']:.2f}s")
                                    st.write(f"**API Time:** {entry['api_duration_seconds']:.2f}s")
                                    st.write(f"**Top Score:** {entry['top_score']:.4f}")
                                    st.write(f"**Avg Score:** {entry['avg_score']:.4f}")
            else:
                st.info("📊 No reranking operations yet. Try asking a question with Cohere reranking enabled!")
        
        # Available models
        st.markdown("#### 🤖 Available Models")
        models_response = requests.get("http://localhost:8100/api/v1/models", timeout=2)
        
        if models_response.status_code == 200:
            models_data = models_response.json()
            
            for model in models_data["models"]:
                with st.expander(f"{'⭐ ' if model.get('recommended') else ''}{model['name']}"):
                    st.write(model["description"])
                    if model.get("recommended"):
                        st.success("✅ Recommended")
    
    except requests.exceptions.RequestException:
        st.error("❌ Cannot connect to Cohere MCP server. Make sure it's running on port 8100")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")


def render_job_monitor():
    """Render document processing job monitoring section"""
    
    if 'processing_jobs' not in st.session_state or not st.session_state.processing_jobs:
        return
    
    st.markdown("### 📊 Document Processing Jobs")
    
    jobs_to_remove = []
    
    for job in st.session_state.processing_jobs:
        try:
            # Fetch current status
            response = requests.get(
                f"{st.session_state.webhook_server_url}/api/v1/documents/jobs/{job['job_id']}",
                timeout=5
            )
            
            if response.status_code == 200:
                status_data = response.json()
                
                # Display job card
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.write(f"**{job['file_name']}**")
                        st.caption(f"Job ID: `{job['job_id'][:16]}...`")
                    
                    with col2:
                        if status_data['status'] == 'processing':
                            st.info("🔄 Processing...")
                        elif status_data['status'] == 'completed':
                            st.success("✅ Complete")
                        elif status_data['status'] == 'failed':
                            st.error("❌ Failed")
                        else:
                            st.warning("⏳ Pending")
                    
                    with col3:
                        st.metric("Progress", f"{status_data['progress']}%")
                    
                    # Progress bar
                    st.progress(status_data['progress'] / 100)
                    
                    # Message
                    st.caption(status_data['message'])
                    
                    # Show results if completed
                    if status_data['status'] == 'completed':
                        with st.expander("📊 View Results"):
                            result = status_data.get('result', {})
                            st.json(result)
                        
                        # Mark for removal
                        jobs_to_remove.append(job)
                    
                    # Show error if failed
                    if status_data['status'] == 'failed':
                        st.error(f"Error: {status_data.get('error', 'Unknown error')}")
                        jobs_to_remove.append(job)
                    
                    st.markdown("---")
        except:
            pass
    
    # Remove completed/failed jobs
    for job in jobs_to_remove:
        st.session_state.processing_jobs.remove(job)
    
    # Auto-refresh if there are active jobs
    if st.session_state.processing_jobs:
        time.sleep(3)
        st.rerun()


def stream_query_from_api(query: str, use_cohere: bool):
    """
    Stream query response from the streaming API
    """
    # Create placeholders for streaming content
    progress_container = st.container()
    answer_container = st.container()
    sources_container = st.container()
    sql_container = st.container()
    
    progress_messages = []
    answer_text = ""
    sources = []
    sql_details = None
    metadata = {}
    
    try:
        # Make streaming request using SSE
        response = requests.post(
            f"{st.session_state.streaming_api_url}/api/v1/query",
            json={
                "query": query,
                "stream": True,
                "use_cohere": use_cohere,
                "top_k": 10,
                "rerank_top_k": 5
            },
            stream=True,
            timeout=120
        )
        
        # Process stream
        for line in response.iter_lines():
            if line:
                # Decode line
                line_text = line.decode('utf-8')
                
                # SSE format: "data: {...}"
                if line_text.startswith('data: '):
                    json_str = line_text[6:]
                    data = json.loads(json_str)
                    
                    event_type = data.get('type')
                    
                    if event_type == 'progress':
                        # Update progress
                        message = data.get('message', '')
                        progress_messages.append(message)
                        
                        # Display latest 10 progress messages
                        with progress_container:
                            for msg in progress_messages[-10:]:
                                st.markdown(f"<small>{msg}</small>", unsafe_allow_html=True)
                    
                    elif event_type == 'answer':
                        # Display answer
                        answer_text = data.get('content', '')
                        metadata = data.get('metadata', {})
                        
                        with answer_container:
                            st.markdown("### 💬 Answer")
                            st.markdown(answer_text)
                            
                            # Show metadata
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Confidence", f"{metadata.get('confidence', 0):.0%}")
                            with col2:
                                st.metric("Retrieved", metadata.get('retrieved_chunks', 0))
                            with col3:
                                st.metric("Reranked", metadata.get('reranked_chunks', 0))
                            with col4:
                                st.metric("Duration", f"{metadata.get('duration_seconds', 0):.1f}s")
                    
                    elif event_type == 'sources':
                        # Display sources
                        sources = data.get('data', [])
                        
                        if sources:
                            with sources_container:
                                with st.expander(f"📚 View {len(sources)} Source Chunks"):
                                    for i, source in enumerate(sources, 1):
                                        st.markdown(f"**Source {i}:** `{source.get('chunk_id', 'Unknown')}`")
                                        st.caption(f"{source.get('chunk_type', 'unknown').upper()} from {source.get('source_document', 'Unknown')}")
                                        st.text(source.get('content', '')[:200] + "...")
                                        st.caption(f"Score: {source.get('final_score', 0):.3f}")
                                        st.markdown("---")
                    
                    elif event_type == 'sql_details':
                        # Display SQL details
                        sql_details = data.get('data', {})
                        
                        if sql_details:
                            with sql_container:
                                with st.expander("💾 View SQL Execution Details"):
                                    st.markdown("### Generated SQL Queries")
                                    for i, query in enumerate(sql_details.get('queries', []), 1):
                                        st.markdown(f"**Query {i}:**")
                                        st.code(query, language="sql")
                                    
                                    st.markdown("### SQL Results")
                                    st.markdown(sql_details.get('answer', ''))
                    
                    elif event_type == 'complete':
                        # Clear progress and show completion
                        with progress_container:
                            st.success("✅ " + data.get('message', 'Complete'))
                    
                    elif event_type == 'error':
                        # Show error
                        with progress_container:
                            st.error("❌ " + data.get('message', 'Error occurred'))
        
        return {
            'answer': answer_text,
            'sources': sources,
            'metadata': metadata,
            'sql_details': sql_details
        }
        
    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out")
        return None
    except requests.exceptions.ConnectionError:
        st.error("❌ Streaming API server not available. Please start it first.")
        return None
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None


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
    
    # MCP Server Status Indicator
    mcp_status = check_mcp_status()
    if mcp_status == 'connected':
        st.success("🟢 MCP Server: Online", icon="✅")
    elif mcp_status == 'disconnected':
        st.warning("🟡 MCP Server: Offline (Fallback to direct DB)", icon="⚠️")
    else:
        st.error("🔴 MCP Server: Error", icon="❌")
    
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Add Cohere Monitor in sidebar
        with st.expander("🎯 Cohere Reranking Monitor", expanded=False):
            render_cohere_monitoring()
            
            # Add refresh button
            if st.button("🔄 Refresh Cohere Stats", key="refresh_cohere"):
                st.rerun()
        
        st.markdown("---")
        
        # MCP Status in sidebar
        st.subheader("🔌 MCP Server Status")
        if mcp_status == 'connected':
            st.success("✅ Online")
        elif mcp_status == 'disconnected':
            st.warning("⚠️ Offline")
            if st.button("🔄 Reconnect MCP", use_container_width=True):
                check_mcp_status()
                st.rerun()
        else:
            st.error("❌ Error")
        
        st.markdown("---")
        
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
        
        # Log Files
        st.header("📝 Log Files")
        query_results_folder = Path("query results")
        if query_results_folder.exists():
            log_files = sorted(query_results_folder.glob("*.txt"), key=lambda x: x.stat().st_mtime, reverse=True)
            if log_files:
                st.write(f"Recent logs ({len(log_files)} total):")
                for log_file in log_files[:5]:  # Show last 5
                    file_size = log_file.stat().st_size / 1024  # KB
                    st.text(f"📄 {log_file.name} ({file_size:.1f} KB)")
            else:
                st.info("No log files yet")
        
        st.markdown("---")
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    
    # Main chat interface
    st.header("💬 Chat Interface")
    
    # Reranking method selector (above chat)
    col_rerank1, col_rerank2 = st.columns([3, 2])
    with col_rerank1:
        st.markdown("#### Reranking Method")
    with col_rerank2:
        # Check Cohere status
        try:
            cohere_response = requests.get(
                f"{st.session_state.cohere_mcp_url}/api/v1/status",
                timeout=2
            )
            if cohere_response.status_code == 200:
                cohere_status = cohere_response.json()
                cohere_available = cohere_status.get('configured', False)
            else:
                cohere_available = False
        except:
            cohere_available = False
    
    # Reranking method toggle
    rerank_method = st.radio(
        "Select reranking method:",
        options=["LLM-based (Default)", "Cohere API"],
        horizontal=True,
        disabled=not cohere_available,
        help="Cohere API provides faster and more accurate reranking but requires an API key" if cohere_available else "Cohere API not available. Please start Cohere MCP server and configure API key."
    )
    
    st.session_state.use_cohere_rerank = (rerank_method == "Cohere API")
    
    if not cohere_available and rerank_method == "Cohere API":
        st.warning("⚠️ Cohere API not configured. Get your free API key at: https://dashboard.cohere.com/api-keys")
    
    st.markdown("---")
    
    # Job monitoring section
    render_job_monitor()
    
    # Add tabs for different views
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 MCP Status", "📝 Live Logs"])
    
    with tab1:
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
    
    # Checkbox for streaming
    use_streaming = st.checkbox(
        "🌊 Use Streaming API (real-time progress updates)",
        value=True,
        help="Enable to see real-time progress as your query is processed"
    )
    
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
        # Add user message to history
        st.session_state.chat_history.append({
            'role': 'user',
            'content': user_input
        })
        
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Process with streaming or standard method
        with st.chat_message("assistant"):
            if use_streaming:
                # Use streaming API
                result = stream_query_from_api(user_input, st.session_state.use_cohere_rerank)
                
                if result:
                    # Add to chat history
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        'content': result['answer'],
                        'confidence_score': result['metadata'].get('confidence', 0),
                        'retrieved_chunks_count': result['metadata'].get('retrieved_chunks', 0),
                        'reranked_chunks_count': result['metadata'].get('reranked_chunks', 0),
                        'sql_executed': result['metadata'].get('sql_executed', False),
                        'duration_seconds': result['metadata'].get('duration_seconds', 0),
                        'reranking_method': result['metadata'].get('reranking_method', 'LLM-based'),
                        'rag_sources': result.get('sources', []),
                        'sql_queries': result.get('sql_details', {}).get('queries', []) if result.get('sql_details') else [],
                        'sql_answer': result.get('sql_details', {}).get('answer', '') if result.get('sql_details') else '',
                        'final_answer': result['answer'],
                        'process_log': []
                    })
                    
                    st.rerun()
            
            else:
                # Use standard orchestrator
                if st.session_state.orchestrator is None:
                    st.error("⚠️ Please initialize the AI agents first using the sidebar button!")
                else:
                    with st.spinner("🤔 Processing your question..."):
                        try:
                            result = st.session_state.orchestrator.process_user_query(
                                user_input,
                                use_cohere_rerank=st.session_state.use_cohere_rerank
                            )
                            
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
    
    with tab2:
        st.header("📊 MCP Server Status")
        
        # Check all MCP servers
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 📡 Webhook Server")
            try:
                response = requests.get("http://localhost:8080/health", timeout=2)
                if response.status_code == 200:
                    st.success("✅ Online")
                else:
                    st.error("❌ Error")
            except:
                st.error("❌ Offline")
        
        with col2:
            st.markdown("### 🌊 Streaming API")
            try:
                response = requests.get("http://localhost:8090/health", timeout=2)
                if response.status_code == 200:
                    st.success("✅ Online")
                else:
                    st.error("❌ Error")
            except:
                st.error("❌ Offline")
        
        with col3:
            st.markdown("### 🎯 Cohere MCP")
            try:
                response = requests.get("http://localhost:8100/health", timeout=2)
                if response.status_code == 200:
                    st.success("✅ Online")
                else:
                    st.error("❌ Error")
            except:
                st.error("❌ Offline")
        
        st.markdown("---")
        
        # Detailed Cohere monitoring
        render_cohere_monitoring()
    
    with tab3:
        st.header("📝 Live Server Logs")
        
        server_choice = st.selectbox(
            "Select Server",
            ["Cohere MCP", "Webhook Server", "Streaming API"],
            key="log_server_choice"
        )
        
        if server_choice == "Cohere MCP":
            st.info("📡 Viewing Cohere MCP Server logs")
            st.markdown("""
            **💡 Tip:** Open the Cohere MCP console window to see detailed real-time logs.
            
            Logs include:
            - 📝 Query text
            - 📚 Number of documents
            - ⚡ API call duration
            - 🎯 Reranking scores
            - 📊 Document previews
            """)
            
            # Show recent history from API
            try:
                history_response = requests.get("http://localhost:8100/api/v1/history?limit=5", timeout=2)
                
                if history_response.status_code == 200:
                    history_data = history_response.json()
                    
                    st.markdown("### 📜 Recent Operations (Last 5)")
                    
                    for entry in reversed(history_data.get("history", [])):
                        st.code(f"""[{entry['timestamp']}] Reranking Request
Request ID: {entry['request_id']}
Query: {entry['query']}
Input: {entry['input_count']} docs → Output: {entry['output_count']} docs
Duration: {entry['duration_seconds']:.2f}s (API: {entry['api_duration_seconds']:.2f}s)
Top Score: {entry['top_score']:.4f}
Avg Score: {entry['avg_score']:.4f}
{'-' * 60}""", language="log")
                else:
                    st.warning("Cannot fetch recent operations")
            except:
                st.error("Cannot connect to Cohere MCP server")
        
        elif server_choice == "Webhook Server":
            st.info("📡 Viewing Webhook Server logs")
            st.markdown("**💡 Tip:** Check the Webhook Server console window for document processing logs.")
        
        elif server_choice == "Streaming API":
            st.info("📡 Viewing Streaming API logs")
            st.markdown("**💡 Tip:** Check the Streaming API console window for query processing logs.")
        
        # Auto-refresh
        st.markdown("---")
        auto_refresh = st.checkbox("Auto-refresh (every 10s)", key="auto_refresh_logs")
        if auto_refresh:
            time.sleep(10)
            st.rerun()
    
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
