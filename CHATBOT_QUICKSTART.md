# 🚀 Quick Start Guide - Chatbot

Get your Multimodal Agentic RAG Chatbot running in 5 minutes!

---

## ⚡ Super Quick Start

```bash
# 1. Navigate to project folder
cd "Agentic-RAG-Handling-Tables-and-Images"

# 2. Run the chatbot
python run_chatbot.py
```

That's it! The browser will open automatically at `http://localhost:8501`

---

## 📋 Prerequisites Checklist

Before running the chatbot, ensure you have:

- ✅ Python 3.10 or higher
- ✅ PostgreSQL with pgvector extension installed
- ✅ AWS credentials configured (for Bedrock)
- ✅ Dependencies installed (`pip install -r requirements.txt`)
- ✅ Database initialized (`python reset_tables.py`)
- ✅ At least one document processed (`python main.py`)

---

## 🎬 First-Time Setup

### Step 1: Environment Configuration

Create `.env` file:

```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here

DB_HOST=localhost
DB_PORT=5432
DB_NAME=multimodal_rag
DB_USER=postgres
DB_PASSWORD=your_password
```

### Step 2: Database Initialization

```bash
python reset_tables.py
```

Expected output:
```
✅ Created table: text_chunks
✅ Created table: image_chunks
✅ Created table: table_chunks
```

### Step 3: Process Initial Documents

Place PDF files in `data/` folder, then:

```bash
python main.py
```

This processes all PDFs and creates embeddings.

### Step 4: Launch Chatbot

```bash
python run_chatbot.py
```

Or directly:

```bash
streamlit run streamlit_app.py
```

---

## 💬 Using the Chatbot

### Initial Setup in UI

1. Open browser to `http://localhost:8501`
2. Click **"🚀 Initialize AI Agents"** in sidebar
3. Wait 10-15 seconds for initialization
4. Start chatting!

### Example Queries

**Simple Questions** (RAG-only):
```
What is business readiness?
Explain governance factors
Describe the regulatory environment
```

**Data Questions** (RAG + SQL):
```
What is the pillar score for Indonesia?
Show me Turkey's governance scores
Which country has the highest pillar I score?
```

**Complex Questions** (Hybrid):
```
Explain business readiness. Also, what are the top 5 countries by pillar I score?
What is governance? Compare scores between Indonesia and Mali.
```

---

## 📁 Managing Documents

### Upload New Document

1. Click **"Choose a PDF file"** in sidebar
2. Select your PDF
3. Click **"📤 Process Document"**
4. Wait for processing (~30-60 seconds)
5. Document is now searchable!

### Delete Document

1. Find document in **"Current Documents"** list
2. Click **🗑️** button next to it
3. Confirm deletion

---

## 🎯 Understanding Responses

Each response shows:

### Confidence Indicators

- 🟢 **High (85-100%)**: Answers fully agree, very reliable
- 🟡 **Medium (70-85%)**: Partial agreement, good reliability  
- 🔴 **Low (<70%)**: Conflicting answers, verify manually

### Metrics Display

- **Retrieved**: Total chunks found by retrieval
- **Reranked**: Top chunks after reranking
- **SQL Executed**: Yes/No - was database queried?
- **Duration**: Total processing time

### Expandable Sections

Click to expand:

- **🔍 View Processing Details**: See every agent step
- **📚 View Source Chunks**: See retrieved documents
- **💾 View SQL Details**: See generated queries & results

---

## 🔧 Troubleshooting

### Problem: "Please initialize agents first"

**Solution**: Click "🚀 Initialize AI Agents" in sidebar

### Problem: Slow responses (>10 seconds)

**Causes**:
- Too many documents in database
- Slow internet connection to AWS
- Database needs indexing

**Solutions**:
```bash
# Check document count
python -c "from utils import DatabaseManager; db = DatabaseManager(); db.connect(); db.cursor.execute('SELECT COUNT(*) FROM text_chunks'); print(db.cursor.fetchone())"

# If >10,000 chunks, create indexes:
# See RETRIEVAL_AGENT_GUIDE.md for indexing instructions
```

### Problem: No SQL results

