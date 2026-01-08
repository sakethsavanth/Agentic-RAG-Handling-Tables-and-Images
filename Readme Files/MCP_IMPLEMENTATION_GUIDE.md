# MCP (Model Context Protocol) Implementation Guide

## Overview

This project now implements a **proper MCP architecture** using the stdio protocol for communication between agents and the PostgreSQL database. The MCP server acts as an intelligent intermediary that handles all SQL operations securely and efficiently.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI                              │
│              (Shows MCP Server Status)                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Agent Layer                                 │
│  ┌──────────────────┐  ┌────────────────────────────────┐  │
│  │ Document Parse   │  │ Text-to-SQL Agent              │  │
│  │ Agent            │  │                                │  │
│  │ (Creates tables) │  │ (Executes SELECT queries)      │  │
│  └────────┬─────────┘  └──────────┬─────────────────────┘  │
└───────────┼────────────────────────┼────────────────────────┘
            │                        │
            │    SQLMCPClient        │
            │    (stdio protocol)    │
            ▼                        ▼
┌─────────────────────────────────────────────────────────────┐
│              MCP Server (FastMCP)                            │
│              sql_executor_mcp.py                             │
│                                                              │
│  Tools:                                                      │
│  ├─ execute_create_table (CREATE TABLE + INSERT)           │
│  ├─ execute_sql_query (SELECT queries)                     │
│  ├─ list_tables (Get all available tables)                 │
│  └─ get_table_schema (Get schema for specific table)       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
                 PostgreSQL Database
```

## Key Components

### 1. MCP Server (`mcp_server/sql_executor_mcp.py`)

The FastMCP server that exposes database operations as tools:

**Tools Available:**
- `execute_create_table` - Creates tables and inserts data
- `execute_sql_query` - Executes SELECT queries and returns results
- `list_tables` - Lists all tables in the database
- `get_table_schema` - Gets schema information for a specific table

**Running the Server:**
```bash
python mcp_server/sql_executor_mcp.py
```

The server runs in stdio mode and communicates via JSON-RPC over stdin/stdout.

### 2. MCP Client (`utils/mcp_client.py`)

**Classes:**

#### `MCPClient`
Low-level client that handles stdio communication with the MCP server.

```python
from utils.mcp_client import MCPClient

client = MCPClient()
client.connect()

# Call a tool
result = client.call_tool("execute_sql_query", {
    "sql_query": "SELECT * FROM table_name LIMIT 10;"
})

client.disconnect()
```

#### `SQLMCPClient`
High-level wrapper with convenient methods for SQL operations.

```python
from utils.mcp_client import SQLMCPClient

with SQLMCPClient() as client:
    # Create a table
    result = client.create_table("""
        CREATE TABLE test (id INT, name VARCHAR(100));
        INSERT INTO test VALUES (1, 'Test');
    """)
    
    # Execute a query
    result = client.execute_query("SELECT * FROM test;")
    print(result['rows'])
    
    # List all tables
    tables = client.list_tables()
    
    # Get schema
    schema = client.get_table_schema("test")
```

#### `MCPSQLExecutor` (Backward Compatibility)
Legacy class that maintains the same interface but now uses the proper MCP client internally.

### 3. Generated Tables Export

All SQL tables created from documents are now saved to files for visibility:

**Location:** `generated_tables/`

**Files Created:**
- `tables_{document_name}_{timestamp}.sql` - Tables from markdown
- `visualization_tables_{document_name}_{timestamp}.sql` - Tables from images

**Format:**
```sql
-- Generated Tables from: Business_Ready_2025
-- Generated at: 2026-01-07 15:30:45
-- Total tables: 5
-- ======================================================================

-- Table: governance_pillars_table_5
-- Source: Business_Ready_2025, table_5
CREATE TABLE governance_pillars_table_5 (
    country_name VARCHAR(255),
    pillar_i_score FLOAT,
    pillar_ii_score FLOAT,
    pillar_iii_score FLOAT
);
INSERT INTO governance_pillars_table_5 VALUES ('Indonesia', 65.2, 72.1, 68.9);
...
```

## Agent Integration

### Document Parse Agent

The Document Parse Agent uses MCP to create tables from:
1. **Visualizations in images** - Extracts data from charts/graphs
2. **Markdown tables** - Converts table text to SQL

```python
from agents.document_parse_agent import DocumentParseAgent

