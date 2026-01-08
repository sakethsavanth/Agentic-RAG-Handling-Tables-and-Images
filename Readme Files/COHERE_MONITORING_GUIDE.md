# Cohere Reranking Monitoring Guide

## ✅ Enhancements Implemented

All three monitoring enhancements have been successfully implemented:

### 1. ✅ Detailed Logging in Cohere MCP Server

**File**: `cohere_mcp.py`

**Features Added**:
- Real-time console logging with detailed information
- Request tracking with unique IDs
- Performance metrics (API duration, total duration)
- Document previews in logs
- Score analysis (top score, average score)
- History tracking (last 100 requests stored in memory)

**What You'll See in Console**:
```
================================================================================
🔄 NEW RERANKING REQUEST [rerank_1704723456789]
================================================================================
📝 Query: What is the pillar score for Indonesia?
📚 Documents received: 10
🎯 Top K requested: 5
🤖 Model: rerank-english-v3.0
🔌 Connecting to Cohere API...
✅ Cohere client ready

📥 INPUT DOCUMENTS:
   Doc 1: Indonesia has a pillar score of 75.3...
          Source: business_readiness_report.pdf
          Chunk ID: chunk_12345
   ... and 7 more documents

⚡ Calling Cohere Rerank API...
✅ Cohere API responded in 1.23s

📤 RERANKED RESULTS (Top 5):

   Rank 1:
   ├─ Score: 0.9876
   ├─ Original Index: 3
   ├─ Chunk ID: chunk_12347
   ├─ Source: business_readiness_report.pdf
   └─ Preview: Indonesia achieved a pillar score of 75.3...

⏱️  Total processing time: 1.45s
📊 Average score: 0.8234
================================================================================
```

### 2. ✅ Cohere Monitoring Dashboard in Streamlit

**File**: `streamlit_app.py`

**Location**: Sidebar → "🎯 Cohere Reranking Monitor" expander

**Features**:
- **Status Indicator**: Shows if Cohere API is configured and ready
- **Usage Statistics**: 
  - Total requests
  - Average duration
  - Average input documents
  - Average relevance score
- **Recent Operations**: Expandable history of last 10 reranking operations
- **Model Information**: Available Cohere models with descriptions
- **Setup Instructions**: Step-by-step guide to get free API key

**How to Access**:
1. Open Streamlit UI
2. Look at left sidebar
3. Click "🎯 Cohere Reranking Monitor" expander
4. Click "🔄 Refresh Cohere Stats" to update

### 3. ✅ Live Logs Viewer Tab

**File**: `streamlit_app.py`

**Location**: Main interface → "📝 Live Logs" tab

**Features**:
- **Server Selection**: Choose which server logs to view
  - Cohere MCP
  - Webhook Server
  - Streaming API
- **Recent Operations Display**: Shows last 5 operations with:
  - Request ID
  - Query text
  - Document counts
  - Duration metrics
  - Relevance scores
- **Auto-Refresh**: Option to automatically refresh every 10 seconds
- **Console Window Tips**: Guidance on viewing detailed real-time logs

---

## 🚀 How to Use the Monitoring Features

### Viewing in Console (Real-Time)

1. **Launch the servers**:
   ```powershell
   .\venv\Scripts\Activate.ps1
   python launch_mcp_servers.py
   ```

2. **Watch the Cohere MCP console window** - You'll see detailed logs for each reranking request

### Viewing in Streamlit UI

1. **Start Streamlit**:
   ```powershell
   streamlit run streamlit_app.py
   ```

2. **Access monitoring in three places**:

   **A. Sidebar Monitor** (Quick view):
   - Expand "🎯 Cohere Reranking Monitor" in sidebar
   - View current status, stats, and recent history
   - Click "Refresh" button to update

   **B. MCP Status Tab** (Detailed):
   - Click "📊 MCP Status" tab
   - See all server statuses
   - Full Cohere monitoring dashboard

   **C. Live Logs Tab** (Historical):
   - Click "📝 Live Logs" tab
   - Select "Cohere MCP" from dropdown
   - View last 5 operations in log format
   - Enable auto-refresh for live updates

---

## 📊 New API Endpoints

### 1. History Endpoint
```bash
GET http://localhost:8100/api/v1/history?limit=10
```

