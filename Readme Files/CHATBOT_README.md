# 🤖 Multimodal Agentic RAG Chatbot

An intelligent chatbot powered by a multi-agent RAG (Retrieval-Augmented Generation) system that combines document retrieval, SQL querying, and LLM-based reasoning to provide accurate, confident answers.

## 🌟 Features

### Core Capabilities

- **Multi-Modal Retrieval**: Search across text, images, and tables from PDF documents
- **Intelligent Reranking**: Advanced scoring combining vector similarity, LLM relevance, and diversity
- **Parallel Processing**: Simultaneous RAG and SQL execution for optimal performance
- **Answer Verification**: Automatic comparison between document-based and database answers
- **Confidence Scoring**: Transparent confidence metrics for every response
- **Document Management**: Upload, process, and delete documents through the UI

### Agent Architecture

1. **🔍 Retrieval Agent (Agent 3)**: Hybrid search across text, images, and tables
2. **⚖️ Reranking Agent (Agent 4)**: Multi-signal relevance scoring
3. **💾 Text-to-SQL Agent (Agent 5)**: Natural language to SQL conversion
4. **📊 Orchestrator**: Coordinates all agents and compares answers

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL with pgvector extension
- AWS Account with Bedrock access
- AWS credentials configured

### Installation

1. **Clone the repository**
   ```bash
   cd "Agentic-RAG-Handling-Tables-and-Images"
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```env
   # AWS Configuration
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   
   # Database Configuration
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=multimodal_rag
   DB_USER=your_username
   DB_PASSWORD=your_password
   ```

4. **Initialize the database**
   ```bash
   python reset_tables.py
   ```

5. **Process initial documents** (if you have PDFs in the `data/` folder)
   ```bash
   python main.py
   ```

### Running the Chatbot

```bash
streamlit run streamlit_app.py
```

The chatbot will open in your browser at `http://localhost:8501`

## 💬 Using the Chatbot

### First Time Setup

1. Click **"🚀 Initialize AI Agents"** in the sidebar
2. Wait for agents to initialize (~10-15 seconds)

### Asking Questions

**Simple Questions** (RAG-only):
```
Explain the role of business readiness
```
→ Uses document retrieval + LLM response

**Data Questions** (RAG + SQL):
```
What is the pillar score for Indonesia?
```
→ Uses document retrieval + SQL query + answer comparison

**Complex Questions** (Hybrid):
```
Explain business readiness. Also, what are the top 5 countries by pillar I score?
```
→ RAG for explanation + SQL for data + combined answer

### Understanding Responses

Each response includes:

- **📝 Answer**: Combined final answer with confidence score
- **📊 Metrics**: Retrieved chunks, reranked chunks, SQL execution, duration
- **🔍 Processing Details**: Full agent execution timeline (expandable)
- **📚 Source Chunks**: Retrieved document chunks with scores (expandable)
- **💾 SQL Details**: Generated queries and results (if applicable, expandable)

### Confidence Levels

- **🟢 High (85-100%)**: Answers agree fully, high reliability
- **🟡 Medium (70-85%)**: Partial agreement, good reliability
- **🔴 Low (<70%)**: Conflicting answers, manual verification recommended

## 📁 Document Management

### Adding Documents

1. Click **"Choose a PDF file"** in the sidebar
2. Select your PDF document
3. Click **"📤 Process Document"**
4. Wait for parsing and embedding (~30-60 seconds per document)

The system will:
- Extract text, images, and tables from the PDF
- Generate AI summaries for images
- Create SQL schemas for tables
- Generate embeddings for all content
- Store everything in the database

### Deleting Documents

