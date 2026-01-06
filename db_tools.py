"""
Utility script for common database and maintenance tasks
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from utils import DatabaseManager
import argparse


def reset_database():
    """Reset the database by dropping and recreating all tables"""
    print("\n⚠️ WARNING: This will delete all data in the database!")
    confirm = input("Type 'YES' to confirm: ")
    
    if confirm != 'YES':
        print("❌ Operation cancelled")
        return
    
    print("\n🔄 Resetting database...")
    
    db = DatabaseManager()
    if db.connect():
        try:
            # Drop existing tables
            db.cursor.execute("DROP TABLE IF EXISTS text_chunks CASCADE;")
            db.cursor.execute("DROP TABLE IF EXISTS image_chunks CASCADE;")
            db.cursor.execute("DROP TABLE IF EXISTS table_chunks CASCADE;")
            db.conn.commit()
            print("✅ Dropped existing tables")
            
            # Recreate tables
            db.create_tables()
            print("✅ Database reset complete!")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        finally:
            db.close()


def show_stats():
    """Show statistics about stored chunks"""
    print("\n📊 Database Statistics\n")
    
    db = DatabaseManager()
    if db.connect():
        try:
            # Text chunks
            db.cursor.execute("SELECT COUNT(*), COUNT(embedding) FROM text_chunks;")
            text_total, text_embedded = db.cursor.fetchone()
            print(f"Text Chunks:")
            print(f"  Total: {text_total}")
            print(f"  Embedded: {text_embedded}")
            print(f"  Pending: {text_total - text_embedded}")
            
            # Image chunks
            db.cursor.execute("SELECT COUNT(*), COUNT(embedding) FROM image_chunks;")
            image_total, image_embedded = db.cursor.fetchone()
            print(f"\nImage Chunks:")
            print(f"  Total: {image_total}")
            print(f"  Embedded: {image_embedded}")
            print(f"  Pending: {image_total - image_embedded}")
            
            # Table chunks
            db.cursor.execute("SELECT COUNT(*) FROM table_chunks;")
            table_total = db.cursor.fetchone()[0]
            print(f"\nTable Chunks:")
            print(f"  Total: {table_total}")
            
            # Documents
            db.cursor.execute("""
                SELECT DISTINCT source_document FROM text_chunks
                UNION
                SELECT DISTINCT source_document FROM image_chunks
                UNION
                SELECT DISTINCT source_document FROM table_chunks;
            """)
            documents = db.cursor.fetchall()
            print(f"\nDocuments:")
            print(f"  Total: {len(documents)}")
            for doc in documents:
                print(f"    - {doc[0]}")
            
            print()
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        finally:
            db.close()


def list_chunks(document_name=None):
    """List chunks in the database"""
    print("\n📋 Chunks List\n")
    
    db = DatabaseManager()
    if db.connect():
        try:
            if document_name:
                query = "SELECT chunk_id, chunk_type, section_id FROM text_chunks WHERE source_document = %s"
                db.cursor.execute(query, (document_name,))
            else:
                query = "SELECT chunk_id, chunk_type, section_id, source_document FROM text_chunks LIMIT 50"
                db.cursor.execute(query)
            
            rows = db.cursor.fetchall()
            
            if not rows:
                print("No chunks found")
            else:
                for row in rows:
                    if document_name:
                        print(f"  {row[0]} | {row[1]} | {row[2]}")
                    else:
                        print(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]}")
            
            print(f"\nShowing {len(rows)} chunks")
            print()
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        finally:
            db.close()


def test_connection():
    """Test database connection"""
    print("\n🔌 Testing Database Connection...\n")
    
    db = DatabaseManager()
    if db.connect():
        print("✅ Successfully connected to PostgreSQL")
        
        # Test pgvector
        try:
            db.cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
            result = db.cursor.fetchone()
            if result:
                print("✅ pgvector extension is installed")
            else:
                print("❌ pgvector extension is NOT installed")
        except Exception as e:
            print(f"❌ Error checking pgvector: {str(e)}")
        
        db.close()
        print()
    else:
        print("❌ Failed to connect to PostgreSQL")
        print("Please check your .env configuration")
        print()


def main():
    parser = argparse.ArgumentParser(description="Database utility tools")
    parser.add_argument('command', choices=['reset', 'stats', 'list', 'test'],
                       help='Command to execute')
    parser.add_argument('--document', help='Document name for list command')
    
    args = parser.parse_args()
    
    if args.command == 'reset':
        reset_database()
    elif args.command == 'stats':
        show_stats()
    elif args.command == 'list':
        list_chunks(args.document)
    elif args.command == 'test':
        test_connection()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("\n📚 Database Utility Tools\n")
        print("Usage: python db_tools.py <command>\n")
        print("Commands:")
        print("  test   - Test database connection")
        print("  stats  - Show database statistics")
        print("  list   - List chunks (use --document to filter)")
        print("  reset  - Reset database (WARNING: deletes all data)")
        print("\nExamples:")
        print("  python db_tools.py test")
        print("  python db_tools.py stats")
        print("  python db_tools.py list --document mydoc")
        print("  python db_tools.py reset")
        print()
    else:
        main()
