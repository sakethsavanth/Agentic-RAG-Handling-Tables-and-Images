"""
FastMCP Server for SQL Query Execution
This MCP server receives SQL queries and executes them in PostgreSQL
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to import utils
sys.path.append(str(Path(__file__).parent.parent))

from fastmcp import FastMCP
from utils.db_utils import DatabaseManager
from dotenv import load_dotenv

# Load environment variables from the project root
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

# Initialize FastMCP server
mcp = FastMCP("SQL Executor MCP")

# Global database manager
db_manager = None


def initialize_db():
    """Initialize database connection"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
        success = db_manager.connect()
        if success:
            db_manager.create_tables()
            return True
        else:
            print(f"❌ MCP failed to connect to database")
            print(f"   Host: {db_manager.conn_params['host']}")
            print(f"   Port: {db_manager.conn_params['port']}")
            print(f"   Database: {db_manager.conn_params['database']}")
            return False
    return True  # Already initialized


def _execute_create_table_impl(sql_query: str) -> dict:
    """
    Execute a CREATE TABLE SQL statement in PostgreSQL
    
    Args:
        sql_query: The SQL CREATE TABLE statement to execute
        
    Returns:
        Dictionary with success status and message
    """
    print(f"\n🔧 MCP Tool Called: execute_create_table")
    print(f"📝 SQL Query received:\n{sql_query}\n")
    
    # Initialize DB if not already done
    if not initialize_db():
        return {
            "success": False,
            "message": "Failed to connect to database"
        }
    
    # Execute the SQL query
    success, message = db_manager.execute_sql(sql_query)
    
    if success:
        print(f"✅ SQL executed successfully!")
        return {
            "success": True,
            "message": f"Table created successfully: {message}"
        }
    else:
        print(f"❌ SQL execution failed: {message}")
        return {
            "success": False,
            "message": f"Failed to execute SQL: {message}"
        }


# Register the tool with MCP
@mcp.tool()
def execute_create_table(sql_query: str) -> dict:
    """
    Execute a CREATE TABLE SQL statement in PostgreSQL
    
    Args:
        sql_query: The SQL CREATE TABLE statement to execute
        
    Returns:
        Dictionary with success status and message
    """
    return _execute_create_table_impl(sql_query)


def _execute_insert_data_impl(sql_query: str) -> dict:
    """
    Execute INSERT SQL statements in PostgreSQL
    
    Args:
        sql_query: The SQL INSERT statement(s) to execute
        
    Returns:
        Dictionary with success status and message
    """
    print(f"\n🔧 MCP Tool Called: execute_insert_data")
    print(f"📝 SQL Query received:\n{sql_query}\n")
    
    # Initialize DB if not already done
    if not initialize_db():
        return {
            "success": False,
            "message": "Failed to connect to database"
        }
    
    # Execute the SQL query
    success, message = db_manager.execute_sql(sql_query)
    
    if success:
        print(f"✅ Data inserted successfully!")
        return {
            "success": True,
            "message": f"Data inserted successfully: {message}"
        }
    else:
        print(f"❌ Insert failed: {message}")
        return {
            "success": False,
            "message": f"Failed to insert data: {message}"
        }


# Register the tool with MCP
@mcp.tool()
def execute_insert_data(sql_query: str) -> dict:
    """
    Execute INSERT SQL statements in PostgreSQL
    
    Args:
        sql_query: The SQL INSERT statement(s) to execute
        
    Returns:
        Dictionary with success status and message
    """
    return _execute_insert_data_impl(sql_query)


def _execute_sql_query_impl(sql_query: str) -> dict:
    """
    Execute any SQL query in PostgreSQL
    
    Args:
        sql_query: The SQL query to execute
        
    Returns:
        Dictionary with success status and message
    """
    print(f"\n🔧 MCP Tool Called: execute_sql_query")
    print(f"📝 SQL Query received:\n{sql_query}\n")
    
    # Initialize DB if not already done
    if not initialize_db():
        return {
            "success": False,
            "message": "Failed to connect to database"
        }
    
    # Execute the SQL query
    success, message = db_manager.execute_sql(sql_query)
    
    if success:
        print(f"✅ SQL executed successfully!")
        return {
            "success": True,
            "message": f"Query executed successfully: {message}"
        }
    else:
        print(f"❌ SQL execution failed: {message}")
        return {
            "success": False,
            "message": f"Failed to execute SQL: {message}"
        }


# Register the tool with MCP
@mcp.tool()
def execute_sql_query(sql_query: str) -> dict:
    """
    Execute any SQL query in PostgreSQL
    
    Args:
        sql_query: The SQL query to execute
        
    Returns:
        Dictionary with success status and message
    """
    return _execute_sql_query_impl(sql_query)


# Client class for calling MCP from agents
class MCPSQLExecutor:
    """Client for calling the MCP SQL execution tools"""
    
    def __init__(self):
        """Initialize the MCP client"""
        # Initialize database connection
        initialize_db()
    
    def create_table(self, sql_query: str) -> dict:
        """
        Create a table using the SQL query
        
        Args:
            sql_query: CREATE TABLE SQL statement
            
        Returns:
            Dict with success status
        """
        # Call the implementation function directly (not the decorated one)
        try:
            result = _execute_create_table_impl(sql_query)
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"Error executing SQL: {str(e)}"
            }
    
    def insert_data(self, sql_query: str) -> dict:
        """
        Insert data using SQL INSERT statements
        
        Args:
            sql_query: INSERT SQL statement(s)
            
        Returns:
            Dict with success status
        """
        try:
            result = _execute_insert_data_impl(sql_query)
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"Error inserting data: {str(e)}"
            }
    
    def execute_query(self, sql_query: str) -> dict:
        """
        Execute any SQL query
        
        Args:
            sql_query: SQL query to execute
            
        Returns:
            Dict with success status
        """
        try:
            result = _execute_sql_query_impl(sql_query)
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"Error executing query: {str(e)}"
            }


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting FastMCP SQL Executor Server")
    print("=" * 60)
    
    # Initialize database on server start
    initialize_db()
    
    # Run the MCP server
    mcp.run()
