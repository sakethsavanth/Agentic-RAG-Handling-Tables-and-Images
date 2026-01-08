# Query Logging System

This folder contains comprehensive logs of all queries and agent operations.

## What Gets Logged

All output from the system is automatically captured to text files, including:

- **Retrieval Process**: Score distributions, chunk counts, similarity scores
- **Reranking Process**: Type weights, LLM relevance scoring, final rankings
- **Text-to-SQL**: SQL classification, query generation, execution results
- **Answer Comparison**: Confidence scores, agreement analysis
- **Full Process Logs**: Timestamps, agent execution details, errors

## Log File Naming

Log files are automatically named with timestamps and query context:

- `main_pipeline_YYYYMMDD_HHMMSS.txt` - Main pipeline execution logs
- `query_YYYYMMDD_HHMMSS_<query_snippet>.txt` - Individual query logs

## How It Works

The system uses a `TeeLogger` that:
1. Displays all output in the terminal/console as normal
2. Simultaneously writes everything to a timestamped text file
3. Flushes data immediately to ensure no logs are lost

## Usage Examples

### Main Pipeline
```bash
python main.py
```
Creates: `query results/main_pipeline_20260107_143022.txt`

### Command Line Chatbot
```bash
python chatbot_cli.py
```
Each query creates a separate log file.

### Streamlit App
```bash
streamlit run streamlit_app.py
```
Logs are saved for each query while the app is running.

## Viewing Logs

Simply open any `.txt` file in this folder to see the complete execution trace:

```
================================================================================
💬 PROCESSING USER QUERY
================================================================================
Query: What is the WASH mortality for African Region?

📊 Score distribution:
   Highest: 0.3128
   Lowest: 0.0417
   Average: 0.1201

[... complete trace ...]
```

## Benefits

✅ **Complete Transparency** - Every step is recorded  
✅ **Debugging** - Easy to trace errors and performance  
✅ **Audit Trail** - Full history of queries and responses  
✅ **No Console Limitations** - Terminal buffer size doesn't matter  
✅ **Shareable** - Send log files for review or support  

## Notes

- Log files are created in real-time as the program runs
- All emoji, formatting, and special characters are preserved
- Files are encoded in UTF-8 to support all characters
- Logs are never truncated - complete output is always saved
