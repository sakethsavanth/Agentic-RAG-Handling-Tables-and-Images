"""
Test Script for MCP Implementation
Tests the proper stdio-based MCP client and server
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.mcp_client import SQLMCPClient


def test_mcp_connection():
    """Test 1: MCP Server Connection"""
    print("\n" + "="*80)
    print("TEST 1: MCP Server Connection")
    print("="*80 + "\n")
    
    client = SQLMCPClient()
    
    if client.connect():
        print("✅ MCP server connected successfully!")
        
        # Check if alive
        if client.is_connected():
            print("✅ MCP server is alive and responding")
        
        client.disconnect()
        print("✅ MCP server disconnected successfully")
        return True
    else:
        print("❌ Failed to connect to MCP server")
        return False


def test_list_tables():
    """Test 2: List Tables via MCP"""
    print("\n" + "="*80)
    print("TEST 2: List Tables via MCP")
    print("="*80 + "\n")
    
    with SQLMCPClient() as client:
        result = client.list_tables()
        
        if result.get('success'):
            tables = result.get('tables', [])
            print(f"✅ Found {len(tables)} table(s):\n")
            
            for i, table in enumerate(tables, 1):
                print(f"   {i}. {table['table_name']}")
                print(f"      Description: {table.get('description', 'No description')}\n")
            
            return len(tables) > 0
        else:
            print(f"❌ Failed to list tables: {result.get('message')}")
            return False


def test_create_table():
    """Test 3: Create Table via MCP"""
    print("\n" + "="*80)
    print("TEST 3: Create Table via MCP")
    print("="*80 + "\n")
    
    with SQLMCPClient() as client:
        # Create a test table
        sql = """
        CREATE TABLE IF NOT EXISTS mcp_test_table (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            value INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        INSERT INTO mcp_test_table (name, value) VALUES 
            ('Test 1', 100),
            ('Test 2', 200),
            ('Test 3', 300);
        """
        
        print("Creating test table...")
        result = client.create_table(sql)
        
        if result.get('success'):
            print("✅ Table created successfully!")
            print(f"   Message: {result.get('message')}")
            return True
        else:
            print(f"❌ Failed to create table: {result.get('message')}")
            return False


def test_get_schema():
    """Test 4: Get Table Schema via MCP"""
    print("\n" + "="*80)
    print("TEST 4: Get Table Schema via MCP")
    print("="*80 + "\n")
    
    with SQLMCPClient() as client:
        result = client.get_table_schema("mcp_test_table")
        
        if result.get('success'):
            print("✅ Schema retrieved successfully!\n")
            print(f"   Table: {result.get('table_name')}")
            
            columns = result.get('columns', [])
            if columns:
                print(f"\n   Columns ({len(columns)}):")
                for col in columns:
                    nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                    print(f"      - {col['column_name']}: {col['data_type']} {nullable}")
            
            return True
        else:
            print(f"❌ Failed to get schema: {result.get('message')}")
            return False


def test_execute_query():
    """Test 5: Execute Query via MCP"""
    print("\n" + "="*80)
    print("TEST 5: Execute SELECT Query via MCP")
    print("="*80 + "\n")
    
    with SQLMCPClient() as client:
        result = client.execute_query("""
            SELECT id, name, value 
            FROM mcp_test_table 
            ORDER BY value DESC
            LIMIT 5;
        """)
        
        if result.get('success'):
            rows = result.get('rows', [])
            print(f"✅ Query executed successfully!")
            print(f"   Retrieved {result.get('row_count')} row(s)\n")
            
            if rows:
                print("   Results:")
                for row in rows:
                    print(f"      - ID: {row.get('id')}, Name: {row.get('name')}, Value: {row.get('value')}")
            
            return True
        else:
            print(f"❌ Query failed: {result.get('message')}")
            return False


def test_cleanup():
    """Test 6: Cleanup Test Table"""
    print("\n" + "="*80)
    print("TEST 6: Cleanup Test Table")
    print("="*80 + "\n")
    
    with SQLMCPClient() as client:
        result = client.execute_query("DROP TABLE IF EXISTS mcp_test_table;")
        
        if result.get('success'):
            print("✅ Test table cleaned up successfully!")
            return True
        else:
            print(f"⚠️ Cleanup warning: {result.get('message')}")
            return True  # Not critical


def main():
    """Run all MCP tests"""
    print("\n" + "="*80)
    print("🧪 MCP IMPLEMENTATION TEST SUITE")
    print("="*80)
    print("\nTesting stdio-based MCP client-server communication...")
    
    tests = [
        ("Connection Test", test_mcp_connection),
        ("List Tables", test_list_tables),
        ("Create Table", test_create_table),
        ("Get Schema", test_get_schema),
        ("Execute Query", test_execute_query),
        ("Cleanup", test_cleanup)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80 + "\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")
    
    print(f"\n{'='*80}")
    print(f"   Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"{'='*80}\n")
    
    if passed == total:
        print("🎉 All tests passed! MCP implementation is working correctly.")
    else:
        print("⚠️ Some tests failed. Please review the output above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
