# Agentic RAG: Handling Tables and Images

A Multimodal Agentic RAG Application using LangGraph, Amazon Bedrock (Nova & Titan), PostgreSQL with pgvector, and FastMCP.

## 🏗️ Architecture

This project implements a sophisticated Multimodal Agentic RAG pipeline with the following components:

### Agents
1. **Agent 1 - Document Parse Agent** (`agents/document_parse_agent.py`)
   - Lists and ingests PDF documents using PyMuPDF4LLM
   - Applies Two-Pass Hybrid Chunking strategy
   - Extracts and processes images (general and visualizations)
   - Extracts and processes tables
   - Stores chunks in PostgreSQL

2. **Agent 2 - Document Embedder Agent** (`agents/document_embedder.py`)
   - Generates embeddings using Amazon Titan
   - Updates PostgreSQL with embeddings
   - Saves chunks to JSONL files

### Key Features

#### Two-Pass Hybrid Chunking
1. **First Pass**: Header-based splitting to preserve document hierarchy
2. **Second Pass**: Recursive character splitting to enforce token limits (700-900 tokens, 10% overlap)

#### Multimodal Processing
- **Text Chunks**: Stored in vector database (pgvector)
- **Tables**: Analyzed by Amazon Nova → SQL generation → Stored in relational database via MCP
- **General Images**: Base64 encoding → Summary by Nova → Stored in vector database
- **Visualization Images**: Data extraction by Nova → SQL generation → Stored in relational database via MCP

#### MCP Server
FastMCP-based server for executing SQL queries in PostgreSQL

## 📋 Prerequisites

- Python 3.9+
- PostgreSQL with pgvector extension
- AWS Account with Bedrock access (Nova and Titan models)

## 🚀 Setup

### 1. Create Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```env
# AWS Credentials
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=multimodal_rag
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
```

### 4. Setup PostgreSQL

Ensure PostgreSQL is installed and the pgvector extension is available:

```sql
CREATE DATABASE multimodal_rag;
\c multimodal_rag
CREATE EXTENSION vector;
```

## 📁 Project Structure

```
Agentic-RAG-Handling-Tables-and-Images/
├── agents/
│   ├── document_parse_agent.py      # Agent 1: Document parsing and chunking
│   └── document_embedder.py         # Agent 2: Embedding generation
├── chunks/                           # Output JSONL files with embeddings
├── data/                             # Input PDF documents
├── mcp_server/
│   └── sql_executor_mcp.py          # FastMCP server for SQL execution
├── utils/
│   ├── __init__.py
│   ├── aws_utils.py                 # AWS Bedrock client (Nova & Titan)
│   ├── chunking_utils.py            # Two-pass hybrid chunker
│   └── db_utils.py                  # PostgreSQL utilities
├── .env                              # Environment variables (create this)
├── requirements.txt                  # Python dependencies
└── README.md
```

## 🎯 Usage

### Run Agent 1: Document Parsing

```powershell
python agents/document_parse_agent.py
```

This will:
1. List all PDF files in the `data/` folder
2. Parse documents using PyMuPDF4LLM
3. Extract images and tables
4. Apply two-pass hybrid chunking
5. Store chunks in PostgreSQL

### Run Agent 2: Document Embedding

```powershell
python agents/document_embedder.py
```

This will:
1. Fetch chunks from PostgreSQL
2. Generate embeddings using Amazon Titan
3. Update database with embeddings
4. Save chunks with embeddings to JSONL files in `chunks/` folder

### Run Both Agents Sequentially

```powershell
# First, run Agent 1
python agents/document_parse_agent.py

# Then, run Agent 2
python agents/document_embedder.py
```

## 🗄️ Database Schema

### text_chunks
- `chunk_id` (VARCHAR): Unique identifier
- `chunk_type` (VARCHAR): 'text'
- `section_id` (VARCHAR): Section identifier from headers
- `source_document` (VARCHAR): Source filename
- `content` (TEXT): Chunk text content
- `embedding` (VECTOR(1536)): Titan embedding
- `metadata` (JSONB): Additional metadata

### image_chunks
- `chunk_id` (VARCHAR): Unique identifier
- `chunk_type` (VARCHAR): 'image'
- `section_id` (VARCHAR): Page identifier
- `source_document` (VARCHAR): Source filename
- `image_type` (VARCHAR): 'general' or 'visualization'
- `image_base64` (TEXT): Base64 encoded image (for general images)
- `image_summary` (TEXT): Nova-generated summary
- `embedding` (VECTOR(1536)): Titan embedding
- `metadata` (JSONB): Additional metadata

### table_chunks
- `chunk_id` (VARCHAR): Unique identifier
- `chunk_type` (VARCHAR): 'table'
- `section_id` (VARCHAR): Table identifier
- `source_document` (VARCHAR): Source filename
- `table_name` (VARCHAR): Generated table name
- `sql_query` (TEXT): CREATE TABLE SQL statement
- `metadata` (JSONB): Additional metadata

## 🔮 Upcoming Agents

The following agents will be added in future iterations:

- **Agent 3**: Retrieval Agent - Semantic search and retrieval
- **Agent 4**: Reranker Agent - Result reranking for relevance
- **Agent 5**: Text-to-SQL Agent - Natural language to SQL queries
- **Streamlit UI**: Interactive web interface

## 📊 Chunk Metadata

Each chunk includes metadata:
- `chunk_id`: Unique identifier
- `chunk_type`: text, image, or table
- `section_id`: Section/page identifier
- `source_document`: Original document name
- Additional type-specific metadata

## 🛠️ Key Technologies

- **LangGraph**: Agentic workflow orchestration
- **PyMuPDF4LLM**: Document parsing and markdown extraction
- **Amazon Bedrock Nova**: Multimodal analysis (images, tables)
- **Amazon Titan**: Text and multimodal embeddings
- **PostgreSQL + pgvector**: Vector and relational storage
- **FastMCP**: Model Context Protocol server
- **LangChain**: Text splitting and processing

## 🔍 Print Statements

The application includes comprehensive logging at each step:
- 🤖 Agent initialization
- 📂 Document listing
- 📄 Document parsing
- 🖼️ Image extraction and analysis
- 📋 Table extraction and SQL generation
- 🔪 Chunking progress
- 💾 Database operations
- 🔤 Embedding generation
- ✅ Success confirmations
- ❌ Error messages

## 📝 Notes

- Place your PDF documents in the `data/` folder before running Agent 1
- Ensure AWS credentials have access to Bedrock models (Nova and Titan)
- PostgreSQL must have the pgvector extension installed
- The chunker targets 700-900 tokens per chunk with 10% overlap
- JSONL files are saved in the `chunks/` folder with naming: `<document_name>_chunks.jsonl`

## 🤝 Contributing

This is a TCS exploration project for Multimodal Agentic RAG systems.

## 📄 License

Internal TCS Project