**Response**:
```json
{
  "history": [
    {
      "request_id": "rerank_1704723456789",
      "timestamp": "2026-01-08T10:30:45.123456",
      "query": "What is the pillar score for Indonesia?",
      "input_count": 10,
      "output_count": 5,
      "model": "rerank-english-v3.0",
      "duration_seconds": 1.45,
      "api_duration_seconds": 1.23,
      "top_score": 0.9876,
      "avg_score": 0.8234
    }
  ],
  "total_requests": 42
}
```

### 2. Statistics Endpoint
```bash
GET http://localhost:8100/api/v1/stats
```

**Response**:
```json
{
  "total_requests": 42,
  "avg_duration_seconds": 1.35,
  "avg_api_duration_seconds": 1.15,
  "avg_input_documents": 12.3,
  "avg_output_documents": 5.0,
  "avg_relevance_score": 0.8156,
  "most_recent": { ... }
}
```

### 3. Status Endpoint (Enhanced)
```bash
GET http://localhost:8100/api/v1/status
```

**Response (Configured)**:
```json
{
  "status": "operational",
  "configured": true,
  "api_accessible": true,
  "message": "Cohere API is ready"
}
```

**Response (Not Configured)**:
```json
{
  "status": "not_configured",
  "configured": false,
  "api_accessible": false,
  "message": "COHERE_API_KEY not found in environment variables...",
  "setup_url": "https://dashboard.cohere.com/api-keys"
}
```

---

## 🧪 Testing the Monitoring

### Test 1: Check Status in UI
1. Open Streamlit UI
2. Sidebar → Expand "🎯 Cohere Reranking Monitor"
3. Should see "✅ Cohere API is configured and ready"

### Test 2: Trigger Reranking
1. In Streamlit, select "Cohere API" for reranking method
2. Ask a question: "What is the pillar score for Indonesia?"
3. Watch:
   - **Cohere console**: Detailed logs appear in real-time
   - **Streamlit sidebar**: Stats update (click Refresh)
   - **Live Logs tab**: New entry appears

### Test 3: View Statistics
1. After asking a few questions
2. Go to "📊 MCP Status" tab
3. View aggregated statistics:
   - Total requests
   - Average durations
   - Average scores

### Test 4: Check History
1. Go to "📝 Live Logs" tab
2. Select "Cohere MCP"
3. See last 5 operations in log format
4. Enable auto-refresh to see live updates

---

## 📈 What to Monitor

### Performance Metrics
- **API Duration**: Should be < 2 seconds
- **Total Duration**: Should be < 3 seconds
- **Relevance Scores**: Higher is better (0.8+ is good)

### Usage Tracking
- **Total Requests**: Track against free tier limit (1000/month)
- **Average Input Docs**: Optimize to reduce API calls
- **Average Output Docs**: Ensure you're getting enough results

### Quality Indicators
- **Top Score**: Should be > 0.9 for highly relevant results
- **Average Score**: Should be > 0.7 for good overall quality
- **Score Distribution**: Check if scores drop significantly after top results

---

## 🎯 Current Status

✅ **Enhancement 1**: Detailed logging implemented and working
✅ **Enhancement 2**: Monitoring dashboard in sidebar working
✅ **Enhancement 3**: Live logs tab with auto-refresh working

**API Status**: ✅ Configured and operational
**Free Tier**: 1000 requests/month (check usage in dashboard)

---

## 💡 Tips

1. **Keep console windows open** to see real-time detailed logs
2. **Use auto-refresh** in Live Logs tab for continuous monitoring
3. **Check sidebar regularly** for quick stats during testing
4. **Monitor API usage** to stay within free tier limits
5. **Compare scores** between Cohere and LLM-based reranking

---

## 🔧 Troubleshooting

### Issue: "Cannot connect to Cohere MCP server"
**Solution**: 
- Ensure server is running: Check console window or run `python launch_mcp_servers.py`
- Check port 8100 is not blocked

### Issue: "No reranking operations yet"
**Solution**:
- Select "Cohere API" reranking method in UI
- Ask a question to trigger reranking
- Verify Cohere is being used (check logs)

### Issue: Stats not updating
**Solution**:
- Click "🔄 Refresh Cohere Stats" button
- Or enable auto-refresh in Live Logs tab

---

## 📚 Related Files

- `cohere_mcp.py` - Enhanced MCP server with logging
- `streamlit_app.py` - UI with monitoring dashboard and live logs
- `agents/reranking_agent.py` - Calls Cohere MCP for reranking
- `.env` - Contains COHERE_API_KEY configuration

---

**Setup Complete!** 🎉 All three monitoring enhancements are now active and ready to use.
