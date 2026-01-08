"""
Webhook Server for Asynchronous Document Processing
Handles document uploads, processes them in background, and provides status updates
"""
from fastapi import FastAPI, BackgroundTasks, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import aiofiles
from datetime import datetime
import asyncio
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from agents.document_parse_agent import DocumentParseAgent
from agents.document_embedder import DocumentEmbedderAgent

app = FastAPI(
    title="Document Processing Webhook Server",
    description="Asynchronous document processing with real-time status updates",
    version="1.0.0"
)

# Enable CORS for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Job storage (use Redis/PostgreSQL in production)
jobs: Dict[str, Dict[str, Any]] = {}


class JobStatus(BaseModel):
    """Job status model"""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    message: str
    file_name: str
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@app.post("/api/v1/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload and process document asynchronously
    
    Args:
        file: PDF file to process
        
    Returns:
        job_id for tracking
    """
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save file to disk
    data_folder = Path("data")
    data_folder.mkdir(exist_ok=True)
    file_path = data_folder / file.filename
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Initialize job status
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "message": "Document upload received",
        "file_name": file.filename,
        "file_path": str(file_path),
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "result": None,
        "error": None
    }
    
    print(f"📥 Document uploaded: {file.filename}")
    print(f"📋 Job ID: {job_id}")
    
    # Start background processing
    background_tasks.add_task(
        process_document_async, 
        job_id, 
        str(file_path), 
        file.filename
    )
    
    return {
        "success": True,
        "job_id": job_id,
        "status": "queued",
        "message": "Document processing started",
        "polling_url": f"/api/v1/documents/jobs/{job_id}",
        "estimated_time": "2-3 minutes"
    }


@app.get("/api/v1/documents/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Check processing status
    
    Returns:
        Current job status and progress
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]


@app.get("/api/v1/documents/jobs")
async def list_jobs(status: Optional[str] = None, limit: int = 50):
    """
    List all jobs with optional filtering
    
    Args:
        status: Filter by status (pending, processing, completed, failed)
        limit: Maximum number of jobs to return
        
    Returns:
        List of jobs
    """
    job_list = list(jobs.values())
    
    # Filter by status if provided
    if status:
        job_list = [j for j in job_list if j["status"] == status]
    
    # Sort by creation time (newest first)
    job_list.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "total": len(job_list),
        "jobs": job_list[:limit]
    }


@app.delete("/api/v1/documents/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job from tracking"""
    if job_id in jobs:
        del jobs[job_id]
        return {"success": True, "message": "Job deleted"}
    else:
        raise HTTPException(status_code=404, detail="Job not found")


async def process_document_async(job_id: str, file_path: str, file_name: str):
    """
    Background task for document processing
    
    This runs asynchronously and updates job status as it progresses
    """
    
    try:
        # Update status: Parsing
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 10
        jobs[job_id]["message"] = "📄 Parsing document with Agent 1..."
        print(f"📄 [{job_id}] Starting document parsing...")
        
        # Agent 1: Document Parse
        parse_agent = DocumentParseAgent(data_folder="data")
        parse_result = parse_agent.run()
        parse_agent.db_manager.close()
        
        jobs[job_id]["progress"] = 40
        jobs[job_id]["message"] = "✅ Document parsed successfully"
        print(f"✅ [{job_id}] Parsing complete: {parse_result.get('total_chunks', 0)} chunks")
        
        # Small delay to simulate realistic processing
        await asyncio.sleep(2)
        
        # Update status: Embedding
        jobs[job_id]["progress"] = 50
        jobs[job_id]["message"] = "🔢 Generating embeddings with Agent 2..."
        print(f"🔢 [{job_id}] Starting embedding generation...")
        
        # Agent 2: Document Embedder
        embed_agent = DocumentEmbedderAgent()
        embed_result = embed_agent.run_all_documents()
        embed_agent.db_manager.close()
        
        jobs[job_id]["progress"] = 90
        jobs[job_id]["message"] = "✅ Embeddings generated successfully"
        print(f"✅ [{job_id}] Embedding complete: {len(embed_result)} documents")
        
        # Finalize
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = "🎉 Document processing completed successfully"
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
        jobs[job_id]["result"] = {
            "file_name": file_name,
            "text_chunks": parse_result.get('text_chunks', 0),
            "image_chunks": parse_result.get('image_chunks', 0),
            "table_chunks": parse_result.get('table_chunks', 0),
            "total_chunks": parse_result.get('total_chunks', 0),
            "documents_embedded": len(embed_result),
            "processing_time_seconds": (
                datetime.fromisoformat(jobs[job_id]["completed_at"]) - 
                datetime.fromisoformat(jobs[job_id]["created_at"])
            ).total_seconds()
        }
        
        print(f"🎉 [{job_id}] Processing completed successfully!")
        
    except Exception as e:
        # Handle failure
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["progress"] = 0
        jobs[job_id]["message"] = "❌ Processing failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
        
        print(f"❌ [{job_id}] Processing failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Document Processing Webhook Server",
        "active_jobs": len([j for j in jobs.values() if j["status"] == "processing"]),
        "total_jobs": len(jobs)
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 80)
    print("🚀 Starting Webhook Server")
    print("=" * 80)
    print("\n📡 Server will be available at: http://localhost:8080")
    print("📖 API docs at: http://localhost:8080/docs")
    print("\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
