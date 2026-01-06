"""
Agent 2: Document Embedder Agent
This agent embeds chunks using Amazon Titan model and saves them to JSONL files
"""
import os
import sys
from pathlib import Path
import json
import jsonlines
from typing import List, Dict, Any
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils import DatabaseManager, AWSBedrockClient

# Load environment variables
load_dotenv()


class DocumentEmbedderState(TypedDict):
    """State for document embedding workflow"""
    source_document: str
    text_chunks: List[Dict[str, Any]]
    image_chunks: List[Dict[str, Any]]
    embedded_chunks: List[Dict[str, Any]]
    output_file: str
    error: str


class DocumentEmbedderAgent:
    """
    Agent 2: Document Embedder Agent
    Handles embedding of chunks and saving to JSONL files
    """
    
    def __init__(self, chunks_folder: str = "chunks"):
        """
        Initialize the Document Embedder Agent
        
        Args:
            chunks_folder: Path to folder where JSONL files will be saved
        """
        print("\n" + "=" * 80)
        print("🤖 INITIALIZING AGENT 2: DOCUMENT EMBEDDER AGENT")
        print("=" * 80 + "\n")
        
        self.chunks_folder = Path(chunks_folder)
        self.chunks_folder.mkdir(exist_ok=True)
        
        self.db_manager = DatabaseManager()
        self.aws_client = AWSBedrockClient()
        
        # Initialize database connection
        if self.db_manager.connect():
            print("✅ Database connection established")
        
        # Build LangGraph workflow
        self.workflow = self._build_workflow()
        
        print("✅ Document Embedder Agent initialized successfully!\n")
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for embedding"""
        workflow = StateGraph(DocumentEmbedderState)
        
        # Add nodes
        workflow.add_node("fetch_chunks", self.fetch_chunks)
        workflow.add_node("embed_text_chunks", self.embed_text_chunks)
        workflow.add_node("embed_image_chunks", self.embed_image_chunks)
        workflow.add_node("update_database", self.update_database)
        workflow.add_node("save_to_jsonl", self.save_to_jsonl)
        
        # Define edges
        workflow.set_entry_point("fetch_chunks")
        workflow.add_edge("fetch_chunks", "embed_text_chunks")
        workflow.add_edge("embed_text_chunks", "embed_image_chunks")
        workflow.add_edge("embed_image_chunks", "update_database")
        workflow.add_edge("update_database", "save_to_jsonl")
        workflow.add_edge("save_to_jsonl", END)
        
        return workflow.compile()
    
    def fetch_chunks(self, state: DocumentEmbedderState) -> DocumentEmbedderState:
        """Fetch chunks from database for a specific document"""
        print("\n" + "-" * 80)
        print("📦 STEP 1: FETCHING CHUNKS FROM DATABASE")
        print("-" * 80)
        
        source_document = state.get('source_document', '')
        
        if not source_document:
            print("⚠️ No source document specified")
            state['text_chunks'] = []
            state['image_chunks'] = []
            return state
        
        print(f"📄 Fetching chunks for: {source_document}\n")
        
        try:
            # Fetch text chunks
            self.db_manager.cursor.execute("""
                SELECT chunk_id, chunk_type, section_id, source_document, content, 
                       metadata, embedding
                FROM text_chunks
                WHERE source_document = %s
                ORDER BY chunk_id;
            """, (source_document,))
            
            text_rows = self.db_manager.cursor.fetchall()
            text_chunks = []
            
            for row in text_rows:
                text_chunks.append({
                    'chunk_id': row['chunk_id'],
                    'chunk_type': row['chunk_type'],
                    'section_id': row['section_id'],
                    'source_document': row['source_document'],
                    'content': row['content'],
                    'metadata': row['metadata'] if row['metadata'] else {},
                    'embedding': row['embedding']
                })
            
            print(f"✅ Fetched {len(text_chunks)} text chunks")
            
            # Fetch image chunks
            self.db_manager.cursor.execute("""
                SELECT chunk_id, chunk_type, section_id, source_document, 
                       image_type, image_summary, metadata, embedding
                FROM image_chunks
                WHERE source_document = %s
                ORDER BY chunk_id;
            """, (source_document,))
            
            image_rows = self.db_manager.cursor.fetchall()
            image_chunks = []
            
            for row in image_rows:
                image_chunks.append({
                    'chunk_id': row['chunk_id'],
                    'chunk_type': row['chunk_type'],
                    'section_id': row['section_id'],
                    'source_document': row['source_document'],
                    'image_type': row['image_type'],
                    'image_summary': row['image_summary'],
                    'metadata': row['metadata'] if row['metadata'] else {},
                    'embedding': row['embedding']
                })
            
            print(f"✅ Fetched {len(image_chunks)} image chunks\n")
            
            state['text_chunks'] = text_chunks
            state['image_chunks'] = image_chunks
            
        except Exception as e:
            print(f"❌ Error fetching chunks: {str(e)}\n")
            state['error'] = str(e)
            state['text_chunks'] = []
            state['image_chunks'] = []
        
        return state
    
    def embed_text_chunks(self, state: DocumentEmbedderState) -> DocumentEmbedderState:
        """Generate embeddings for text chunks using Amazon Titan"""
        print("\n" + "-" * 80)
        print("🔤 STEP 2: EMBEDDING TEXT CHUNKS WITH AMAZON TITAN")
        print("-" * 80)
        
        text_chunks = state.get('text_chunks', [])
        
        if not text_chunks:
            print("⚠️ No text chunks to embed\n")
            return state
        
        print(f"🚀 Processing {len(text_chunks)} text chunks...\n")
        
        embedded_count = 0
        skipped_count = 0
        
        for i, chunk in enumerate(text_chunks, 1):
            chunk_id = chunk['chunk_id']
            
            # Skip if already embedded
            if chunk.get('embedding'):
                print(f"   [{i}/{len(text_chunks)}] ⏭️ Skipping {chunk_id} (already embedded)")
                skipped_count += 1
                continue
            
            print(f"   [{i}/{len(text_chunks)}] 🔄 Embedding {chunk_id}...")
            
            # Get embedding from Titan
            result = self.aws_client.get_titan_embeddings(chunk['content'])
            
            if result['success']:
                chunk['embedding'] = result['embedding']
                embedded_count += 1
                print(f"      ✅ Generated {result['dimension']}-dimensional embedding")
            else:
                print(f"      ❌ Failed: {result.get('error', 'Unknown error')}")
        
        print(f"\n📊 Text Embedding Summary:")
        print(f"   Successfully embedded: {embedded_count}")
        print(f"   Skipped (already embedded): {skipped_count}")
        print(f"   Failed: {len(text_chunks) - embedded_count - skipped_count}\n")
        
        state['text_chunks'] = text_chunks
        return state
    
    def embed_image_chunks(self, state: DocumentEmbedderState) -> DocumentEmbedderState:
        """Generate embeddings for image chunks using Amazon Titan"""
        print("\n" + "-" * 80)
        print("🖼️ STEP 3: EMBEDDING IMAGE CHUNKS WITH AMAZON TITAN")
        print("-" * 80)
        
        image_chunks = state.get('image_chunks', [])
        
        if not image_chunks:
            print("⚠️ No image chunks to embed\n")
            return state
        
        print(f"🚀 Processing {len(image_chunks)} image chunks...\n")
        
        embedded_count = 0
        skipped_count = 0
        
        for i, chunk in enumerate(image_chunks, 1):
            chunk_id = chunk['chunk_id']
            
            # Skip if already embedded
            if chunk.get('embedding'):
                print(f"   [{i}/{len(image_chunks)}] ⏭️ Skipping {chunk_id} (already embedded)")
                skipped_count += 1
                continue
            
            print(f"   [{i}/{len(image_chunks)}] 🔄 Embedding {chunk_id}...")
            
            # Use the image summary for embedding (text-based)
            # For general images, we embed the summary
            # For visualizations, we could embed structured data description
            
            image_summary = chunk.get('image_summary', '')
            
            if not image_summary:
                print(f"      ⚠️ No image summary available, skipping")
                continue
            
            # Get embedding from Titan (text model for summaries)
            result = self.aws_client.get_titan_embeddings(image_summary)
            
            if result['success']:
                chunk['embedding'] = result['embedding']
                embedded_count += 1
                print(f"      ✅ Generated {result['dimension']}-dimensional embedding")
            else:
                print(f"      ❌ Failed: {result.get('error', 'Unknown error')}")
        
        print(f"\n📊 Image Embedding Summary:")
        print(f"   Successfully embedded: {embedded_count}")
        print(f"   Skipped (already embedded): {skipped_count}")
        print(f"   Failed: {len(image_chunks) - embedded_count - skipped_count}\n")
        
        state['image_chunks'] = image_chunks
        return state
    
    def update_database(self, state: DocumentEmbedderState) -> DocumentEmbedderState:
        """Update database with embeddings"""
        print("\n" + "-" * 80)
        print("💾 STEP 4: UPDATING DATABASE WITH EMBEDDINGS")
        print("-" * 80)
        
        text_chunks = state.get('text_chunks', [])
        image_chunks = state.get('image_chunks', [])
        
        print(f"📝 Updating {len(text_chunks)} text chunks...")
        
        for chunk in text_chunks:
            if chunk.get('embedding'):
                try:
                    self.db_manager.cursor.execute("""
                        UPDATE text_chunks
                        SET embedding = %s
                        WHERE chunk_id = %s;
                    """, (chunk['embedding'], chunk['chunk_id']))
                    self.db_manager.conn.commit()  # Commit after each successful update
                    print(f"   ✅ Updated: {chunk['chunk_id']}")
                except Exception as e:
                    self.db_manager.conn.rollback()  # Rollback on error to prevent transaction abort
                    print(f"   ❌ Failed to update {chunk['chunk_id']}: {str(e)}")
        
        print(f"\n🖼️ Updating {len(image_chunks)} image chunks...")
        
        for chunk in image_chunks:
            if chunk.get('embedding'):
                try:
                    self.db_manager.cursor.execute("""
                        UPDATE image_chunks
                        SET embedding = %s
                        WHERE chunk_id = %s;
                    """, (chunk['embedding'], chunk['chunk_id']))
                    self.db_manager.conn.commit()  # Commit after each successful update
                    print(f"   ✅ Updated: {chunk['chunk_id']}")
                except Exception as e:
                    self.db_manager.conn.rollback()  # Rollback on error to prevent transaction abort
                    print(f"   ❌ Failed to update {chunk['chunk_id']}: {str(e)}")
        print(f"\n✅ Database updated successfully!\n")
        
        return state
    
    def save_to_jsonl(self, state: DocumentEmbedderState) -> DocumentEmbedderState:
        """Save chunks with embeddings to JSONL file"""
        print("\n" + "-" * 80)
        print("💾 STEP 5: SAVING CHUNKS TO JSONL FILE")
        print("-" * 80)
        
        source_document = state.get('source_document', 'unknown')
        text_chunks = state.get('text_chunks', [])
        image_chunks = state.get('image_chunks', [])
        
        # Combine all chunks
        all_chunks = text_chunks + image_chunks
        
        if not all_chunks:
            print("⚠️ No chunks to save\n")
            return state
        
        # Create output filename
        output_file = self.chunks_folder / f"{source_document}_chunks.jsonl"
        
        print(f"📁 Output file: {output_file}")
        print(f"📦 Total chunks: {len(all_chunks)}\n")
        
        try:
            with jsonlines.open(output_file, mode='w') as writer:
                for chunk in all_chunks:
                    # Convert embedding to list if needed
                    chunk_data = {
                        'chunk_id': chunk['chunk_id'],
                        'chunk_type': chunk['chunk_type'],
                        'section_id': chunk['section_id'],
                        'source_document': chunk['source_document'],
                        'metadata': chunk.get('metadata', {}),
                        'embedding': chunk.get('embedding', [])
                    }
                    
                    # Add content based on chunk type
                    if chunk['chunk_type'] == 'text':
                        chunk_data['content'] = chunk.get('content', '')
                    elif chunk['chunk_type'] == 'image':
                        chunk_data['image_type'] = chunk.get('image_type', '')
                        chunk_data['image_summary'] = chunk.get('image_summary', '')
                    
                    writer.write(chunk_data)
                    print(f"   ✅ Saved: {chunk['chunk_id']}")
            
            print(f"\n✅ Successfully saved {len(all_chunks)} chunks to {output_file}\n")
            
            state['output_file'] = str(output_file)
            state['embedded_chunks'] = all_chunks
            
        except Exception as e:
            print(f"❌ Error saving to JSONL: {str(e)}\n")
            state['error'] = str(e)
        
        return state
    
    def run(self, source_document: str) -> Dict[str, Any]:
        """Execute the embedding workflow for a specific document"""
        print("\n" + "=" * 80)
        print("🚀 STARTING DOCUMENT EMBEDDING WORKFLOW")
        print("=" * 80)
        
        # Initial state
        initial_state = {
            'source_document': source_document,
            'text_chunks': [],
            'image_chunks': [],
            'embedded_chunks': [],
            'output_file': '',
            'error': ''
        }
        
        # Run workflow
        final_state = self.workflow.invoke(initial_state)
        
        print("\n" + "=" * 80)
        print("✅ DOCUMENT EMBEDDING WORKFLOW COMPLETED")
        print("=" * 80)
        
        # Summary
        print("\n📊 SUMMARY:")
        print(f"   Document: {source_document}")
        print(f"   Total chunks embedded: {len(final_state.get('embedded_chunks', []))}")
        print(f"   Output file: {final_state.get('output_file', 'N/A')}")
        
        if final_state.get('error'):
            print(f"   ⚠️ Errors encountered: {final_state['error']}")
        
        print("\n")
        
        return final_state
    
    def run_all_documents(self) -> List[Dict[str, Any]]:
        """Run embedding for all documents in the database"""
        print("\n" + "=" * 80)
        print("🔄 EMBEDDING ALL DOCUMENTS")
        print("=" * 80 + "\n")
        
        # Get list of unique source documents
        self.db_manager.cursor.execute("""
            SELECT DISTINCT source_document 
            FROM text_chunks
            UNION
            SELECT DISTINCT source_document
            FROM image_chunks;
        """)
        
        documents = [row['source_document'] for row in self.db_manager.cursor.fetchall()]
        
        print(f"📚 Found {len(documents)} document(s) to process:")
        for doc in documents:
            print(f"   - {doc}")
        print()
        
        results = []
        
        for doc in documents:
            result = self.run(doc)
            results.append(result)
        
        print("\n" + "=" * 80)
        print("✅ ALL DOCUMENTS EMBEDDED SUCCESSFULLY")
        print("=" * 80 + "\n")
        
        return results


def main():
    """Main entry point for Agent 2"""
    # Initialize agent
    agent = DocumentEmbedderAgent(chunks_folder="chunks")
    
    # Run for all documents
    results = agent.run_all_documents()
    
    return results


if __name__ == "__main__":
    main()