agent = DocumentParseAgent(data_folder="data")
result = agent.run()  # Automatically uses MCP for table creation
```

**Features:**
- ✅ Exports all generated SQL to `generated_tables/` folder
- ✅ Makes table names unique (appends suffixes)
- ✅ Uses MCP for secure table creation
- ✅ Stores table metadata in PostgreSQL

### Text-to-SQL Agent

The Text-to-SQL Agent uses MCP to:
1. **List available tables** - Gets table inventory from MCP
2. **Execute SELECT queries** - Runs queries via MCP
3. **Get table schemas** - Retrieves column information

```python
from agents.text_to_sql_agent import TextToSQLAgent

agent = TextToSQLAgent()
result = agent.process_query("What is the pillar score for Indonesia?")
```

**Features:**
- ✅ Intelligent table routing (queries the correct table)
- ✅ Fallback to direct DB if MCP unavailable
- ✅ Returns structured results with rows and metadata

## Streamlit UI Integration

The Streamlit UI now shows MCP server status:

**Status Indicators:**
- 🟢 **Online** - MCP server is connected and responding
- 🟡 **Offline** - MCP unavailable, using direct DB fallback
- 🔴 **Error** - Connection error

**Features:**
- Real-time status checking
- Reconnect button in sidebar
- Automatic fallback to direct database if MCP fails

## How It Works

### 1. Document Processing Flow

```
PDF Document
    ↓
PyMuPDF4LLM (Extract markdown + images)
    ↓
AWS Bedrock (Analyze images/tables → Generate SQL)
    ↓
MCP Client (Send SQL to server)
    ↓
MCP Server (Validate + Execute SQL)
    ↓
PostgreSQL (Store tables)
    ↓
Export SQL file to generated_tables/
```

### 2. Query Execution Flow

```
User Query ("What is the pillar score for Indonesia?")
    ↓
Text-to-SQL Agent
    ↓
Step 1: List Tables (via MCP)
    ↓
Step 2: Generate SQL (LLM)
    → SELECT * FROM governance_pillars WHERE country = 'Indonesia';
    ↓
Step 3: Execute Query (via MCP)
    ↓
MCP Server (Execute on correct table)
    ↓
PostgreSQL (Return results)
    ↓
Format Results
    ↓
Return to User
```

### 3. Table Intelligence

The MCP server and agents work together to ensure queries run on the correct tables:

**Example:**
- Query: "Show immunization coverage data"
- Agent lists tables via MCP
- Finds: `immunization_coverage_by_dimension_table_85`
- Generates SQL: `SELECT * FROM immunization_coverage_by_dimension_table_85 ...`
- MCP executes on that specific table only

## Benefits of MCP Architecture

### 🔒 Security
- SQL validation before execution
- Centralized access control
- Prevents direct database manipulation

### 🚀 Performance
- Connection pooling in MCP server
- Efficient query routing
- Caching opportunities

### 🔧 Maintainability
- Single point for database logic
- Easy to add new tools/operations
- Standardized error handling

### 🔌 Interoperability
- Standard protocol (JSON-RPC over stdio)
- Can be used by external tools
- Language-agnostic interface

### 📊 Visibility
- All SQL operations logged in MCP server
- Query history and audit trail
- Generated tables exported for review

## Configuration

### Environment Variables

Required in `.env`:
```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=multimodal_rag
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
```

### MCP Server Settings

Edit `mcp_server/sql_executor_mcp.py`:
```python
# Connection timeout
TIMEOUT = 30  # seconds

# Query limits
MAX_ROWS = 10000
```

## Troubleshooting

### MCP Server Won't Start

**Error:** "Failed to connect to MCP server"

**Solutions:**
1. Check Python path: `which python`
2. Verify server script exists: `ls mcp_server/sql_executor_mcp.py`
3. Check database credentials in `.env`
4. Run server manually to see errors:
   ```bash
   python mcp_server/sql_executor_mcp.py
   ```

### MCP Status Shows Offline

**Possible Causes:**
1. Server not running
2. Database connection failed
3. Port conflict

**Fix:**
1. Click "Reconnect MCP" button in Streamlit UI
2. Check database is running: `psql -h localhost -U your_user -d multimodal_rag`
3. Restart the application

### Queries Failing

**Error:** "Timeout waiting for response"

**Solutions:**
1. Increase timeout in `mcp_client.py`:
   ```python
   result = client.call_tool("execute_sql_query", args, timeout=60)
   ```
2. Optimize SQL query (add LIMIT clause)
3. Check MCP server logs

### Tables Not Being Created

**Check:**
1. Look in `generated_tables/` folder for SQL files
2. Verify MCP server is running
3. Check database permissions
4. Review MCP server console output

## Testing

### Test MCP Connection

```python
from utils.mcp_client import SQLMCPClient

