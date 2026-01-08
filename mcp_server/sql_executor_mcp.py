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
    Execute a SQL SELECT query in PostgreSQL and return results
    
    Args:
        sql_query: The SQL SELECT query to execute
        
    Returns:
        Dictionary with success status, rows, and metadata
    """
    print(f"\n🔧 MCP Tool Called: execute_sql_query")
    print(f"📝 SQL Query received:\n{sql_query}\n")
    
    # Initialize DB if not already done
    if not initialize_db():
        return {
            "success": False,
            "message": "Failed to connect to database",
            "rows": [],
            "row_count": 0
        }
    
    try:
        # Execute the SELECT query
        db_manager.cursor.execute(sql_query)
        
        # Fetch all results
        rows = db_manager.cursor.fetchall()
        
        # Convert to list of dicts
        if rows:
            result_data = [dict(row) for row in rows]
            print(f"✅ Query executed successfully! Retrieved {len(result_data)} row(s)")
            return {
                "success": True,
                "message": f"Query executed successfully",
                "rows": result_data,
                "row_count": len(result_data),
                "columns": list(result_data[0].keys()) if result_data else []
            }
        else:
            print(f"✅ Query executed successfully! No rows returned")
            return {
                "success": True,
                "message": "Query executed successfully",
                "rows": [],
                "row_count": 0,
                "columns": []
            }
            
    except Exception as e:
        print(f"❌ SQL execution failed: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to execute SQL: {str(e)}",
            "rows": [],
            "row_count": 0,
            "error": str(e)
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


def _list_tables_impl() -> dict:
    """
    List all tables in the database
    
    Returns:
        Dictionary with list of tables
    """
    print(f"\n🔧 MCP Tool Called: list_tables")
    
    # Initialize DB if not already done
    if not initialize_db():
        return {
            "success": False,
            "message": "Failed to connect to database",
            "tables": []
        }
    
    try:
        # Query to get all table names from table_chunks
        db_manager.cursor.execute("""
            SELECT DISTINCT table_name, metadata
            FROM table_chunks
            ORDER BY table_name;
        """)
        
        rows = db_manager.cursor.fetchall()
        
        tables = []
        for row in rows:
            tables.append({
                "table_name": row['table_name'],
                "description": row['metadata'].get('description', 'No description') if row['metadata'] else 'No description'
            })
        
        print(f"✅ Found {len(tables)} table(s)")
        return {
            "success": True,
            "message": f"Found {len(tables)} table(s)",
            "tables": tables,
            "count": len(tables)
        }
        
    except Exception as e:
        print(f"❌ Failed to list tables: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to list tables: {str(e)}",
            "tables": [],
            "error": str(e)
        }


@mcp.tool()
def list_tables() -> dict:
    """
    List all tables in the database
    
    Returns:
        Dictionary with list of tables
    """
    return _list_tables_impl()


def _get_table_schema_impl(table_name: str) -> dict:
    """
    Get schema information for a specific table
    
    Args:
        table_name: Name of the table
        
    Returns:
        Dictionary with schema information
    """
    print(f"\n🔧 MCP Tool Called: get_table_schema")
    print(f"📝 Table name: {table_name}\n")
    
    # Initialize DB if not already done
    if not initialize_db():
        return {
            "success": False,
            "message": "Failed to connect to database",
            "schema": None
        }
    
    try:
        # Get the CREATE TABLE statement from table_chunks
        db_manager.cursor.execute("""
            SELECT sql_query, metadata
            FROM table_chunks
            WHERE table_name = %s
            LIMIT 1;
        """, (table_name,))
        
        row = db_manager.cursor.fetchone()
        
        if row:
            # Also get actual column info from PostgreSQL information_schema
            db_manager.cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))
            
            columns = db_manager.cursor.fetchall()
            column_info = [dict(col) for col in columns] if columns else []
            
            print(f"✅ Schema retrieved for table: {table_name}")
            return {
                "success": True,
                "message": f"Schema retrieved for {table_name}",
                "table_name": table_name,
                "sql_query": row['sql_query'],
                "columns": column_info,
                "metadata": row['metadata']
            }
        else:
            print(f"❌ Table not found: {table_name}")
            return {
                "success": False,
                "message": f"Table not found: {table_name}",
                "schema": None
            }
            
    except Exception as e:
        print(f"❌ Failed to get schema: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to get schema: {str(e)}",
            "schema": None,
            "error": str(e)
        }


@mcp.tool()
def get_table_schema(table_name: str) -> dict:
    """
    Get schema information for a specific table
    
    Args:
        table_name: Name of the table
        
    Returns:
        Dictionary with schema information
    """
    return _get_table_schema_impl(table_name)


# Client class for calling MCP from agents
class MCPSQLExecutor:
    """Client for calling the MCP SQL execution tools"""
    
    def __init__(self):
        """Initialize the MCP client"""
        # Initialize database connection for backward compatibility
        # New code should use utils.mcp_client.SQLMCPClient instead
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
            Dict with success status and results
        """
        try:
            result = _execute_sql_query_impl(sql_query)
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"Error executing query: {str(e)}",
                "rows": [],
                "row_count": 0
            }
    
    def list_tables(self) -> dict:
        """
        List all tables in the database
        
        Returns:
            Dict with table list
        """
        try:
            result = _list_tables_impl()
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"Error listing tables: {str(e)}",
                "tables": []
            }
    
    def get_table_schema(self, table_name: str) -> dict:
        """
        Get schema for a specific table
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dict with schema information
        """
        try:
            result = _get_table_schema_impl(table_name)
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"Error getting schema: {str(e)}",
                "schema": None
            }



if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting FastMCP SQL Executor Server")
    print("=" * 60)
    
    # Initialize database on server start
    initialize_db()
    
    # Run the MCP server
    mcp.run()
