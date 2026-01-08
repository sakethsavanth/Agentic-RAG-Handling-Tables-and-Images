"""
Setup Script for MCP-Enhanced RAG System
Checks dependencies, environment variables, and provides setup guidance
"""
import subprocess
import sys
import os
from pathlib import Path

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")

def check_python_version():
    """Check if Python version is compatible"""
    print_header("Checking Python Version")
    
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 8:
        print("✅ Python version is compatible (>= 3.8)")
        return True
    else:
        print("❌ Python version must be >= 3.8")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    print_header("Checking Dependencies")
    
    required = [
        'streamlit', 'fastapi', 'uvicorn', 'cohere', 
        'boto3', 'psycopg2', 'langgraph', 'requests'
    ]
    
    missing = []
    
    for package in required:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - NOT INSTALLED")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️ Missing packages: {', '.join(missing)}")
        print("\nTo install all dependencies, run:")
        print("   pip install -r requirements.txt")
        return False
    else:
        print("\n✅ All required packages are installed!")
        return True

def check_env_file():
    """Check if .env file exists and has required variables"""
    print_header("Checking Environment Configuration")
    
    env_path = Path('.env')
    
    if not env_path.exists():
        print("❌ .env file not found!")
        print("\nCreate a .env file with the following variables:")
        print("""
# PostgreSQL Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database
DB_USER=your_user
DB_PASSWORD=your_password

# AWS Bedrock
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1

# Cohere API (Optional)
COHERE_API_KEY=your_cohere_api_key
        """)
        return False
    
    print("✅ .env file found")
    
    # Check for required variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
        'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
            print(f"⚠️ {var} - Not set")
        else:
            print(f"✅ {var}")
    
    # Check optional Cohere key
    if os.getenv('COHERE_API_KEY'):
        print("✅ COHERE_API_KEY (optional)")
    else:
        print("ℹ️ COHERE_API_KEY - Not set (optional, for Cohere reranking)")
        print("   Get free key at: https://dashboard.cohere.com/api-keys")
    
    if missing_vars:
        print(f"\n⚠️ Missing required variables: {', '.join(missing_vars)}")
        return False
    else:
        print("\n✅ All required environment variables are set!")
        return True

def check_database_connection():
    """Test database connection"""
    print_header("Checking Database Connection")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        import psycopg2
        
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT', 5432),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        
        conn.close()
        print("✅ Database connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        print("\nMake sure PostgreSQL is running and credentials are correct.")
        return False

def check_project_structure():
    """Check if required files exist"""
    print_header("Checking Project Structure")
    
    required_files = [
        'webhook_server.py',
        'streaming_api.py',
        'cohere_mcp.py',
        'streamlit_app.py',
        'launch_mcp_servers.py',
        'requirements.txt',
        'chatbot_orchestrator.py'
    ]
    
    required_folders = [
        'agents',
        'utils',
        'mcp_server',
        'data'
    ]
    
    all_ok = True
    
    for file in required_files:
        if Path(file).exists():
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - NOT FOUND")
            all_ok = False
    
    for folder in required_folders:
        if Path(folder).exists():
            print(f"✅ {folder}/")
        else:
            print(f"❌ {folder}/ - NOT FOUND")
            all_ok = False
    
    if all_ok:
        print("\n✅ All required files and folders are present!")
    else:
        print("\n⚠️ Some files or folders are missing!")
    
    return all_ok

def display_next_steps():
    """Display next steps to user"""
    print_header("Next Steps")
    
    print("""
🚀 Your MCP-Enhanced RAG system is ready to use!

To start the system:

1. Launch all MCP servers (Terminal 1):
   python launch_mcp_servers.py

2. Start Streamlit UI (Terminal 2):
   streamlit run streamlit_app.py

3. Open browser to: http://localhost:8501

For detailed instructions, see: MCP_QUICKSTART_GUIDE.md

Features available:
✅ Asynchronous document processing
✅ Real-time streaming queries
✅ Optional Cohere reranking
✅ Full API access

Have fun! 🎉
    """)

def main():
    """Main setup check"""
    print("\n" + "=" * 80)
    print("  MCP-ENHANCED RAG SYSTEM - SETUP CHECK")
    print("=" * 80)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Environment Configuration", check_env_file),
        ("Database Connection", check_database_connection),
        ("Project Structure", check_project_structure)
    ]
    
    results = {}
    
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n❌ Error during {name} check: {str(e)}")
            results[name] = False
    
    # Summary
    print_header("Setup Check Summary")
    
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")
    
    if all(results.values()):
        print("\n🎉 All checks passed! System is ready to use.")
        display_next_steps()
    else:
        print("\n⚠️ Some checks failed. Please fix the issues above before proceeding.")
        print("\nFor help, see: MCP_QUICKSTART_GUIDE.md")

if __name__ == "__main__":
    main()
