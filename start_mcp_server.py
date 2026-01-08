"""
MCP Server Launcher
Starts the FastMCP SQL Executor Server with proper configuration
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Set environment variable to indicate server mode
os.environ['MCP_SERVER_MODE'] = '1'

print("="*80)
print("🚀 Starting FastMCP SQL Executor Server")
print("="*80)
print(f"\n📁 Project Root: {project_root}")
print(f"🔧 Server Script: {project_root / 'mcp_server' / 'sql_executor_mcp.py'}")
print(f"\n💡 The server will communicate via stdio (JSON-RPC)")
print(f"🔌 Agents will connect automatically when they start")
print(f"\n⚠️  Keep this terminal window open while using the application")
print(f"⏹️  Press Ctrl+C to stop the server\n")
print("="*80 + "\n")

# Import and run the MCP server
from mcp_server.sql_executor_mcp import mcp, initialize_db

# Initialize database
if initialize_db():
    print("✅ Database initialized successfully\n")
else:
    print("⚠️  Warning: Database initialization had issues\n")

print("🎧 Server is now listening for connections...\n")
print("="*80 + "\n")

# Run the FastMCP server
try:
    mcp.run()
except KeyboardInterrupt:
    print("\n\n" + "="*80)
    print("⏹️  MCP Server stopped by user")
    print("="*80 + "\n")
except Exception as e:
    print(f"\n\n❌ Server error: {str(e)}\n")
    sys.exit(1)
