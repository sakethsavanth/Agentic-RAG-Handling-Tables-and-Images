# 🚀 MCP Quick Start Guide

## What Changed?

Your project now uses **proper MCP (Model Context Protocol)** for all database operations:

- ✅ **stdio-based client-server architecture**
- ✅ **MCP server handles all SQL operations**
- ✅ **Agents communicate via JSON-RPC protocol**
- ✅ **Real-time server status in Streamlit UI**
- ✅ **All generated tables exported to files**

## Quick Start (3 Steps)

### Step 1: Start the MCP Server

**Open a NEW terminal** and run:

```bash
python start_mcp_server.py
```

You should see:
```
================================================================================
🚀 Starting FastMCP SQL Executor Server
================================================================================

✅ Database initialized successfully

🎧 Server is now listening for connections...
================================================================================
```

⚠️ **Keep this terminal open!** The server must run continuously.

---

### Step 2: Run Your Application

**In a DIFFERENT terminal**, start your application:

#### Option A: Streamlit UI
```bash
streamlit run streamlit_app.py
```

#### Option B: CLI Chatbot
```bash
python test scripts/run_chatbot.py
```

#### Option C: Test MCP
```bash
python "test scripts/test_mcp_implementation.py"
```

---

### Step 3: Check MCP Status

**In Streamlit UI:**
- Look for the status indicator at the top:
  - 🟢 **Online** = MCP working perfectly
  - 🟡 **Offline** = Using fallback (still works)
  - 🔴 **Error** = Check MCP server terminal

**In CLI:**
- Watch for "✅ MCP server connected" messages
- Logs will show "via MCP" when using the server

---

## What's Different Now?

### Before (Direct Database)
```
Agent → PostgreSQL (direct connection)
```

### After (MCP Architecture)
```
Agent → MCP Client (stdio) → MCP Server → PostgreSQL
```

---

## New Features

### 1. 📁 Generated Tables Export

All tables created from documents are now saved to:
```
generated_tables/
├── tables_Business_Ready_2025_20260107_153045.sql
└── visualization_tables_WHO_2025_20260107_153112.sql
```

Each file contains:
- Complete SQL statements
- Table metadata
- Source information
- Timestamps

**To view:**
```bash
cat "generated_tables/tables_*.sql"
```

### 2. 🔌 MCP Server Status

The Streamlit UI shows real-time MCP status:

- **Sidebar**: MCP status with reconnect button
- **Header**: Global status indicator
- **Auto-reconnect**: Click "🔄 Reconnect MCP" if offline

### 3. 🎯 Intelligent Query Routing

The MCP server now intelligently routes queries to the correct tables:

**Example:**
```
Query: "What is the immunization coverage in Indonesia?"
       ↓
Agent lists tables via MCP
       ↓
Finds: immunization_coverage_by_dimension_table_85
       ↓
Generates SQL for THAT specific table
       ↓
MCP executes on correct table only
```

---

## Testing Your Setup

### Test 1: MCP Connection
```bash
python "test scripts/test_mcp_implementation.py"
```

Should show:
```
✅ PASS - Connection Test
✅ PASS - List Tables
✅ PASS - Create Table
✅ PASS - Get Schema
✅ PASS - Execute Query
✅ PASS - Cleanup

Total: 6/6 tests passed (100.0%)
```

### Test 2: Document Processing

1. Place a PDF in `data/` folder
2. Run: `python agents/document_parse_agent.py`
3. Check `generated_tables/` for exported SQL
4. Verify tables in database:
   ```bash
   psql -U your_user -d multimodal_rag
   \dt
   SELECT * FROM table_chunks;
   ```

### Test 3: Query Execution

```bash
python agents/text_to_sql_agent.py
```

Watch for:
```
✅ MCP server connected
⚡ STEP 3: EXECUTING SQL QUERIES VIA MCP
✅ Success (via MCP): Retrieved 10 row(s)
```

---

## Common Issues & Solutions

### ❌ "MCP Server: Offline"

**Problem:** MCP server not running

**Solution:**
```bash
# Start the server in a separate terminal
python start_mcp_server.py
```

---

### ❌ "Failed to connect to MCP server"

**Problem:** Server crashed or database connection failed

**Solution:**
1. Check MCP server terminal for errors
2. Verify database is running:
   ```bash
   psql -h localhost -U your_user -d multimodal_rag
   ```
3. Check `.env` file has correct credentials
4. Restart MCP server

---

### ❌ "Timeout waiting for response"

**Problem:** Query taking too long

