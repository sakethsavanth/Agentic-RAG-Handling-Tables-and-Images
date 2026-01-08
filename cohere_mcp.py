"""
Cohere MCP Server for Reranking
Provides Cohere reranking capabilities via MCP/HTTP endpoints
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import logging
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CohereReranking")

app = FastAPI(
    title="Cohere Reranking MCP Server",
    description="MCP server for Cohere-based document reranking",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cohere client (lazy initialization)
cohere_client = None

# Store reranking history for monitoring
reranking_history = []


def get_cohere_client():
    """Initialize Cohere client with API key"""
    global cohere_client
    
    if cohere_client is None:
        try:
            import cohere
            
            # Get API key from environment or use trial key
            api_key = os.getenv("COHERE_API_KEY")
            
            if not api_key:
                # Provide instructions for getting a free trial key
                raise ValueError(
                    "COHERE_API_KEY not found in environment variables. "
                    "Get a free trial key at: https://dashboard.cohere.com/api-keys"
                )
            
            cohere_client = cohere.Client(api_key)
            print("✅ Cohere client initialized successfully")
            
        except ImportError:
            raise ImportError("Cohere package not installed. Run: pip install cohere")
        except Exception as e:
            raise Exception(f"Failed to initialize Cohere client: {str(e)}")
    
    return cohere_client


class Document(BaseModel):
    """Document model for reranking"""
    text: str
    chunk_id: Optional[str] = None
    chunk_type: Optional[str] = None
    source_document: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class RerankRequest(BaseModel):
    """Reranking request model"""
    query: str
    documents: List[Document]
    top_k: int = 5
    model: str = "rerank-english-v3.0"


class RerankResponse(BaseModel):
    """Reranking response model"""
    success: bool
    reranked_documents: List[Dict[str, Any]]
    count: int
    model_used: str
    error: Optional[str] = None


@app.post("/api/v1/rerank", response_model=RerankResponse)
async def rerank_documents(request: RerankRequest):
    """
    Rerank documents using Cohere's reranking API with detailed logging
    """
    start_time = time.time()
    request_id = f"rerank_{int(start_time * 1000)}"
    
    logger.info("=" * 80)
    logger.info(f"🔄 NEW RERANKING REQUEST [{request_id}]")
    logger.info("=" * 80)
    logger.info(f"📝 Query: {request.query}")
    logger.info(f"📚 Documents received: {len(request.documents)}")
    logger.info(f"🎯 Top K requested: {request.top_k}")
    logger.info(f"🤖 Model: {request.model}")
    
    try:
        # Get Cohere client
        logger.info("🔌 Connecting to Cohere API...")
        client = get_cohere_client()
        logger.info("✅ Cohere client ready")
        
        # Log input documents (first 3)
        logger.info("\n📥 INPUT DOCUMENTS:")
        for i, doc in enumerate(request.documents[:3], 1):
            preview = doc.text[:100] + "..." if len(doc.text) > 100 else doc.text
            logger.info(f"   Doc {i}: {preview}")
            logger.info(f"          Source: {doc.source_document}")
            logger.info(f"          Chunk ID: {doc.chunk_id}")
        
        if len(request.documents) > 3:
            logger.info(f"   ... and {len(request.documents) - 3} more documents")
        
        # Prepare documents for Cohere
        texts = [doc.text for doc in request.documents]
        
        # Call Cohere rerank API
        logger.info(f"\n⚡ Calling Cohere Rerank API...")
        api_start = time.time()
        
        response = client.rerank(
            query=request.query,
            documents=texts,
            top_n=request.top_k,
            model=request.model
        )
        
        api_duration = time.time() - api_start
        logger.info(f"✅ Cohere API responded in {api_duration:.2f}s")
        
        # Process results
        logger.info(f"\n📤 RERANKED RESULTS (Top {len(response.results)}):")
        reranked = []
        
        for rank, result in enumerate(response.results, 1):
            original_doc = request.documents[result.index]
            
            preview = original_doc.text[:80] + "..." if len(original_doc.text) > 80 else original_doc.text
            logger.info(f"\n   Rank {rank}:")
            logger.info(f"   ├─ Score: {result.relevance_score:.4f}")
            logger.info(f"   ├─ Original Index: {result.index}")
            logger.info(f"   ├─ Chunk ID: {original_doc.chunk_id}")
            logger.info(f"   ├─ Source: {original_doc.source_document}")
            logger.info(f"   └─ Preview: {preview}")
            
            reranked.append({
                "chunk_id": original_doc.chunk_id,
                "chunk_type": original_doc.chunk_type,
                "content": original_doc.text,
                "source_document": original_doc.source_document,
                "cohere_score": result.relevance_score,
                "original_index": result.index,
                "metadata": original_doc.metadata or {}
            })
        
        total_duration = time.time() - start_time
        
        # Store in history
        history_entry = {
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "query": request.query,
            "input_count": len(request.documents),
            "output_count": len(reranked),
            "model": request.model,
            "duration_seconds": total_duration,
            "api_duration_seconds": api_duration,
            "top_score": reranked[0]["cohere_score"] if reranked else 0,
            "avg_score": sum(r["cohere_score"] for r in reranked) / len(reranked) if reranked else 0
        }
        reranking_history.append(history_entry)
        
        # Keep only last 100 entries
        if len(reranking_history) > 100:
            reranking_history.pop(0)
        
        logger.info(f"\n⏱️  Total processing time: {total_duration:.2f}s")
        logger.info(f"📊 Average score: {history_entry['avg_score']:.4f}")
        logger.info("=" * 80 + "\n")
        
        return RerankResponse(
            success=True,
            reranked_documents=reranked,
            count=len(reranked),
            model_used=request.model
        )
        
    except ValueError as e:
        logger.error(f"❌ Configuration error: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))
    except ImportError as e:
        logger.error(f"❌ Import error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Reranking failed: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=f"Reranking failed: {str(e)}")
    except Exception as e:
        # Other errors
        raise HTTPException(
            status_code=500,
            detail=f"Reranking failed: {str(e)}"
        )


@app.get("/api/v1/models")
async def list_models():
    """List available Cohere reranking models"""
    return {
        "models": [
            {
                "name": "rerank-english-v3.0",
                "description": "Latest English reranking model with best performance",
                "recommended": True
            },
            {
                "name": "rerank-english-v2.0",
                "description": "Previous generation English reranking model",
                "recommended": False
            },
            {
                "name": "rerank-multilingual-v2.0",
                "description": "Multilingual reranking model supporting 100+ languages",
                "recommended": False
            }
        ]
    }


@app.get("/api/v1/history")
async def get_reranking_history(limit: int = 10):
    """
    Get recent reranking history
    
    Args:
        limit: Number of recent entries to return
    
    Returns:
        List of recent reranking operations
    """
    return {
        "history": reranking_history[-limit:],
        "total_requests": len(reranking_history)
    }


@app.get("/api/v1/stats")
async def get_statistics():
    """Get reranking statistics"""
    if not reranking_history:
        return {
            "total_requests": 0,
            "message": "No reranking requests yet"
        }
    
    total_requests = len(reranking_history)
    avg_duration = sum(h["duration_seconds"] for h in reranking_history) / total_requests
    avg_api_duration = sum(h["api_duration_seconds"] for h in reranking_history) / total_requests
    avg_input_count = sum(h["input_count"] for h in reranking_history) / total_requests
    avg_output_count = sum(h["output_count"] for h in reranking_history) / total_requests
    avg_score = sum(h["avg_score"] for h in reranking_history) / total_requests
    
    return {
        "total_requests": total_requests,
        "avg_duration_seconds": round(avg_duration, 2),
        "avg_api_duration_seconds": round(avg_api_duration, 2),
        "avg_input_documents": round(avg_input_count, 1),
        "avg_output_documents": round(avg_output_count, 1),
        "avg_relevance_score": round(avg_score, 4),
        "most_recent": reranking_history[-1] if reranking_history else None
    }


@app.get("/api/v1/status")
async def check_status():
    """Check if Cohere API is configured and accessible"""
    try:
        client = get_cohere_client()
        
        # Test with a simple rerank call
        test_response = client.rerank(
            query="test",
            documents=["This is a test document."],
            top_n=1,
            model="rerank-english-v3.0"
        )
        
        return {
            "status": "operational",
            "configured": True,
            "api_accessible": True,
            "message": "Cohere API is ready"
        }
        
    except ValueError as e:
        # API key not configured
        return {
            "status": "not_configured",
            "configured": False,
            "api_accessible": False,
            "message": str(e),
            "setup_url": "https://dashboard.cohere.com/api-keys"
        }
    except Exception as e:
        # API error
        return {
            "status": "error",
            "configured": True,
            "api_accessible": False,
            "message": f"API error: {str(e)}"
        }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Cohere Reranking MCP Server"
    }


# Client class for easy integration
class CohereMCPClient:
    """Client for calling Cohere MCP server from agents"""
    
    def __init__(self, base_url: str = "http://localhost:8100"):
        """
        Initialize Cohere MCP client
        
        Args:
            base_url: Base URL of the Cohere MCP server
        """
        self.base_url = base_url
        self.is_available = False
        self._check_availability()
    
    def _check_availability(self):
        """Check if server is available"""
        try:
            import requests
            response = requests.get(f"{self.base_url}/health", timeout=2)
            self.is_available = response.status_code == 200
        except:
            self.is_available = False
    
    def rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = 5) -> Dict[str, Any]:
        """
        Rerank documents using Cohere API via MCP
        
        Args:
            query: Search query
            documents: List of document dictionaries
            top_k: Number of top results
        
        Returns:
            Dictionary with reranked results
        """
        import requests
        
        if not self.is_available:
            self._check_availability()
        
        if not self.is_available:
            return {
                "success": False,
                "error": "Cohere MCP server not available"
            }
        
        try:
            # Prepare documents
            doc_list = []
            for doc in documents:
                doc_list.append({
                    "text": doc.get('content', ''),
                    "chunk_id": doc.get('chunk_id'),
                    "chunk_type": doc.get('chunk_type'),
                    "source_document": doc.get('source_document'),
                    "metadata": doc.get('metadata', {})
                })
            
            # Call MCP server
            response = requests.post(
                f"{self.base_url}/api/v1/rerank",
                json={
                    "query": query,
                    "documents": doc_list,
                    "top_k": top_k,
                    "model": "rerank-english-v3.0"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }
    
    def check_status(self) -> Dict[str, Any]:
        """Check Cohere API status"""
        import requests
        
        try:
            response = requests.get(f"{self.base_url}/api/v1/status", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "status": "error",
                    "message": f"Status check failed: {response.status_code}"
                }
        except Exception as e:
            return {
                "status": "unreachable",
                "message": f"Server unreachable: {str(e)}"
            }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 80)
    print("🚀 Starting Cohere Reranking MCP Server")
    print("=" * 80)
    print("\n📡 Server will be available at: http://localhost:8100")
    print("📖 API docs at: http://localhost:8100/docs")
    print("\n💡 Get your free Cohere API key at: https://dashboard.cohere.com/api-keys")
    print("   Add it to your .env file as: COHERE_API_KEY=your_key_here")
    print("\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8100, log_level="info")