1. Find the document in the **"Current Documents"** list
2. Click the **🗑️** button next to it
3. Document is removed (you'll need to manually clean database for full removal)

## 🏗️ Architecture

### Data Flow

```
User Query
    ↓
    ├─→ [Retrieval Agent] → [Reranking Agent] → [LLM] → RAG Answer
    │
    └─→ [Text-to-SQL Agent] → [SQL Execution] → SQL Answer
                ↓
        [Answer Comparison] → Confidence Score
                ↓
           Final Answer
```

### Parallel Processing

RAG and SQL paths execute **simultaneously** using Python's ThreadPoolExecutor, reducing latency by ~40%.

### Database Schema

**Tables**:
- `text_chunks`: Text passages with embeddings
- `image_chunks`: Image summaries with embeddings
- `table_chunks`: SQL table definitions
- Dynamic tables: Extracted tables from PDFs (e.g., `governance_pillars_table_5`)

## 🔧 Configuration

### Adjusting Retrieval

In `streamlit_app.py`, modify:

```python
ChatbotOrchestrator(
    retrieval_top_k=10,  # Chunks retrieved per type
    rerank_top_k=5       # Top chunks after reranking
)
```

### Changing LLM Models

In `utils/aws_utils.py`:

```python
# For general responses
model_id = "us.amazon.nova-pro-v1:0"

# For embeddings
embedding_model = "amazon.titan-embed-text-v2:0"
```

### Adjusting Confidence Thresholds

In `streamlit_app.py`, modify `get_confidence_class()`:

```python
def get_confidence_class(confidence: float) -> str:
    if confidence >= 0.85:  # Adjust high threshold
        return "confidence-high"
    elif confidence >= 0.70:  # Adjust medium threshold
        return "confidence-medium"
    else:
        return "confidence-low"
```

## 🐛 Troubleshooting

### "No agents initialized" Error

**Solution**: Click "🚀 Initialize AI Agents" in the sidebar before asking questions.

### Slow Response Times

**Possible causes**:
1. Large number of chunks in database
2. Slow AWS Bedrock API
3. Database not indexed

**Solutions**:
- Reduce `retrieval_top_k` and `rerank_top_k`
- Create indexes on embedding columns (see `RETRIEVAL_AGENT_GUIDE.md`)
- Use faster AWS region

### SQL Queries Not Executing

**Possible causes**:
1. No tables in database
2. Query classification skipping SQL
3. SQL generation errors

**Solutions**:
- Check if PDFs with tables have been processed
- Review process log (expandable in UI) for errors
- Manually test with `python agents/text_to_sql_agent.py`

### Upload Fails

**Possible causes**:
1. File too large
2. Invalid PDF format
3. Database connection issues

**Solutions**:
- Check file size (<50MB recommended)
- Verify PDF is not corrupted
- Check database connection in `.env`

## 📊 Performance Metrics

Typical performance on a standard machine:

- **Query Processing**: 2-5 seconds
- **Document Upload**: 30-60 seconds (depends on document size)
- **Retrieval**: <1 second
- **Reranking**: 1-2 seconds (with LLM scoring)
- **SQL Execution**: <500ms

## 🔒 Security Considerations

- **AWS Credentials**: Never commit `.env` file to version control
- **SQL Injection**: Parameterized queries used throughout
- **File Uploads**: Only PDF files accepted, validated before processing
- **Database Access**: Use read-only user for production deployments

## 📚 Related Documentation

- [RETRIEVAL_AGENT_GUIDE.md](RETRIEVAL_AGENT_GUIDE.md) - Deep dive into retrieval
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Complete system overview
- [QUICKSTART.md](QUICKSTART.md) - Setup guide

## 🛠️ Development

### Running Tests

```bash
# Test individual agents
python agents/text_to_sql_agent.py
python agents/retrieval_agent.py
python agents/reranking_agent.py

# Test orchestrator
python chatbot_orchestrator.py

# Test full pipeline
python main.py
```

### Adding New Agents

1. Create agent file in `agents/` directory
2. Follow LangGraph StateGraph pattern
3. Add to orchestrator in `chatbot_orchestrator.py`
4. Update UI in `streamlit_app.py` if needed

## 🎯 Roadmap

- [ ] Support for more document formats (Word, Excel, HTML)
- [ ] Multi-language support
- [ ] Voice input/output
- [ ] Export conversation history
- [ ] User authentication and sessions
- [ ] Advanced analytics dashboard
- [ ] Custom agent configuration in UI

## 📝 License

See LICENSE file for details.

## 👥 Contributors

Built with ❤️ using LangGraph, AWS Bedrock, and PostgreSQL.

---

**Need Help?** Check the troubleshooting section or review the process logs in the UI for detailed error information.
