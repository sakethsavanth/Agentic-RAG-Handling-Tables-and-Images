"""
Credentials Test Script
Tests AWS Bedrock and PostgreSQL connections before running the main pipeline
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("\n" + "=" * 80)
print("🔐 CREDENTIALS TEST SCRIPT")
print("=" * 80 + "\n")


def test_postgresql():
    """Test PostgreSQL connection"""
    print("\n" + "-" * 80)
    print("🐘 TESTING POSTGRESQL CONNECTION")
    print("-" * 80)
    
    try:
        import psycopg2
        
        # Get credentials
        conn_params = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'multimodal_rag'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', '')
        }
        
        print(f"📡 Attempting connection to:")
        print(f"   Host: {conn_params['host']}")
        print(f"   Port: {conn_params['port']}")
        print(f"   Database: {conn_params['database']}")
        print(f"   User: {conn_params['user']}")
        print()
        
        # Test connection
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        print("✅ PostgreSQL connection successful!\n")
        
        # Test pgvector extension
        print("🔍 Checking pgvector extension...")
        cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
        result = cursor.fetchone()
        
        if result:
            print("✅ pgvector extension is installed\n")
            try:
                from pgvector.psycopg2 import register_vector
                register_vector(conn)
                print("✅ pgvector registered successfully\n")
            except ImportError:
                print("⚠️ pgvector Python package not installed")
                print("   Run: pip install pgvector\n")
        else:
            print("⚠️ pgvector extension NOT found")
            print("   You can either:")
            print("   1. Install pgvector (run: python install_pgvector.py)")
            print("   2. Use the non-pgvector version (works but slower)")
            print()
        
        # Test database version
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"📊 PostgreSQL Version:")
        print(f"   {version.split(',')[0]}\n")
        
        # Check if tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('text_chunks', 'image_chunks', 'table_chunks');
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        if existing_tables:
            print(f"📋 Found existing tables: {', '.join(existing_tables)}")
            
            # Count chunks in each table
            for table in existing_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                print(f"   {table}: {count} chunks")
            print()
        else:
            print("📋 No RAG tables found yet (will be created on first run)\n")
        
        cursor.close()
        conn.close()
        
        return True
        
    except ImportError as e:
        print(f"❌ Missing Python package: {str(e)}")
        print("   Run: pip install psycopg2-binary\n")
        return False
        
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {str(e)}\n")
        print("💡 Troubleshooting:")
        print("   1. Check if PostgreSQL is running")
        print("   2. Verify credentials in .env file")
        print("   3. Ensure database exists")
        print("   4. Check port (default is 5432, not 5433)")
        print("\n   Run: python setup_postgres_interactive.py for guided setup\n")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}\n")
        return False


def test_aws_bedrock():
    """Test AWS Bedrock connection and models"""
    print("\n" + "-" * 80)
    print("☁️ TESTING AWS BEDROCK CONNECTION")
    print("-" * 80)
    
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        
        # Get credentials
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        aws_region = os.getenv('AWS_REGION', 'us-east-1')
        
        if not aws_access_key or not aws_secret_key:
            print("❌ AWS credentials not found in .env file\n")
            print("💡 Add to .env:")
            print("   AWS_ACCESS_KEY_ID=your_key")
            print("   AWS_SECRET_ACCESS_KEY=your_secret")
            print("   AWS_REGION=us-east-1\n")
            return False
        
        print(f"📡 Testing AWS Bedrock in region: {aws_region}")
        print(f"   Access Key: {aws_access_key[:8]}...{aws_access_key[-4:]}")
        print()
        
        # Initialize Bedrock Runtime client
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        print("✅ AWS Bedrock client initialized successfully\n")
        
        # Test Amazon Nova (for image/table analysis)
        print("🤖 Testing Amazon Nova model...")
        try:
            import json
            
            test_prompt = "Hello, this is a test. Please respond with 'Nova is working'."
            
            body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": test_prompt
                            }
                        ]
                    }
                ],
                "inferenceConfig": {
                    "max_new_tokens": 100,
                    "temperature": 0.3
                }
            }
            
            response = bedrock_runtime.invoke_model(
                modelId="us.amazon.nova-lite-v1:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            
            if 'output' in response_body:
                print("✅ Amazon Nova is accessible and working!")
                content = response_body['output']['message']['content']
                if isinstance(content, list) and len(content) > 0:
                    response_text = content[0].get('text', '')[:100]
                    print(f"   Response preview: {response_text}...")
                print()
            else:
                print("⚠️ Nova responded but format is unexpected\n")
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            print(f"❌ Amazon Nova test failed: {error_code}")
            
            if 'AccessDenied' in error_code:
                print("   💡 Your AWS account doesn't have access to Nova")
                print("   Check: https://console.aws.amazon.com/bedrock/")
            elif 'ResourceNotFound' in error_code:
                print("   💡 Nova model not available in this region")
                print(f"   Current region: {aws_region}")
            else:
                print(f"   Error details: {e.response['Error']['Message']}")
            print()
        
        # Test Amazon Titan Embeddings
        print("🔤 Testing Amazon Titan Embeddings model...")
        try:
            test_text = "This is a test for embeddings."
            
            body = json.dumps({
                "inputText": test_text
            })
            
            response = bedrock_runtime.invoke_model(
                modelId="amazon.titan-embed-text-v2:0",
                contentType="application/json",
                accept="application/json",
                body=body
            )
            
            response_body = json.loads(response['body'].read())
            embedding = response_body.get('embedding', [])
            
            if embedding:
                print(f"✅ Amazon Titan Embeddings is accessible and working!")
                print(f"   Embedding dimension: {len(embedding)}")
                print()
            else:
                print("⚠️ Titan responded but no embedding received\n")
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            print(f"❌ Amazon Titan test failed: {error_code}")
            
            if 'AccessDenied' in error_code:
                print("   💡 Your AWS account doesn't have access to Titan")
                print("   Check: https://console.aws.amazon.com/bedrock/")
            elif 'ResourceNotFound' in error_code:
                print("   💡 Titan model not available in this region")
                print(f"   Current region: {aws_region}")
            else:
                print(f"   Error details: {e.response['Error']['Message']}")
            print()
        
        return True
        
    except ImportError as e:
        print(f"❌ Missing Python package: {str(e)}")
        print("   Run: pip install boto3\n")
        return False
        
    except NoCredentialsError:
        print("❌ AWS credentials not found or invalid\n")
        print("💡 Check your .env file:\n")
        print("   AWS_ACCESS_KEY_ID=your_key")
        print("   AWS_SECRET_ACCESS_KEY=your_secret")
        print("   AWS_REGION=us-east-1\n")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}\n")
        return False


def main():
    """Run all credential tests"""
    
    # Check if .env file exists
    if not Path('.env').exists():
        print("❌ .env file not found!\n")
        print("💡 Create .env file:")
        print("   1. Copy .env.example to .env")
        print("   2. Add your AWS and PostgreSQL credentials\n")
        print("=" * 80 + "\n")
        return
    
    results = {
        'postgresql': False,
        'aws_bedrock': False
    }
    
    # Test PostgreSQL
    results['postgresql'] = test_postgresql()
    
    # Test AWS Bedrock
    results['aws_bedrock'] = test_aws_bedrock()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80 + "\n")
    
    if results['postgresql']:
        print("✅ PostgreSQL: READY")
    else:
        print("❌ PostgreSQL: FAILED")
    
    if results['aws_bedrock']:
        print("✅ AWS Bedrock: READY")
    else:
        print("❌ AWS Bedrock: FAILED")
    
    print()
    
    if all(results.values()):
        print("🎉 ALL TESTS PASSED!")
        print("✅ You're ready to run: python main.py")
    else:
        print("⚠️ SOME TESTS FAILED")
        print("💡 Please fix the issues above before running the pipeline")
    
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()

'''
# ...existing code...


# ...existing code...'''
