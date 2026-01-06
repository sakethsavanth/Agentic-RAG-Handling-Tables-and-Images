"""
Database utilities for PostgreSQL with pgvector support
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector
from typing import List, Dict, Any
import json


class DatabaseManager:
    def __init__(self):
        """Initialize database connection using environment variables"""
        print("🔌 Initializing Database Connection...")
        self.conn_params = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'multimodal_rag'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', '')
        }
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Establish database connection"""
        try:
            print(f"📡 Connecting to PostgreSQL at {self.conn_params['host']}:{self.conn_params['port']}...")
            self.conn = psycopg2.connect(**self.conn_params)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            
            # Register pgvector extension
            register_vector(self.conn)
            
            # Enable pgvector extension if not already enabled
            self.cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            self.conn.commit()
            
            print("✅ Database connection established successfully!")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to database: {str(e)}")
            return False
    
    def create_tables(self):
        """Create necessary tables for storing chunks"""
        print("\n📊 Creating database tables...")
        
        try:
            # Table for text chunks with vector embeddings
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS text_chunks (
                    chunk_id VARCHAR(255) PRIMARY KEY,
                    chunk_type VARCHAR(50) DEFAULT 'text',
                    section_id VARCHAR(255),
                    source_document VARCHAR(500),
                    content TEXT,
                    embedding vector(1024),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            print("✅ Created/verified text_chunks table")
            
            # Table for images (relational data)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS image_chunks (
                    chunk_id VARCHAR(255) PRIMARY KEY,
                    chunk_type VARCHAR(50) DEFAULT 'image',
                    section_id VARCHAR(255),
                    source_document VARCHAR(500),
                    image_type VARCHAR(50),
                    image_base64 TEXT,
                    image_summary TEXT,
                    embedding vector(1024),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            print("✅ Created/verified image_chunks table")
            
            # Table for table chunks (relational data)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS table_chunks (
                    chunk_id VARCHAR(255) PRIMARY KEY,
                    chunk_type VARCHAR(50) DEFAULT 'table',
                    section_id VARCHAR(255),
                    source_document VARCHAR(500),
                    table_name VARCHAR(255),
                    sql_query TEXT,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            print("✅ Created/verified table_chunks table")
            
            # Create indexes for better performance
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_text_chunks_embedding 
                ON text_chunks USING ivfflat (embedding vector_cosine_ops);
            """)
            
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_image_chunks_embedding 
                ON image_chunks USING ivfflat (embedding vector_cosine_ops);
            """)
            
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_source_document 
                ON text_chunks(source_document);
            """)
            
            print("✅ Created indexes for optimized retrieval")
            
            self.conn.commit()
            print("✅ All tables created successfully!\n")
            
        except Exception as e:
            print(f"❌ Error creating tables: {str(e)}")
            self.conn.rollback()
            raise
    
    def drop_all_tables(self):
        """Drop all tables in the database to start fresh"""
        print("\n🗑️ Dropping all existing tables...")
        
        try:
            # Get all table names in the public schema
            self.cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public';
            """)
            
            tables = [row['tablename'] for row in self.cursor.fetchall()]
            
            if tables:
                print(f"   Found {len(tables)} table(s) to drop")
                
                # Drop each table
                for table in tables:
                    self.cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                    print(f"   ✅ Dropped: {table}")
                
                self.conn.commit()
                print("✅ All tables dropped successfully!\n")
            else:
                print("   No tables found to drop\n")
                
        except Exception as e:
            print(f"❌ Error dropping tables: {str(e)}")
            self.conn.rollback()
            raise
    
    def reset_database(self):
        """Reset database by dropping all tables and recreating core tables"""
        print("\n" + "=" * 60)
        print("🔄 RESETTING DATABASE")
        print("=" * 60)
        
        self.drop_all_tables()
        self.create_tables()
        
        print("✅ Database reset complete!\n")
    
    def insert_text_chunk(self, chunk_id: str, content: str, section_id: str, 
                         source_document: str, embedding: List[float] = None, 
                         metadata: Dict = None):
        """Insert a text chunk into the database"""
        try:
            self.cursor.execute("""
                INSERT INTO text_chunks 
                (chunk_id, chunk_type, section_id, source_document, content, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata;
            """, (chunk_id, 'text', section_id, source_document, content, 
                  embedding, json.dumps(metadata) if metadata else None))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Error inserting text chunk {chunk_id}: {str(e)}")
            self.conn.rollback()
            return False
    
    def insert_image_chunk(self, chunk_id: str, section_id: str, source_document: str,
                          image_type: str, image_base64: str = None, image_summary: str = None,
                          embedding: List[float] = None, metadata: Dict = None):
        """Insert an image chunk into the database"""
        try:
            self.cursor.execute("""
                INSERT INTO image_chunks 
                (chunk_id, chunk_type, section_id, source_document, image_type, 
                 image_base64, image_summary, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    image_base64 = EXCLUDED.image_base64,
                    image_summary = EXCLUDED.image_summary,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata;
            """, (chunk_id, 'image', section_id, source_document, image_type,
                  image_base64, image_summary, embedding, json.dumps(metadata) if metadata else None))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Error inserting image chunk {chunk_id}: {str(e)}")
            self.conn.rollback()
            return False
    
    def insert_table_chunk(self, chunk_id: str, section_id: str, source_document: str,
                          table_name: str, sql_query: str, metadata: Dict = None):
        """Insert a table chunk into the database"""
        try:
            self.cursor.execute("""
                INSERT INTO table_chunks 
                (chunk_id, chunk_type, section_id, source_document, table_name, sql_query, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    sql_query = EXCLUDED.sql_query,
                    metadata = EXCLUDED.metadata;
            """, (chunk_id, 'table', section_id, source_document, table_name, 
                  sql_query, json.dumps(metadata) if metadata else None))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Error inserting table chunk {chunk_id}: {str(e)}")
            self.conn.rollback()
            return False
    
    def execute_sql(self, sql_query: str):
        """Execute a SQL query (for MCP server)"""
        try:
            self.cursor.execute(sql_query)
            self.conn.commit()
            return True, "Query executed successfully"
        except Exception as e:
            self.conn.rollback()
            return False, str(e)
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("🔌 Database connection closed")
