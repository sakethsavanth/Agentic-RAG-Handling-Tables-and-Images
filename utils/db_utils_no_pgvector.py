"""
Database Utilities (pgvector-free version)
Manages PostgreSQL connections without pgvector extension
"""
import os
import json
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    """Manages PostgreSQL database without pgvector"""
    
    def __init__(self):
        self.conn_params = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'multimodal_rag'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', '')
        }
        self.conn = None
    
    def connect(self):
        """Connect to PostgreSQL"""
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**self.conn_params)
        return self.conn
    
    def close(self):
        """Close connection"""
        if self.conn:
            self.conn.close()
    
    def initialize_tables(self):
        """Create tables without vector type"""
        print("📊 Initializing database tables...")
        
        conn = self.connect()
        cursor = conn.cursor()
        
        # Text chunks table (using FLOAT[] instead of vector)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS text_chunks (
                id SERIAL PRIMARY KEY,
                chunk_id VARCHAR(255) UNIQUE NOT NULL,
                chunk_type VARCHAR(50) DEFAULT 'text',
                section_id VARCHAR(255),
                source_document VARCHAR(500),
                content TEXT NOT NULL,
                embedding FLOAT[],
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create index on embedding for similarity search
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS text_chunks_embedding_idx 
            ON text_chunks USING GIN (embedding);
        """)
        
        # Image chunks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_chunks (
                id SERIAL PRIMARY KEY,
                chunk_id VARCHAR(255) UNIQUE NOT NULL,
                chunk_type VARCHAR(50) DEFAULT 'image',
                section_id VARCHAR(255),
                source_document VARCHAR(500),
                image_path VARCHAR(500),
                image_base64 TEXT,
                summary TEXT,
                embedding FLOAT[],
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Table chunks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS table_chunks (
                id SERIAL PRIMARY KEY,
                chunk_id VARCHAR(255) UNIQUE NOT NULL,
                chunk_type VARCHAR(50) DEFAULT 'table',
                section_id VARCHAR(255),
                source_document VARCHAR(500),
                table_name VARCHAR(255),
                sql_query TEXT,
                table_data JSONB,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        conn.commit()
        cursor.close()
        
        print("✅ Tables created successfully (without pgvector)")
    
    def insert_text_chunk(self, chunk_data):
        """Insert text chunk"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Convert embedding list to PostgreSQL array format
        embedding_array = None
        if chunk_data.get('embedding'):
            embedding_array = chunk_data['embedding']
        
        cursor.execute("""
            INSERT INTO text_chunks 
            (chunk_id, chunk_type, section_id, source_document, content, embedding, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (chunk_id) DO UPDATE SET
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                metadata = EXCLUDED.metadata;
        """, (
            chunk_data['chunk_id'],
            chunk_data.get('chunk_type', 'text'),
            chunk_data.get('section_id'),
            chunk_data['source_document'],
            chunk_data['content'],
            embedding_array,
            json.dumps(chunk_data.get('metadata', {}))
        ))
        
        conn.commit()
        cursor.close()
    
    def insert_image_chunk(self, chunk_data):
        """Insert image chunk"""
        conn = self.connect()
        cursor = conn.cursor()
        
        embedding_array = None
        if chunk_data.get('embedding'):
            embedding_array = chunk_data['embedding']
        
        cursor.execute("""
            INSERT INTO image_chunks 
            (chunk_id, chunk_type, section_id, source_document, image_path, 
             image_base64, summary, embedding, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (chunk_id) DO UPDATE SET
                image_base64 = EXCLUDED.image_base64,
                summary = EXCLUDED.summary,
                embedding = EXCLUDED.embedding,
                metadata = EXCLUDED.metadata;
        """, (
            chunk_data['chunk_id'],
            chunk_data.get('chunk_type', 'image'),
            chunk_data.get('section_id'),
            chunk_data['source_document'],
            chunk_data.get('image_path'),
            chunk_data.get('image_base64'),
            chunk_data.get('summary'),
            embedding_array,
            json.dumps(chunk_data.get('metadata', {}))
        ))
        
        conn.commit()
        cursor.close()
    
    def insert_table_chunk(self, chunk_data):
        """Insert table chunk"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO table_chunks 
            (chunk_id, chunk_type, section_id, source_document, table_name, 
             sql_query, table_data, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (chunk_id) DO UPDATE SET
                sql_query = EXCLUDED.sql_query,
                table_data = EXCLUDED.table_data,
                metadata = EXCLUDED.metadata;
        """, (
            chunk_data['chunk_id'],
            chunk_data.get('chunk_type', 'table'),
            chunk_data.get('section_id'),
            chunk_data['source_document'],
            chunk_data.get('table_name'),
            chunk_data.get('sql_query'),
            json.dumps(chunk_data.get('table_data', {})),
            json.dumps(chunk_data.get('metadata', {}))
        ))
        
        conn.commit()
        cursor.close()
    
    def get_all_chunks(self):
        """Get all chunks from database"""
        conn = self.connect()
        cursor = conn.cursor()
        
        chunks = []
        
        # Get text chunks
        cursor.execute("SELECT chunk_id, content, embedding FROM text_chunks;")
        for row in cursor.fetchall():
            chunks.append({
                'chunk_id': row[0],
                'content': row[1],
                'embedding': row[2],
                'chunk_type': 'text'
            })
        
        # Get image chunks
        cursor.execute("SELECT chunk_id, summary, embedding FROM image_chunks;")
        for row in cursor.fetchall():
            chunks.append({
                'chunk_id': row[0],
                'content': row[1],
                'embedding': row[2],
                'chunk_type': 'image'
            })
        
        cursor.close()
        return chunks
    
    def cosine_similarity_search(self, query_embedding, top_k=5):
        """
        Perform cosine similarity search without pgvector
        Note: This is less efficient than pgvector but works without the extension
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        # Convert embedding to string for SQL
        embedding_str = ','.join(map(str, query_embedding))
        
        # Manual cosine similarity calculation
        # This is a simplified version - in production, you'd want to optimize this
        cursor.execute(f"""
            WITH query_vec AS (
                SELECT ARRAY[{embedding_str}]::float[] as vec
            )
            SELECT 
                chunk_id,
                content,
                embedding,
                (
                    SELECT SUM(a * b) / 
                    (SQRT(SUM(a * a)) * SQRT(SUM(b * b)))
                    FROM UNNEST(embedding) WITH ORDINALITY AS t1(a, i)
                    JOIN UNNEST((SELECT vec FROM query_vec)) WITH ORDINALITY AS t2(b, j) 
                    ON t1.i = t2.j
                ) as similarity
            FROM text_chunks
            WHERE embedding IS NOT NULL
            ORDER BY similarity DESC
            LIMIT %s;
        """, (top_k,))
        
        results = cursor.fetchall()
        cursor.close()
        
        return [
            {
                'chunk_id': row[0],
                'content': row[1],
                'embedding': row[2],
                'similarity': row[3]
            }
            for row in results
        ]
    
    def update_chunk_embedding(self, chunk_id, embedding):
        """Update chunk embedding"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE text_chunks 
            SET embedding = %s 
            WHERE chunk_id = %s;
        """, (embedding, chunk_id))
        
        cursor.execute("""
            UPDATE image_chunks 
            SET embedding = %s 
            WHERE chunk_id = %s;
        """, (embedding, chunk_id))
        
        conn.commit()
        cursor.close()
