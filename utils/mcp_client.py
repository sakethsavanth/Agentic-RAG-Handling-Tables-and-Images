"""
MCP Client for SQL Executor
Proper stdio-based client for communicating with the MCP SQL server
"""
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import threading
import queue
import time


class MCPClient:
    """Client for communicating with MCP server via stdio"""
    
    def __init__(self, server_script: str = None):
        """
        Initialize MCP client
        
        Args:
            server_script: Path to the MCP server script (default: mcp_server/sql_executor_mcp.py)
        """
        if server_script is None:
            server_script = str(Path(__file__).parent.parent / "mcp_server" / "sql_executor_mcp.py")
        
        self.server_script = server_script
        self.process = None
        self.stdout_queue = queue.Queue()
        self.stderr_queue = queue.Queue()
        self.request_id = 0
        self.is_connected = False
        self._lock = threading.Lock()
    
    def connect(self) -> bool:
        """
        Start the MCP server process
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            print(f"🔌 Connecting to MCP server: {self.server_script}")
            
            # Start the MCP server as a subprocess
            self.process = subprocess.Popen(
                [sys.executable, self.server_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Start threads to read stdout and stderr
            stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
            stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
            
            stdout_thread.start()
            stderr_thread.start()
            
            # Wait a bit for server to initialize
            time.sleep(2)
            
            # Check if process is still running
            if self.process.poll() is None:
                self.is_connected = True
                print("✅ MCP server connected successfully")
                return True
            else:
                print("❌ MCP server process terminated")
                return False
                
        except Exception as e:
            print(f"❌ Failed to connect to MCP server: {str(e)}")
            return False
    
    def disconnect(self):
        """Close the connection to MCP server"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                print("✅ MCP server disconnected")
            except:
                self.process.kill()
            finally:
                self.is_connected = False
                self.process = None
    
    def _read_stdout(self):
        """Read stdout from server process"""
        try:
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    self.stdout_queue.put(line.strip())
        except:
            pass
    
    def _read_stderr(self):
        """Read stderr from server process"""
        try:
            for line in iter(self.process.stderr.readline, ''):
                if line:
                    self.stderr_queue.put(line.strip())
        except:
            pass
    
    def _get_next_id(self) -> int:
        """Get next request ID"""
        with self._lock:
            self.request_id += 1
            return self.request_id
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """
        Call a tool on the MCP server
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            timeout: Timeout in seconds
            
        Returns:
            Tool response or error
        """
        if not self.is_connected or not self.process:
            return {
                "success": False,
                "error": "Not connected to MCP server"
            }
        
        try:
            # Create MCP request
            request_id = self._get_next_id()
            request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            # Send request
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str)
            self.process.stdin.flush()
            
            # Wait for response
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    # Check stdout queue for response
                    line = self.stdout_queue.get(timeout=0.1)
                    
                    # Try to parse as JSON
                    try:
                        response = json.loads(line)
                        
                        # Check if this is our response
                        if response.get("id") == request_id:
                            if "result" in response:
                                return response["result"]
                            elif "error" in response:
                                return {
                                    "success": False,
                                    "error": response["error"].get("message", "Unknown error")
                                }
                    except json.JSONDecodeError:
                        # Not JSON, might be server log output
                        continue
                        
                except queue.Empty:
                    continue
            
            return {
                "success": False,
                "error": f"Timeout waiting for response (>{timeout}s)"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error calling tool: {str(e)}"
            }
    
    def list_tools(self, timeout: int = 10) -> List[Dict[str, Any]]:
        """
        List available tools from the MCP server
        
        Returns:
            List of available tools
        """
        if not self.is_connected or not self.process:
            return []
        
        try:
            request_id = self._get_next_id()
            request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/list",
                "params": {}
            }
            
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str)
            self.process.stdin.flush()
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    line = self.stdout_queue.get(timeout=0.1)
                    response = json.loads(line)
                    
                    if response.get("id") == request_id:
                        if "result" in response:
                            return response["result"].get("tools", [])
                        
                except (queue.Empty, json.JSONDecodeError):
                    continue
            
            return []
            
        except Exception as e:
            print(f"Error listing tools: {str(e)}")
            return []
    
    def is_alive(self) -> bool:
        """Check if MCP server is still running"""
        return self.is_connected and self.process and self.process.poll() is None
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


class SQLMCPClient:
    """High-level client for SQL operations via MCP"""
    
    def __init__(self):
        """Initialize SQL MCP client"""
        self.client = MCPClient()
        self._connected = False
    
    def connect(self) -> bool:
        """Connect to MCP server"""
        result = self.client.connect()
        self._connected = result
        return result
    
    def disconnect(self):
        """Disconnect from MCP server"""
        self.client.disconnect()
        self._connected = False
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self._connected and self.client.is_alive()
    
    def create_table(self, sql_query: str) -> Dict[str, Any]:
        """
        Create a table using SQL CREATE TABLE statement
        
        Args:
            sql_query: CREATE TABLE SQL statement
            
        Returns:
            Result dictionary with success status
        """
        return self.client.call_tool("execute_create_table", {"sql_query": sql_query})
    
    def execute_query(self, sql_query: str) -> Dict[str, Any]:
        """
        Execute a SQL SELECT query
        
        Args:
            sql_query: SELECT SQL query
            
        Returns:
            Result dictionary with rows and metadata
        """
        return self.client.call_tool("execute_sql_query", {"sql_query": sql_query})
    
    def list_tables(self) -> Dict[str, Any]:
        """
        List all tables in the database
        
        Returns:
            Dictionary with table list
        """
        return self.client.call_tool("list_tables", {})
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Get schema for a specific table
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with schema information
        """
        return self.client.call_tool("get_table_schema", {"table_name": table_name})
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Backward compatibility class (wraps the new client)
class MCPSQLExecutor(SQLMCPClient):
    """
    Backward compatible wrapper for MCPSQLExecutor
    Maintains the same interface but uses proper MCP protocol
    """
    
    def __init__(self):
        """Initialize MCP SQL Executor"""
        super().__init__()
        # Auto-connect on initialization for backward compatibility
        self.connect()
