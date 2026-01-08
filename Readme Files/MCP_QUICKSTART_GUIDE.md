# 🚀 MCP-Enhanced Multimodal RAG System - Quick Start Guide

## Overview

This guide will help you start all the MCP servers and the Streamlit UI for the enhanced RAG system with:
- ✅ **Webhook Server** - Asynchronous document processing
- ✅ **Streaming API** - Real-time query progress updates
- ✅ **Cohere MCP** - Optional Cohere-based reranking

---

## Prerequisites

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root with:

```env
# PostgreSQL Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database
DB_USER=your_user
DB_PASSWORD=your_password

# AWS Bedrock (for LLM and embeddings)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1

# Cohere API (Optional - for enhanced reranking)
COHERE_API_KEY=your_cohere_api_key
```

**Get your free Cohere API key**: https://dashboard.cohere.com/api-keys

---

## 🎯 Quick Start (All-in-One)

### Option 1: Launch All Servers at Once

```bash
python launch_mcp_servers.py
```

This will start:
- Webhook Server on `http://localhost:8080`
- Streaming API on `http://localhost:8090`
- Cohere MCP on `http://localhost:8100`

### Option 2: Start Streamlit UI

In a **new terminal**:

```bash
streamlit run streamlit_app.py
```

The UI will open at `http://localhost:8501`

---

## 🔧 Manual Start (Individual Servers)

If you prefer to start servers individually:

### Terminal 1: Webhook Server
```bash
python webhook_server.py
```
- **Purpose**: Asynchronous document processing
- **Port**: 8080
- **API Docs**: http://localhost:8080/docs

### Terminal 2: Streaming API
```bash
python streaming_api.py
```
- **Purpose**: Real-time query processing with SSE
- **Port**: 8090
- **API Docs**: http://localhost:8090/docs

### Terminal 3: Cohere MCP (Optional)
```bash
python cohere_mcp.py
```
- **Purpose**: Cohere-based reranking
- **Port**: 8100
- **API Docs**: http://localhost:8100/docs
- **Note**: Requires `COHERE_API_KEY` in `.env`

### Terminal 4: Streamlit UI
```bash
streamlit run streamlit_app.py
```
- **Purpose**: Main chat interface
- **Port**: 8501

---

## 📋 Features Guide

### 1. Asynchronous Document Processing

**How to use:**
1. Open Streamlit UI
2. Go to sidebar → "Upload New Document"
3. Select a PDF file
4. Click "📤 Process Document"
5. Monitor progress in "Document Processing Jobs" section

**What happens:**
- Document uploads to Webhook Server immediately
- Processing happens in background
- Real-time progress updates (0-100%)
- Notification when complete

---

### 2. Streaming Query API

**How to use:**
1. In chat interface, ensure "🌊 Use Streaming API" is **checked**
2. Type your question
3. Click "Send 🚀"

**What you'll see:**
```
🔍 Classifying your query...
✅ Detected SQL query needed
💾 Generating SQL...
✅ SQL generated: SELECT country, score...
⚡ Executing query...
✅ Retrieved 50 rows
📊 Formatting results...
💬 Answer generated
```

**Benefits:**
- Real-time progress updates
- No more waiting in silence
- See exactly what's happening

---

### 3. Cohere Reranking

**How to use:**
1. Ensure Cohere MCP server is running
2. Add `COHERE_API_KEY` to `.env`
3. In chat interface, select **"Cohere API"** radio button
4. Type your question

**What it does:**
- Uses Cohere's reranking API instead of LLM
- Faster and more accurate reranking
- Free tier: 1000 requests/month

**Comparison:**

| Method | Speed | Accuracy | Cost |
|--------|-------|----------|------|
| LLM-based | Slower | Good | AWS Bedrock calls |
| Cohere API | Faster | Excellent | Free tier available |

---

## 🧪 Testing the Setup

### 1. Test Webhook Server

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "Document Processing Webhook Server",
  "active_jobs": 0,
  "total_jobs": 0
}
```

### 2. Test Streaming API

```bash
curl http://localhost:8090/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "Streaming Query API",
  "orchestrator_initialized": false
}
```

### 3. Test Cohere MCP

```bash
curl http://localhost:8100/api/v1/status
```

Expected response (if configured):
```json
{
  "status": "operational",
  "configured": true,
  "api_accessible": true,
  "message": "Cohere API is ready"
}
```

---

## 📊 Monitoring & Logs

### Server Logs

Each server outputs logs to console:
- **Webhook Server**: Document processing progress
- **Streaming API**: Query processing steps
- **Cohere MCP**: Reranking API calls

### Query Logs

Query results are saved to:
```
query results/
  ├── query_20260107_143049_List_the_pillar_scores_of_5_countries_.txt
  └── ...
