# Quick Start Guide

## 🚀 Getting Started in 5 Steps

### Step 1: Activate Virtual Environment

```powershell
# The venv is already created, just activate it
.\venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 3: Configure Environment

1. Copy `.env.example` to `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```

2. Edit `.env` and add your credentials:
   - AWS credentials (for Bedrock access)
   - PostgreSQL connection details

### Step 4: Setup PostgreSQL

Make sure PostgreSQL is running and create the database:

```sql
CREATE DATABASE multimodal_rag;
\c multimodal_rag
CREATE EXTENSION vector;
```

### Step 5: Run Setup Check

```powershell
python setup_check.py
```

This will verify your environment is correctly configured.

---

## 📖 Running the Pipeline

### Option 1: Run Complete Pipeline

```powershell
python main.py
```

This runs both Agent 1 and Agent 2 sequentially.

### Option 2: Run Agents Individually

**Agent 1 - Document Parsing:**
```powershell
python agents/document_parse_agent.py
```

**Agent 2 - Document Embedding:**
```powershell
python agents/document_embedder.py
```

---

## 📁 Directory Structure

Before running, ensure:
- ✅ PDF files are in `data/` folder
- ✅ `.env` file is configured
- ✅ PostgreSQL is running

After running:
- 📦 Chunks stored in PostgreSQL
- 📄 JSONL files in `chunks/` folder

---

## 🔍 Verify Installation

```powershell
python -c "import langgraph, pymupdf4llm, boto3, psycopg2; print('✅ All key packages installed')"
```

---

## 🐛 Troubleshooting

### Issue: Module not found
**Solution:** Make sure venv is activated and run `pip install -r requirements.txt`

### Issue: PostgreSQL connection failed
**Solution:** 
- Verify PostgreSQL is running
- Check credentials in `.env`
- Ensure database exists and pgvector extension is installed

### Issue: AWS Bedrock access denied
**Solution:**
- Verify AWS credentials in `.env`
- Ensure your AWS account has Bedrock access
- Check that Nova and Titan models are enabled in your region

### Issue: No PDF files found
**Solution:** Place PDF documents in the `data/` folder

---

## 📊 What Each Agent Does

### Agent 1: Document Parse Agent
- Lists PDF documents
- Extracts text, images, and tables
- Applies two-pass hybrid chunking
- Analyzes images and tables with Amazon Nova
- Stores chunks in PostgreSQL

### Agent 2: Document Embedder Agent
- Fetches chunks from database
- Generates embeddings with Amazon Titan
- Updates database with embeddings
- Saves chunks to JSONL files

---

## 🎯 Expected Output

After successful execution:

```
✅ Documents processed: X
✅ Text chunks created: XXX
✅ Image chunks created: XX
✅ Table chunks created: XX
✅ Embeddings generated
✅ JSONL files saved to chunks/
```

---

## 📚 Next Steps

After completing Agent 1 and Agent 2:
- Agent 3: Retrieval Agent (coming soon)
- Agent 4: Reranker Agent (coming soon)
- Agent 5: Text-to-SQL Agent (coming soon)
- Streamlit UI (coming soon)

---

## 💡 Tips

1. Start with a small PDF document to test the pipeline
2. Check the console output for detailed progress logs
3. Use `setup_check.py` to verify configuration before running
4. Monitor PostgreSQL for chunk storage
5. Check `chunks/` folder for output JSONL files

---

## 📞 Support

For issues or questions about this TCS Exploration project, refer to the main README.md or contact the project team.