**Causes**:
- Query doesn't require SQL (by design)
- No tables in database
- SQL generation failed

**Solutions**:
- Check "View Processing Details" for SQL classification reasoning
- Verify tables exist: `SELECT * FROM table_chunks LIMIT 5;`
- Try more specific question: "What is Indonesia's exact pillar score?"

### Problem: Document upload fails

**Causes**:
- File too large (>100MB)
- Not a valid PDF
- Database connection error

**Solutions**:
- Check file size
- Verify PDF isn't corrupted
- Check `.env` database credentials

---

## 🎨 UI Tips & Tricks

### Keyboard Shortcuts

- **Enter** in text box: Send message
- **Ctrl+C** in terminal: Stop server

### Best Practices

1. **Specific Questions**: More specific = better answers
   - ❌ "Tell me about scores"
   - ✅ "What is Indonesia's pillar II score?"

2. **Use Expandable Sections**: Understand how the answer was generated

3. **Check Confidence**: Low confidence? Try rephrasing

4. **Upload Quality Docs**: Better documents = better answers

---

## 📊 Example Session

### Session Flow

```
1. Initialize agents (sidebar button)
   ↓
2. Ask: "What is the pillar score for Indonesia?"
   ↓
3. Wait 3-5 seconds
   ↓
4. See answer with confidence: 92%
   ↓
5. Expand "View Processing Details" to see:
   - Retrieved 25 chunks
   - Reranked to 5 chunks
   - SQL executed: 1 query
   - Agreement: FULL
   ↓
6. Expand "View SQL Details" to see:
   - Generated SQL query
   - Table results
   ↓
7. Continue conversation!
```

---

## 🚀 Performance Tips

### For Faster Responses

1. **Reduce Retrieval**:
   - Edit `streamlit_app.py`
   - Change `retrieval_top_k=10` to `retrieval_top_k=5`

2. **Reduce Reranking**:
   - Change `rerank_top_k=5` to `rerank_top_k=3`

3. **Use Faster Region**:
   - Edit `.env`
   - Try `AWS_REGION=us-east-1` (usually fastest)

### For Better Quality

1. **Increase Context**:
   - Change `rerank_top_k=5` to `rerank_top_k=7`

2. **Better Documents**:
   - Upload high-quality PDFs
   - Include tables and images
   - Add descriptive content

---

## 📞 Getting Help

### Debug Information

Always check:

1. **Process Log** (in UI): Shows exactly what happened
2. **Terminal Output**: Shows any error messages
3. **Error Section** (in UI): Lists all errors encountered

### Common Error Messages

**"No query embedding available"**
- AWS Bedrock connection issue
- Check `.env` credentials

**"No tables available in database"**
- No documents with tables processed yet
- Upload a PDF with tables

**"Error generating SQL"**
- LLM couldn't understand query
- Try rephrasing more specifically

---

## 🎓 Learning Resources

- **Architecture**: [CHATBOT_ARCHITECTURE.md](CHATBOT_ARCHITECTURE.md)
- **Detailed Usage**: [CHATBOT_README.md](CHATBOT_README.md)
- **Retrieval Details**: [RETRIEVAL_AGENT_GUIDE.md](RETRIEVAL_AGENT_GUIDE.md)
- **Project Overview**: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)

---

## ✅ Checklist: Is Everything Working?

Run this quick test:

```bash
# 1. Database connected?
python -c "from utils import DatabaseManager; db = DatabaseManager(); print('✅ DB OK' if db.connect() else '❌ DB FAILED')"

# 2. AWS Bedrock accessible?
python -c "from utils import AWSBedrockClient; client = AWSBedrockClient(); print('✅ AWS OK' if client.get_titan_embeddings('test')['success'] else '❌ AWS FAILED')"

# 3. Documents processed?
python -c "from utils import DatabaseManager; db = DatabaseManager(); db.connect(); db.cursor.execute('SELECT COUNT(*) FROM text_chunks'); print(f'✅ {db.cursor.fetchone()[0]} chunks in DB')"
```

All ✅? You're ready to go!

---

**Happy chatting! 🎉**

For issues, check the expandable sections in the UI or review the terminal output.