```

### Job Tracking

Active document processing jobs can be viewed:
1. In Streamlit UI → "Document Processing Jobs" section
2. Via API: `GET http://localhost:8080/api/v1/documents/jobs`

---

## 🐛 Troubleshooting

### Webhook Server Not Available

**Symptom**: "Webhook server not available" error in UI

**Solution**:
1. Check if server is running: `curl http://localhost:8080/health`
2. Start server: `python webhook_server.py`
3. The system will fallback to local processing if webhook unavailable

### Streaming API Connection Error

**Symptom**: "Streaming API server not available"

**Solution**:
1. Start streaming server: `python streaming_api.py`
2. Uncheck "Use Streaming API" to use standard processing

### Cohere API Not Configured

**Symptom**: Cohere option is disabled

**Solution**:
1. Get API key: https://dashboard.cohere.com/api-keys
2. Add to `.env`: `COHERE_API_KEY=your_key_here`
3. Restart Cohere MCP server

### Port Already in Use

**Symptom**: "Address already in use" error

**Solution**:
```bash
# Windows
netstat -ano | findstr :8080
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8080
kill -9 <PID>
```

---

## 🔗 API Documentation

### Webhook Server APIs

- **POST** `/api/v1/documents/upload` - Upload document for processing
- **GET** `/api/v1/documents/jobs/{job_id}` - Get job status
- **GET** `/api/v1/documents/jobs` - List all jobs
- **DELETE** `/api/v1/documents/jobs/{job_id}` - Delete job

Full docs: http://localhost:8080/docs

### Streaming API

- **POST** `/api/v1/query` - Query with streaming
  - Body: `{"query": "...", "stream": true, "use_cohere": false}`

Full docs: http://localhost:8090/docs

### Cohere MCP APIs

- **POST** `/api/v1/rerank` - Rerank documents
- **GET** `/api/v1/models` - List available models
- **GET** `/api/v1/status` - Check API status

Full docs: http://localhost:8100/docs

---

## 🎓 Usage Examples

### Example 1: Upload Document via Webhook

```python
import requests

files = {"file": open("document.pdf", "rb")}
response = requests.post(
    "http://localhost:8080/api/v1/documents/upload",
    files=files
)

job_id = response.json()["job_id"]
print(f"Job ID: {job_id}")

# Poll for status
import time
while True:
    status = requests.get(
        f"http://localhost:8080/api/v1/documents/jobs/{job_id}"
    ).json()
    
    print(f"Status: {status['status']} ({status['progress']}%)")
    
    if status['status'] in ['completed', 'failed']:
        break
    
    time.sleep(3)
```

### Example 2: Query with Streaming

```python
import requests
import json

response = requests.post(
    "http://localhost:8090/api/v1/query",
    json={
        "query": "What is the pillar score for Indonesia?",
        "stream": True,
        "use_cohere": False
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        line_text = line.decode('utf-8')
        if line_text.startswith('data: '):
            data = json.loads(line_text[6:])
            print(f"{data['type']}: {data.get('message', '')}")
```

### Example 3: Rerank with Cohere

```python
import requests

response = requests.post(
    "http://localhost:8100/api/v1/rerank",
    json={
        "query": "business readiness factors",
        "documents": [
            {"text": "Regulatory environment is key...", "chunk_id": "doc1"},
            {"text": "Infrastructure development...", "chunk_id": "doc2"}
        ],
        "top_k": 5,
        "model": "rerank-english-v3.0"
    }
)

result = response.json()
for doc in result['reranked_documents']:
    print(f"{doc['chunk_id']}: {doc['cohere_score']:.3f}")
```

---

## 📞 Support

For issues or questions:
1. Check troubleshooting section above
2. Review server logs in terminal
3. Check API docs at `/docs` endpoints
4. Verify environment variables in `.env`

---

## 🎉 You're All Set!

Your MCP-enhanced RAG system is now ready to use with:
- ✅ Asynchronous document processing
- ✅ Real-time streaming queries
- ✅ Optional Cohere reranking
- ✅ Full API access

Happy querying! 🚀
