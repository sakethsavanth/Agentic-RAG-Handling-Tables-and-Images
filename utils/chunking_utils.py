"""
Helper utilities for chunking and text processing
"""
import tiktoken
from typing import List, Dict, Any
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


class TwoPassHybridChunker:
    """
    Two-Pass Hybrid Chunker that prioritizes document hierarchy before enforcing token limits
    """
    
    def __init__(self, target_token_size: int = 800, overlap_percentage: float = 0.1):
        """
        Initialize the chunker
        
        Args:
            target_token_size: Target size for chunks in tokens (700-900 range)
            overlap_percentage: Percentage of overlap between chunks (0.1 = 10%)
        """
        print(f"📝 Initializing Two-Pass Hybrid Chunker...")
        print(f"   Target token size: {target_token_size}")
        print(f"   Overlap: {int(overlap_percentage * 100)}%\n")
        
        self.target_token_size = target_token_size
        self.overlap_percentage = overlap_percentage
        self.overlap_size = int(target_token_size * overlap_percentage)
        
        # Initialize tokenizer (using tiktoken for GPT-style tokenization)
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # First Pass: Header-based splitter
        self.headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
            ("#####", "Header 5"),
            ("######", "Header 6"),
        ]
        
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            strip_headers=False
        )
        
        # Second Pass: Recursive character splitter
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.target_token_size * 4,  # Approximate characters (4 chars ≈ 1 token)
            chunk_overlap=self.overlap_size * 4,
            length_function=self.count_tokens,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken"""
        return len(self.tokenizer.encode(text))
    
    def chunk_document(self, markdown_text: str, source_document: str) -> List[Dict[str, Any]]:
        """
        Apply two-pass hybrid chunking strategy
        
        Args:
            markdown_text: The markdown text to chunk
            source_document: Name of the source document
            
        Returns:
            List of chunk dictionaries with metadata
        """
        print(f"🔪 Starting Two-Pass Hybrid Chunking for: {source_document}")
        
        chunks = []
        
        # FIRST PASS: Split by headers to preserve document hierarchy
        print("📑 First Pass: Splitting by headers...")
        try:
            header_splits = self.markdown_splitter.split_text(markdown_text)
            print(f"   Found {len(header_splits)} header-based sections")
        except Exception as e:
            print(f"   ⚠️ Header splitting failed: {e}")
            print(f"   Falling back to treating entire document as one section")
            header_splits = [{"content": markdown_text, "metadata": {}}]
        
        # SECOND PASS: Within each header section, apply recursive character splitting
        print("🔨 Second Pass: Applying token-limit splitting...")
        
        chunk_id_counter = 0
        
        for section_idx, section in enumerate(header_splits):
            # Extract section content and metadata
            if hasattr(section, 'page_content'):
                section_content = section.page_content
                section_metadata = section.metadata
            elif isinstance(section, dict):
                section_content = section.get('content', '')
                section_metadata = section.get('metadata', {})
            else:
                section_content = str(section)
                section_metadata = {}
            
            # Generate section ID from headers
            section_id = self._generate_section_id(section_metadata, section_idx)
            
            # Check if section needs further splitting
            token_count = self.count_tokens(section_content)
            
            if token_count <= self.target_token_size:
                # Section is small enough, keep as single chunk
                chunk_id_counter += 1
                chunks.append({
                    'chunk_id': f"{source_document}_chunk_{chunk_id_counter}",
                    'chunk_type': 'text',
                    'section_id': section_id,
                    'source_document': source_document,
                    'content': section_content,
                    'metadata': {
                        **section_metadata,
                        'token_count': token_count,
                        'is_split': False
                    }
                })
            else:
                # Section exceeds limit, apply recursive splitting
                print(f"   ⚡ Section '{section_id}' has {token_count} tokens, splitting further...")
                
                sub_chunks = self.recursive_splitter.split_text(section_content)
                
                for sub_chunk in sub_chunks:
                    chunk_id_counter += 1
                    token_count = self.count_tokens(sub_chunk)
                    
                    chunks.append({
                        'chunk_id': f"{source_document}_chunk_{chunk_id_counter}",
                        'chunk_type': 'text',
                        'section_id': section_id,
                        'source_document': source_document,
                        'content': sub_chunk,
                        'metadata': {
                            **section_metadata,
                            'token_count': token_count,
                            'is_split': True
                        }
                    })
        
        print(f"✅ Chunking complete: {len(chunks)} chunks created\n")
        
        # Print statistics
        self._print_chunking_stats(chunks)
        
        return chunks
    
    def _generate_section_id(self, metadata: Dict, section_idx: int) -> str:
        """Generate a section ID from header metadata"""
        headers = []
        for i in range(1, 7):
            header_key = f"Header {i}"
            if header_key in metadata:
                headers.append(metadata[header_key])
        
        if headers:
            return " > ".join(headers)
        else:
            return f"Section_{section_idx + 1}"
    
    def _print_chunking_stats(self, chunks: List[Dict[str, Any]]):
        """Print statistics about the chunking results"""
        if not chunks:
            return
        
        token_counts = [chunk['metadata'].get('token_count', 0) for chunk in chunks]
        avg_tokens = sum(token_counts) / len(token_counts) if token_counts else 0
        min_tokens = min(token_counts) if token_counts else 0
        max_tokens = max(token_counts) if token_counts else 0
        
        print("📊 Chunking Statistics:")
        print(f"   Total chunks: {len(chunks)}")
        print(f"   Average tokens per chunk: {avg_tokens:.1f}")
        print(f"   Min tokens: {min_tokens}")
        print(f"   Max tokens: {max_tokens}")
        print(f"   Target range: 700-900 tokens\n")


def extract_tables_from_markdown(markdown_text: str, context_lines: int = 5) -> List[Dict[str, Any]]:
    """
    Extract tables from markdown text along with surrounding context
    
    Args:
        markdown_text: The markdown text to extract tables from
        context_lines: Number of lines before/after table to capture as context
    
    Returns:
        List of dictionaries containing table information with context
    """
    tables = []
    lines = markdown_text.split('\n')
    
    current_table = []
    in_table = False
    table_idx = 0
    table_start_idx = 0
    
    for line_idx, line in enumerate(lines):
        # Check if line is part of a markdown table (contains |)
        if '|' in line and line.strip():
            if not in_table:
                in_table = True
                table_idx += 1
                current_table = []
                table_start_idx = line_idx
            current_table.append(line)
        else:
            if in_table and current_table:
                # End of table - capture context
                table_end_idx = line_idx
                
                # Get preceding context (up to context_lines before table)
                context_before_start = max(0, table_start_idx - context_lines)
                context_before = '\n'.join(lines[context_before_start:table_start_idx])
                
                # Get following context (up to context_lines after table)
                context_after_end = min(len(lines), table_end_idx + context_lines)
                context_after = '\n'.join(lines[table_end_idx:context_after_end])
                
                tables.append({
                    'table_id': f"table_{table_idx}",
                    'content': '\n'.join(current_table),
                    'row_count': len(current_table) - 1,  # Minus header
                    'context_before': context_before.strip(),
                    'context_after': context_after.strip(),
                })
                current_table = []
                in_table = False
    
    # Handle last table if document ends with one
    if in_table and current_table:
        table_end_idx = len(lines)
        context_before_start = max(0, table_start_idx - context_lines)
        context_before = '\n'.join(lines[context_before_start:table_start_idx])
        
        tables.append({
            'table_id': f"table_{table_idx}",
            'content': '\n'.join(current_table),
            'row_count': len(current_table) - 1,
            'context_before': context_before.strip(),
            'context_after': '',
        })
    
    return tables
