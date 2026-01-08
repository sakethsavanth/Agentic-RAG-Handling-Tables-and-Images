# Logging System Implementation

## Overview

A comprehensive logging system has been implemented to capture all console output to text files in the **'query results'** folder. This solves the terminal buffer limitation issue and provides complete audit trails.

## Key Features

✅ **Dual Output** - Everything appears in console AND is saved to file  
✅ **Complete Capture** - All emojis, formatting, scores, and details preserved  
✅ **Automatic Timestamping** - Each log file has a unique timestamp  
✅ **Query-Based Naming** - Log files include sanitized query text for easy identification  
✅ **Real-Time Writing** - Logs are flushed immediately, no data loss  
✅ **UTF-8 Encoding** - Supports all special characters and emojis  

## Implementation

### Core Component: `utils/logging_utils.py`

**TeeLogger Class**
- Acts like Unix 'tee' command - splits output to console and file
- Implements context manager protocol for clean setup/teardown
- Redirects `sys.stdout` to capture all print statements
- Automatically creates 'query results' folder if needed

**Helper Functions**
- `get_log_filename()` - Generates safe, timestamped filenames with query context

### Updated Files

1. **`main.py`** - Main pipeline now logs all agent execution
2. **`chatbot_orchestrator.py`** - Query processing logged with enable_logging flag
3. **`streamlit_app.py`** - Shows recent log files in sidebar
4. **`chatbot_cli.py`** - NEW command-line chatbot with full logging

## Usage

### Main Pipeline
```python
from utils.logging_utils import TeeLogger, get_log_filename

log_filename = get_log_filename(prefix="main_pipeline")
with TeeLogger(log_folder="query results", log_name=log_filename):
    # All print statements here go to console AND file
    print("Starting pipeline...")
    # ... rest of code ...
```

### Chatbot Orchestrator
```python
orchestrator = ChatbotOrchestrator(
    retrieval_top_k=10,
    rerank_top_k=5,
    enable_logging=True  # Enable file logging
)

result = orchestrator.process_user_query("What is the WASH mortality?")
# Automatically creates: query_20260107_143022_What_is_the_WASH_mortality.txt
```

### Command Line Chatbot
```bash
python chatbot_cli.py
```
Each query automatically gets its own log file.

### Streamlit App
```bash
streamlit run streamlit_app.py
```
- Logs created for each query
- View recent logs in sidebar under "📝 Log Files"

## Log File Structure

### Naming Convention
- `main_pipeline_YYYYMMDD_HHMMSS.txt` - Pipeline execution
- `query_YYYYMMDD_HHMMSS_<query>.txt` - Individual queries

### Content Example
```
📝 Logging to: query results\query_20260107_143022_WASH_mortality.txt

================================================================================
💬 PROCESSING USER QUERY
================================================================================
Query: What is the WASH mortality for African Region?

================================================================================
🚀 STARTING RETRIEVAL WORKFLOW
================================================================================
Query: What is the WASH mortality for African Region?
Top K: 18

[1/18] Chunk: WHO 2025_chunk_5 (text)
   Similarity: 0.3128

📊 Score distribution:
   Highest: 0.3128
   Lowest: 0.0417
   Average: 0.1201

================================================================================
✅ RETRIEVAL WORKFLOW COMPLETED
================================================================================
```

## Testing

Run the test script to see logging in action:
```bash
python test_logging.py
```

This creates example log files demonstrating the feature.

## Benefits

### For Development
- **Full Debugging** - Complete execution trace available
- **Performance Analysis** - See timing and scores for all operations
- **Error Tracking** - Stack traces and error messages preserved

### For Users
- **Transparency** - See exactly what the system did
- **Documentation** - Keep records of queries and responses
- **Sharing** - Send log files for support or collaboration

### For Operations
- **Audit Trail** - Complete history of all operations
- **No Data Loss** - Terminal buffer limitations overcome
- **Easy Review** - Simple text files, searchable and shareable

## Directory Structure

```
query results/
├── README.md                                    # Folder documentation
├── main_pipeline_20260107_143022.txt           # Pipeline logs
├── query_20260107_143530_WASH_mortality.txt    # Query logs
└── query_20260107_144215_pillar_scores.txt     # More query logs
```

## Notes

- Log files are created with UTF-8 encoding for full character support
- Files are flushed immediately to ensure data is written even if program crashes
- Context manager ensures proper cleanup and file closure
- Original stdout is preserved and restored after logging
- No performance impact - writing to disk happens asynchronously via OS buffering

## Future Enhancements

Possible improvements:
- Log rotation (archive old logs automatically)
- JSON structured logging alongside text logs
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- Integration with cloud logging services
- Searchable log viewer in Streamlit app