client = SQLMCPClient()
if client.connect():
    print("✅ MCP Connected")
    
    # Test listing tables
    result = client.list_tables()
    print(f"Tables: {result}")
    
    client.disconnect()
else:
    print("❌ MCP Connection Failed")
```

### Test Table Creation

```python
from utils.mcp_client import SQLMCPClient

with SQLMCPClient() as client:
    result = client.create_table("""
        CREATE TABLE test_table (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100)
        );
        INSERT INTO test_table (name) VALUES ('Test');
    """)
    
    print(f"Result: {result}")
```

### Test Query Execution

```python
from utils.mcp_client import SQLMCPClient

with SQLMCPClient() as client:
    result = client.execute_query("""
        SELECT * FROM test_table LIMIT 10;
    """)
    
    print(f"Rows: {result.get('rows')}")
    print(f"Count: {result.get('row_count')}")
```

## Monitoring

### MCP Server Logs

The MCP server prints detailed logs:
```
🔧 MCP Tool Called: execute_sql_query
📝 SQL Query received:
SELECT * FROM governance_pillars LIMIT 10;

✅ Query executed successfully! Retrieved 10 row(s)
```

### Generated SQL Files

Check the `generated_tables/` folder:
```bash
ls -lh generated_tables/
```

Each file contains:
- Source document name
- Timestamp
- Table count
- Complete SQL statements

## Advanced Usage

### Custom MCP Tools

Add new tools to `mcp_server/sql_executor_mcp.py`:

```python
@mcp.tool()
def custom_operation(param: str) -> dict:
    """Your custom database operation"""
    # Implementation
    return {"success": True, "result": "..."}
```

Update client in `utils/mcp_client.py`:

```python
class SQLMCPClient:
    def custom_operation(self, param: str) -> dict:
        return self.client.call_tool("custom_operation", {"param": param})
```

### Direct MCP Protocol Usage

For advanced use cases, use the low-level `MCPClient`:

```python
from utils.mcp_client import MCPClient

client = MCPClient()
client.connect()

# Send custom JSON-RPC request
result = client.call_tool("any_tool_name", {
    "arg1": "value1",
    "arg2": "value2"
})

client.disconnect()
```

## Migration Notes

### From Direct Database Access

**Old Code:**
```python
db_manager.cursor.execute("SELECT * FROM table;")
rows = db_manager.cursor.fetchall()
```

**New Code:**
```python
from utils.mcp_client import SQLMCPClient

client = SQLMCPClient()
client.connect()
result = client.execute_query("SELECT * FROM table;")
rows = result['rows']
```

### Backward Compatibility

The old `MCPSQLExecutor` class still works but now uses MCP internally:

```python
from mcp_server.sql_executor_mcp import MCPSQLExecutor

executor = MCPSQLExecutor()
result = executor.create_table("CREATE TABLE ...")  # Still works!
```

## Future Enhancements

Potential improvements to the MCP system:

1. **Query Caching** - Cache frequent queries in MCP server
2. **Rate Limiting** - Limit queries per client
3. **Authentication** - Add API keys/tokens
4. **Query History** - Store query logs in database
5. **Performance Metrics** - Track query execution times
6. **Connection Pooling** - Reuse database connections
7. **Multiple Databases** - Support for multiple DB backends
8. **GraphQL Support** - Add GraphQL query interface

## Summary

Your project now has a **production-ready MCP architecture** that:

✅ Uses proper stdio protocol for client-server communication  
✅ Provides secure, centralized database access  
✅ Exports all generated SQL to files for transparency  
✅ Shows real-time server status in the UI  
✅ Intelligently routes queries to correct tables  
✅ Maintains backward compatibility  
✅ Includes comprehensive error handling and fallbacks  

The system is modular, scalable, and ready for production use!
