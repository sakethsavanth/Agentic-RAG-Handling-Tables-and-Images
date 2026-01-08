# Quick Start: Query Logging

## What's New?

All console output is now automatically saved to text files in the **'query results'** folder!

## How to Use

### 1. Run Main Pipeline
```bash
python main.py
```
✅ Creates: `query results/main_pipeline_[timestamp].txt`

### 2. Run Command-Line Chatbot
```bash
python chatbot_cli.py
```
✅ Each query creates its own log file

### 3. Run Streamlit UI
```bash
streamlit run streamlit_app.py
```
✅ View recent logs in sidebar  
✅ Each query automatically logged

### 4. Test Logging System
```bash
python test_logging.py
```
✅ See example logs created

## What Gets Logged?

**Everything you see in the terminal:**
- 📊 Score distributions and metrics
- 🔍 Retrieval and reranking details  
- 🤖 LLM calls and responses
- 💾 SQL query generation and execution
- ⚖️ Answer comparison and confidence scores
- ⏱️ Timing information
- ❌ Errors and stack traces

**Example:**
```
================================================================================
🚀 STARTING RETRIEVAL WORKFLOW
================================================================================
Query: What is the WASH mortality for African Region?

📊 Score distribution:
   Highest: 0.3128
   Lowest: 0.0417
   Average: 0.1201

✅ Retrieved 18 chunks
```

## Benefits

✅ **No Terminal Limitations** - Complete logs saved regardless of buffer size  
✅ **Easy Debugging** - Review full execution trace anytime  
✅ **Audit Trail** - Keep records of all queries  
✅ **Shareable** - Send log files to others  

## Finding Your Logs

All logs are in: `query results/`

Files are named with timestamps:
- `main_pipeline_20260107_143022.txt`
- `query_20260107_143530_What_is_WASH_mortality.txt`

## Tips

- Logs include ALL emoji and formatting 📊 ✅ 🔍
- Files are UTF-8 encoded for full character support
- Search logs with any text editor or grep
- Logs are written in real-time (not buffered)

That's it! Logging happens automatically. 🎉
