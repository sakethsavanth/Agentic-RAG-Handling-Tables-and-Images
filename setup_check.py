"""
Setup script to verify environment and dependencies
"""
import os
import sys
from pathlib import Path


def check_environment():
    """Check if environment is properly configured"""
    print("\n" + "=" * 80)
    print("🔍 ENVIRONMENT SETUP CHECK")
    print("=" * 80 + "\n")
    
    issues = []
    
    # Check .env file
    print("1. Checking .env file...")
    env_file = Path(".env")
    if not env_file.exists():
        print("   ❌ .env file not found!")
        print("   📝 Create .env file based on .env.example")
        issues.append(".env file missing")
    else:
        print("   ✅ .env file found")
        
        # Check required variables
        from dotenv import load_dotenv
        load_dotenv()
        
        required_vars = [
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'AWS_REGION',
            'POSTGRES_HOST',
            'POSTGRES_PORT',
            'POSTGRES_DB',
            'POSTGRES_USER',
            'POSTGRES_PASSWORD'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"   ⚠️ Missing environment variables: {', '.join(missing_vars)}")
            issues.append(f"Missing env vars: {', '.join(missing_vars)}")
        else:
            print("   ✅ All required environment variables are set")
    
    # Check data folder
    print("\n2. Checking data folder...")
    data_folder = Path("data")
    if not data_folder.exists():
        print("   ⚠️ data/ folder not found, creating it...")
        data_folder.mkdir(exist_ok=True)
        print("   ✅ data/ folder created")
        print("   📝 Place your PDF documents in the data/ folder")
    else:
        pdf_files = list(data_folder.glob("*.pdf"))
        if not pdf_files:
            print("   ⚠️ No PDF files found in data/ folder")
            print("   📝 Place your PDF documents in the data/ folder")
        else:
            print(f"   ✅ Found {len(pdf_files)} PDF file(s)")
    
    # Check chunks folder
    print("\n3. Checking chunks folder...")
    chunks_folder = Path("chunks")
    if not chunks_folder.exists():
        print("   📁 chunks/ folder not found, creating it...")
        chunks_folder.mkdir(exist_ok=True)
        print("   ✅ chunks/ folder created")
    else:
        print("   ✅ chunks/ folder exists")
    
    # Check Python version
    print("\n4. Checking Python version...")
    python_version = sys.version_info
    if python_version.major >= 3 and python_version.minor >= 9:
        print(f"   ✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    else:
        print(f"   ❌ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        print("   ⚠️ Python 3.9+ is required")
        issues.append("Python version < 3.9")
    
    # Check key dependencies
    print("\n5. Checking key dependencies...")
    dependencies = [
        'langgraph',
        'langchain',
        'pymupdf4llm',
        'boto3',
        'psycopg2',
        'pgvector',
        'fastmcp',
        'streamlit',
        'tiktoken',
        'jsonlines'
    ]
    
    missing_deps = []
    for dep in dependencies:
        try:
            __import__(dep.replace('-', '_'))
            print(f"   ✅ {dep}")
        except ImportError:
            print(f"   ❌ {dep}")
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"\n   ⚠️ Missing dependencies: {', '.join(missing_deps)}")
        print("   📝 Run: pip install -r requirements.txt")
        issues.append(f"Missing packages: {', '.join(missing_deps)}")
    
    # Summary
    print("\n" + "=" * 80)
    if issues:
        print("⚠️ SETUP ISSUES FOUND:")
        for issue in issues:
            print(f"   - {issue}")
        print("\n📝 Please resolve the issues above before running the pipeline.")
    else:
        print("✅ ENVIRONMENT SETUP COMPLETE")
        print("\n🚀 You're ready to run the pipeline!")
        print("\nNext steps:")
        print("   1. Place PDF documents in data/ folder")
        print("   2. Update .env with your AWS and PostgreSQL credentials")
        print("   3. Run: python main.py")
    print("=" * 80 + "\n")
    
    return len(issues) == 0


if __name__ == "__main__":
    check_environment()
