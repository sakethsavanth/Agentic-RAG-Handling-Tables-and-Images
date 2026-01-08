"""
Agent 1: Document Parse Agent
This agent lists documents, ingests them using PyMuPDF4LLM, applies two-pass hybrid chunking,
and stores chunks in PostgreSQL with support for text, images, and tables.
"""
import os
import sys
from pathlib import Path
import base64
import pymupdf4llm
import pymupdf
from typing import List, Dict, Any
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils import DatabaseManager, AWSBedrockClient, TwoPassHybridChunker, extract_tables_from_markdown
from mcp_server.sql_executor_mcp import MCPSQLExecutor

# Load environment variables
load_dotenv()


class DocumentParseState(TypedDict):
    """State for document parsing workflow"""
    data_folder: str
    documents: List[str]
    current_document: str
    markdown_text: str
    text_chunks: List[Dict[str, Any]]
    image_chunks: List[Dict[str, Any]]
    table_chunks: List[Dict[str, Any]]
    error: str


class DocumentParseAgent:
    """
    Agent 1: Document Parse Agent
    Handles document ingestion, parsing, chunking, and storage
    """
    
    def __init__(self, data_folder: str = "data"):
        """
        Initialize the Document Parse Agent
        
        Args:
            data_folder: Path to folder containing PDF documents
        """
        print("\n" + "=" * 80)
        print("🤖 INITIALIZING AGENT 1: DOCUMENT PARSE AGENT")
        print("=" * 80 + "\n")
        
        self.data_folder = data_folder
        self.db_manager = DatabaseManager()
        self.aws_client = AWSBedrockClient()
        self.chunker = TwoPassHybridChunker(target_token_size=800, overlap_percentage=0.1)
        self.mcp_executor = MCPSQLExecutor()
        
        # Initialize database with fresh reset
        if self.db_manager.connect():
            self.db_manager.reset_database()  # Drop all tables and recreate
        
        # Build LangGraph workflow
        self.workflow = self._build_workflow()
        
        print("✅ Document Parse Agent initialized successfully!\n")
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for document parsing"""
        workflow = StateGraph(DocumentParseState)
        
        # Add nodes
        workflow.add_node("list_documents", self.list_documents)
        workflow.add_node("parse_document", self.parse_document)
        workflow.add_node("extract_images", self.extract_images)
        workflow.add_node("extract_tables", self.extract_tables)
        workflow.add_node("chunk_text", self.chunk_text)
        workflow.add_node("store_chunks", self.store_chunks)
        
        # Define edges
        workflow.set_entry_point("list_documents")
        workflow.add_edge("list_documents", "parse_document")
        workflow.add_edge("parse_document", "extract_images")
        workflow.add_edge("extract_images", "extract_tables")
        workflow.add_edge("extract_tables", "chunk_text")
        workflow.add_edge("chunk_text", "store_chunks")
        workflow.add_edge("store_chunks", END)
        
        return workflow.compile()
    
    def list_documents(self, state: DocumentParseState) -> DocumentParseState:
        """List all PDF documents in the data folder"""
        print("\n" + "-" * 80)
        print("📂 STEP 1: LISTING DOCUMENTS")
        print("-" * 80)
        
        data_path = Path(self.data_folder)
        
        if not data_path.exists():
            print(f"❌ Data folder not found: {self.data_folder}")
            state['error'] = f"Data folder not found: {self.data_folder}"
            state['documents'] = []
            return state
        
        # Find all PDF files
        pdf_files = list(data_path.glob("*.pdf"))
        
        if not pdf_files:
            print(f"⚠️ No PDF files found in {self.data_folder}")
            state['documents'] = []
        else:
            print(f"✅ Found {len(pdf_files)} PDF document(s):")
            for i, pdf_file in enumerate(pdf_files, 1):
                print(f"   {i}. {pdf_file.name}")
            
            state['documents'] = [str(pdf_file) for pdf_file in pdf_files]
        
        print()
        return state
    
    def parse_document(self, state: DocumentParseState) -> DocumentParseState:
        """Parse document using PyMuPDF4LLM"""
        print("\n" + "-" * 80)
        print("📄 STEP 2: PARSING DOCUMENT WITH PYMUPDF4LLM")
        print("-" * 80)
        
        if not state.get('documents'):
            print("⚠️ No documents to parse")
            return state
        
        # For now, process the first document
        # In a full implementation, this would loop through all documents
        document_path = state['documents'][0]
        state['current_document'] = Path(document_path).stem
        
        print(f"📖 Processing: {Path(document_path).name}")
        print(f"🔧 Using PyMuPDF4LLM to extract markdown...\n")
        
        try:
            # Open document with PyMuPDF
            doc = pymupdf.open(document_path)
            print(f"   Pages: {len(doc)}")
            print(f"   Format: {doc.metadata.get('format', 'Unknown')}")
            
            # Extract markdown with page chunks for better structure
            md_text = pymupdf4llm.to_markdown(
                doc,
                page_chunks=False,  # We'll do our own chunking
                write_images=False,  # We'll extract images separately
                show_progress=True
            )
            
            state['markdown_text'] = md_text
            
            print(f"\n✅ Successfully extracted {len(md_text)} characters of markdown text")
            print(f"   Preview (first 200 chars):")
            print(f"   {md_text[:200]}...\n")
            
        except Exception as e:
            print(f"❌ Error parsing document: {str(e)}")
            state['error'] = str(e)
            state['markdown_text'] = ""
        
        return state
    
    def extract_images(self, state: DocumentParseState) -> DocumentParseState:
        """Extract and process images from the document"""
        print("\n" + "-" * 80)
        print("🖼️ STEP 3: EXTRACTING AND ANALYZING IMAGES")
        print("-" * 80)
        
        image_chunks = []
        all_image_sql_queries = []  # Store SQL from visualizations
        
        if not state.get('documents'):
            state['image_chunks'] = image_chunks
            return state
        
        document_path = state['documents'][0]
        source_document = state.get('current_document', Path(document_path).stem)
        
        try:
            doc = pymupdf.open(document_path)
            
            print(f"🔍 Scanning {len(doc)} pages for images...\n")
            
            image_counter = 0
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                if image_list:
                    print(f"   Page {page_num + 1}: Found {len(image_list)} image(s)")
                
                for img_index, img in enumerate(image_list):
                    image_counter += 1
                    xref = img[0]
                    
                    # Extract image
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Convert to base64
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    
                    # Extract page text for context
                    page_text = page.get_text()
                    
                    chunk_id = f"{source_document}_img_{image_counter}"
                    section_id = f"Page_{page_num + 1}"
                    
                    print(f"      🖼️ Processing image {image_counter} (format: {image_ext})...")
                    
                    # Analyze image with Nova to determine type
                    # First, try to detect if it's a visualization
                    analysis_result = self.aws_client.analyze_image(
                        image_base64=image_base64,
                        image_type="general",
                        page_context=page_text[:800]  # Pass page context
                    )
                    
                    if analysis_result['success']:
                        summary = analysis_result.get('summary', '')
                        
                        # Check if it's likely a data visualization
                        viz_keywords = ['chart', 'graph', 'plot', 'pie', 'bar', 'line', 'scatter', 
                                       'histogram', 'visualization', 'diagram']
                        is_visualization = any(keyword in summary.lower() for keyword in viz_keywords)
                        
                        if is_visualization:
                            print(f"         📊 Detected as data visualization")
                            print(f"         🔄 Re-analyzing to extract data table...")
                            
                            # Re-analyze as visualization to get SQL
                            viz_result = self.aws_client.analyze_image(
                                image_base64=image_base64,
                                image_type="visualization",
                                page_context=page_text[:800]  # Pass page context
                            )
                            
                            if viz_result['success'] and 'sql_query' in viz_result:
                                sql_query = viz_result['sql_query']
                                
                                # Make table name unique by appending image counter
                                # Extract table name and append suffix
                                import re
                                table_match = re.search(r'CREATE TABLE(?: IF NOT EXISTS)?\s+(\w+)', sql_query, re.IGNORECASE)
                                if table_match:
                                    original_table = table_match.group(1)
                                    unique_table = f"{original_table}_img{image_counter}"
                                    sql_query = sql_query.replace(original_table, unique_table, 1)  # Replace first occurrence
                                    # Also replace in INSERT statements
                                    sql_query = re.sub(f'INSERT INTO {original_table}', f'INSERT INTO {unique_table}', sql_query, flags=re.IGNORECASE)
                                
                                # Execute SQL via MCP
                                print(f"         🔧 Creating table via MCP...")
                                
                                # Store SQL query for file export
                                all_image_sql_queries.append(f"-- Visualization Image: {unique_table if table_match else 'unknown'}\n-- Source: {source_document}, Page {page_num + 1}, Image {image_counter}\n{sql_query}\n")
                                
                                mcp_result = self.mcp_executor.create_table(sql_query)
                                
                                if mcp_result['success']:
                                    print(f"         ✅ Table created successfully")
                                    
                                    image_chunks.append({
                                        'chunk_id': chunk_id,
                                        'chunk_type': 'image',
                                        'image_type': 'visualization',
                                        'section_id': section_id,
                                        'source_document': source_document,
                                        'image_base64': None,  # Don't store base64 for visualizations
                                        'image_summary': summary,
                                        'sql_query': sql_query,
                                        'metadata': {
                                            'page': page_num + 1,
                                            'image_format': image_ext,
                                            'is_visualization': True
                                        }
                                    })
                                else:
                                    print(f"         ⚠️ Table creation failed: {mcp_result['message']}")
                            else:
                                print(f"         ⚠️ Could not extract data table")
                        else:
                            print(f"         📷 Detected as general image")
                            print(f"         💬 Summary: {summary[:100]}...")
                            
                            # Store as general image with summary
                            image_chunks.append({
                                'chunk_id': chunk_id,
                                'chunk_type': 'image',
                                'image_type': 'general',
                                'section_id': section_id,
                                'source_document': source_document,
                                'image_base64': image_base64,
                                'image_summary': summary,
                                'metadata': {
                                    'page': page_num + 1,
                                    'image_format': image_ext,
                                    'is_visualization': False
                                }
                            })
                            print(f"         ✅ Image processed and stored")
                    else:
                        print(f"         ⚠️ Image analysis failed: {analysis_result.get('error', 'Unknown error')}")
            
            # Save all SQL queries from visualizations to a file
            if all_image_sql_queries:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                images_file = Path("generated_tables") / f"visualization_tables_{source_document}_{timestamp}.sql"
                images_file.parent.mkdir(exist_ok=True)
                
                try:
                    with open(images_file, 'w', encoding='utf-8') as f:
                        f.write(f"-- Generated Tables from Visualizations: {source_document}\n")
                        f.write(f"-- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"-- Total visualization tables: {len(all_image_sql_queries)}\n")
                        f.write("-- " + "="*70 + "\n\n")
                        f.write("\n\n".join(all_image_sql_queries))
                    print(f"\n💾 Saved {len(all_image_sql_queries)} visualization table(s) to: {images_file}")
                except Exception as e:
                    print(f"\n⚠️ Failed to save visualization tables to file: {str(e)}")
            
            print(f"\n✅ Extracted and processed {image_counter} images")
            print(f"   Visualizations: {sum(1 for img in image_chunks if img.get('image_type') == 'visualization')}")
            print(f"   General images: {sum(1 for img in image_chunks if img.get('image_type') == 'general')}\n")
            
        except Exception as e:
            print(f"❌ Error extracting images: {str(e)}\n")
            state['error'] = str(e)
        
        state['image_chunks'] = image_chunks
        return state
    
    def extract_tables(self, state: DocumentParseState) -> DocumentParseState:
        """Extract and process tables from markdown"""
        print("\n" + "-" * 80)
        print("📋 STEP 4: EXTRACTING AND ANALYZING TABLES")
        print("-" * 80)
        
        table_chunks = []
        all_sql_queries = []  # Store all SQL queries for file export
        
        markdown_text = state.get('markdown_text', '')
        source_document = state.get('current_document', 'unknown')
        
        if not markdown_text:
            print("⚠️ No markdown text available for table extraction\n")
            state['table_chunks'] = table_chunks
            return state
        
        # Extract tables from markdown
        tables = extract_tables_from_markdown(markdown_text)
        
        print(f"🔍 Found {len(tables)} table(s) in markdown\n")
        
        for table in tables:
            table_id = table['table_id']
            table_content = table['content']
            context_before = table.get('context_before', '')
            context_after = table.get('context_after', '')
            
            print(f"   📊 Processing {table_id}...")
            print(f"      Rows: {table['row_count']}")
            if context_before:
                print(f"      Context available: {len(context_before)} chars before, {len(context_after)} chars after")
            
            # Analyze table with Nova to get SQL CREATE TABLE statement
            analysis_result = self.aws_client.analyze_table(
                table_content, 
                context_before=context_before, 
                context_after=context_after
            )
            
            if analysis_result['success']:
                sql_query = analysis_result['sql_query']
                
                # Make table name unique by appending table_id
                import re
                table_match = re.search(r'CREATE TABLE(?: IF NOT EXISTS)?\s+(\w+)', sql_query, re.IGNORECASE)
                if table_match:
                    original_table = table_match.group(1)
                    unique_table = f"{original_table}_{table_id}"
                    # Replace in CREATE TABLE statement (first occurrence)
                    sql_query = sql_query.replace(original_table, unique_table, 1)
                    # Also replace in all INSERT statements
                    sql_query = re.sub(f'INSERT INTO {original_table}', f'INSERT INTO {unique_table}', sql_query, flags=re.IGNORECASE)
                
                print(f"      🔧 Generated SQL CREATE TABLE and INSERT statements")
                print(f"      📤 Executing via MCP...")
                
                # Store SQL query for file export
                all_sql_queries.append(f"-- Table: {unique_table if table_match else 'unknown'}\n-- Source: {source_document}, {table_id}\n{sql_query}\n")
                
                # Execute SQL via MCP
                mcp_result = self.mcp_executor.create_table(sql_query)
                
                if mcp_result['success']:
                    print(f"      ✅ Table created and data inserted in database")
                    
                    # Extract table name from SQL
                    table_name = "unknown_table"
                    if "CREATE TABLE" in sql_query.upper():
                        parts = sql_query.upper().split("CREATE TABLE")[1].split("(")[0].strip()
                        table_name = parts.split()[0].strip()
                    
                    table_chunks.append({
                        'chunk_id': f"{source_document}_{table_id}",
                        'chunk_type': 'table',
                        'section_id': table_id,
                        'source_document': source_document,
                        'table_name': table_name,
                        'sql_query': sql_query,
                        'metadata': {
                            'row_count': table['row_count'],
                            'original_markdown': table_content[:500]  # Store snippet
                        }
                    })
                else:
                    print(f"      ⚠️ Table creation failed: {mcp_result['message']}")
            else:
                print(f"      ⚠️ Table analysis failed: {analysis_result.get('error', 'Unknown error')}")
        
        # Save all SQL queries to a file before storing in PostgreSQL
        if all_sql_queries:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            tables_file = Path("generated_tables") / f"tables_{source_document}_{timestamp}.sql"
            tables_file.parent.mkdir(exist_ok=True)
            
            try:
                with open(tables_file, 'w', encoding='utf-8') as f:
                    f.write(f"-- Generated Tables from: {source_document}\n")
                    f.write(f"-- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"-- Total tables: {len(all_sql_queries)}\n")
                    f.write("-- " + "="*70 + "\n\n")
                    f.write("\n\n".join(all_sql_queries))
                print(f"\n💾 Saved {len(all_sql_queries)} table(s) to: {tables_file}")
            except Exception as e:
                print(f"\n⚠️ Failed to save tables to file: {str(e)}")
        
        print(f"\n✅ Processed {len(table_chunks)} table(s) successfully\n")
        
        state['table_chunks'] = table_chunks
        return state
    
    def chunk_text(self, state: DocumentParseState) -> DocumentParseState:
        """Apply two-pass hybrid chunking to the markdown text"""
        print("\n" + "-" * 80)
        print("🔪 STEP 5: APPLYING TWO-PASS HYBRID CHUNKING")
        print("-" * 80)
        
        markdown_text = state.get('markdown_text', '')
        source_document = state.get('current_document', 'unknown')
        
        if not markdown_text:
            print("⚠️ No markdown text available for chunking\n")
            state['text_chunks'] = []
            return state
        
        # Apply two-pass hybrid chunking
        text_chunks = self.chunker.chunk_document(markdown_text, source_document)
        
        state['text_chunks'] = text_chunks
        
        return state
    
    def store_chunks(self, state: DocumentParseState) -> DocumentParseState:
        """Store all chunks in PostgreSQL"""
        print("\n" + "-" * 80)
        print("💾 STEP 6: STORING CHUNKS IN POSTGRESQL")
        print("-" * 80)
        
        text_chunks = state.get('text_chunks', [])
        image_chunks = state.get('image_chunks', [])
        table_chunks = state.get('table_chunks', [])
        
        total_chunks = len(text_chunks) + len(image_chunks) + len(table_chunks)
        print(f"📦 Total chunks to store: {total_chunks}")
        print(f"   Text chunks: {len(text_chunks)}")
        print(f"   Image chunks: {len(image_chunks)}")
        print(f"   Table chunks: {len(table_chunks)}\n")
        
        # Store text chunks (without embeddings for now - Agent 2 will add them)
        print("💬 Storing text chunks...")
        for chunk in text_chunks:
            success = self.db_manager.insert_text_chunk(
                chunk_id=chunk['chunk_id'],
                content=chunk['content'],
                section_id=chunk['section_id'],
                source_document=chunk['source_document'],
                embedding=None,  # Will be added by Agent 2
                metadata=chunk['metadata']
            )
            if success:
                print(f"   ✅ Stored: {chunk['chunk_id']}")
        
        # Store image chunks
        print("\n🖼️ Storing image chunks...")
        for chunk in image_chunks:
            success = self.db_manager.insert_image_chunk(
                chunk_id=chunk['chunk_id'],
                section_id=chunk['section_id'],
                source_document=chunk['source_document'],
                image_type=chunk['image_type'],
                image_base64=chunk.get('image_base64'),
                image_summary=chunk.get('image_summary'),
                embedding=None,  # Will be added by Agent 2
                metadata=chunk['metadata']
            )
            if success:
                print(f"   ✅ Stored: {chunk['chunk_id']}")
        
        # Store table chunks
        print("\n📊 Storing table chunks...")
        for chunk in table_chunks:
            success = self.db_manager.insert_table_chunk(
                chunk_id=chunk['chunk_id'],
                section_id=chunk['section_id'],
                source_document=chunk['source_document'],
                table_name=chunk['table_name'],
                sql_query=chunk['sql_query'],
                metadata=chunk['metadata']
            )
            if success:
                print(f"   ✅ Stored: {chunk['chunk_id']}")
        
        print(f"\n✅ All chunks stored successfully in PostgreSQL!\n")
        
        return state
    
    def run(self) -> Dict[str, Any]:
        """Execute the document parsing workflow"""
        print("\n" + "=" * 80)
        print("🚀 STARTING DOCUMENT PARSING WORKFLOW")
        print("=" * 80)
        
        # Initial state
        initial_state = {
            'data_folder': self.data_folder,
            'documents': [],
            'current_document': '',
            'markdown_text': '',
            'text_chunks': [],
            'image_chunks': [],
            'table_chunks': [],
            'error': ''
        }
        
        # Run workflow
        final_state = self.workflow.invoke(initial_state)
        
        print("\n" + "=" * 80)
        print("✅ DOCUMENT PARSING WORKFLOW COMPLETED")
        print("=" * 80)
        
        # Summary
        print("\n📊 SUMMARY:")
        print(f"   Documents processed: {len(final_state.get('documents', []))}")
        print(f"   Text chunks created: {len(final_state.get('text_chunks', []))}")
        print(f"   Image chunks created: {len(final_state.get('image_chunks', []))}")
        print(f"   Table chunks created: {len(final_state.get('table_chunks', []))}")
        
        if final_state.get('error'):
            print(f"   ⚠️ Errors encountered: {final_state['error']}")
        
        print("\n")
        
        return final_state


def main():
    """Main entry point for Agent 1"""
    # Initialize and run agent
    agent = DocumentParseAgent(data_folder="data")
    result = agent.run()
    
    return result


if __name__ == "__main__":
    main()