**Solution:**
1. Add LIMIT clause to your query
2. Increase timeout in code:
   ```python
   result = client.call_tool("execute_sql_query", args, timeout=60)
   ```
3. Check MCP server is responsive

---

### ⚠️ "Using direct database connection"

**Problem:** MCP unavailable, using fallback

**Solution:**
- This is OK! Application still works
- Start MCP server for full functionality
- Click "Reconnect MCP" in Streamlit sidebar

---

## Workflow Examples

### Example 1: Processing a New Document

```bash
# Terminal 1: Start MCP server
python start_mcp_server.py

# Terminal 2: Process document
python agents/document_parse_agent.py

# Check results
ls generated_tables/
cat generated_tables/tables_*.sql
```

### Example 2: Running the Chatbot

```bash
# Terminal 1: MCP server (keep running)
python start_mcp_server.py

# Terminal 2: Start Streamlit
streamlit run streamlit_app.py

# In browser:
# 1. Check MCP status (should be 🟢 Online)
# 2. Click "Initialize AI Agents"
# 3. Ask: "What is the pillar score for Indonesia?"
```

### Example 3: CLI Query

```bash
# Terminal 1: MCP server
python start_mcp_server.py

# Terminal 2: Run query
python "test scripts/run_chatbot.py"

# Enter query when prompted:
> What are the top 5 countries by pillar I score?
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│           Streamlit UI / CLI Interface               │
│         (Shows MCP Status: 🟢/🟡/🔴)                 │
└──────────────────────┬──────────────────────────────┘
                       │
           ┌───────────┴───────────┐
           │                       │
┌──────────▼──────────┐  ┌────────▼────────────┐
│ Document Parse Agent│  │ Text-to-SQL Agent   │
│ (Creates tables)    │  │ (Executes queries)  │
└──────────┬──────────┘  └────────┬────────────┘
           │                       │
           │    SQLMCPClient       │
           │    (stdio/JSON-RPC)   │
           └───────────┬───────────┘
                       │
           ┌───────────▼───────────┐
           │   MCP Server (stdio)  │
           │  - execute_create_table│
           │  - execute_sql_query  │
           │  - list_tables        │
           │  - get_table_schema   │
           └───────────┬───────────┘
                       │
           ┌───────────▼───────────┐
           │   PostgreSQL Database │
           └───────────────────────┘
```

---

## Pro Tips

### 💡 Tip 1: Check Server Logs

Always keep an eye on the MCP server terminal:
```
🔧 MCP Tool Called: execute_sql_query
📝 SQL Query received:
SELECT * FROM governance_pillars LIMIT 10;

✅ Query executed successfully! Retrieved 10 row(s)
```

### 💡 Tip 2: Monitor Generated Tables

Periodically check:
```bash
ls -lht generated_tables/ | head
```

Each SQL file shows exactly what tables were created.

### 💡 Tip 3: Use Context Managers

In your code:
```python
# ✅ Good (auto-cleanup)
with SQLMCPClient() as client:
    result = client.execute_query("SELECT ...")

# ❌ Less good (manual cleanup)
client = SQLMCPClient()
client.connect()
result = client.execute_query("SELECT ...")
client.disconnect()
```

### 💡 Tip 4: Fallback is OK

If MCP is offline, the system automatically falls back to direct database:
- ⚠️ You'll see warnings
- ✅ Functionality still works
- 🔄 Reconnect when convenient

---

## Next Steps

1. ✅ **Start MCP Server** → `python start_mcp_server.py`
2. ✅ **Test Connection** → `python "test scripts/test_mcp_implementation.py"`
3. ✅ **Run Application** → `streamlit run streamlit_app.py`
4. ✅ **Check Status** → Look for 🟢 in UI
5. ✅ **Process Documents** → Upload PDFs
6. ✅ **Ask Questions** → Use the chatbot!

---

## Getting Help

### Check Logs
```bash
# MCP server terminal - shows all SQL operations
# Streamlit terminal - shows agent activity
```

### Review Documentation
```bash
cat "Readme Files/MCP_IMPLEMENTATION_GUIDE.md"
```

### Run Tests
```bash
python "test scripts/test_mcp_implementation.py"
```

---

## Summary

Your MCP implementation is ready! 🎉

**Key Benefits:**
- ✅ Secure, centralized database access
- ✅ Real-time server monitoring
- ✅ Complete SQL export for transparency
- ✅ Intelligent table routing
- ✅ Production-ready architecture

**Remember:**
- Keep MCP server running in a separate terminal
- Check status indicator in UI
- Review generated_tables/ folder
- Use fallback if MCP unavailable

Happy coding! 🚀
