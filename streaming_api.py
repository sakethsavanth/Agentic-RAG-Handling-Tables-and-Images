"""
Streaming Query API for Real-Time Query Processing
Provides Server-Sent Events (SSE) streaming for live progress updates
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import AsyncGenerator, Optional
import json
import asyncio
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from chatbot_orchestrator import ChatbotOrchestrator
from agents.text_to_sql_agent import TextToSQLAgent

app = FastAPI(
    title="Streaming Query API",
    description="Real-time query processing with live progress updates",
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

# Global orchestrator (initialized on first use)
orchestrator = None


class QueryRequest(BaseModel):
    """Query request model"""
    query: str
    top_k: int = 10
    rerank_top_k: int = 5
    stream: bool = True
    use_cohere: bool = False


def format_sse(data: dict) -> str:
    """
    Format data as Server-Sent Event
    
    Args:
        data: Dictionary to send
        
    Returns:
        SSE formatted string
    """
    return f"data: {json.dumps(data)}\n\n"


async def stream_query_response(
    query: str,
    top_k: int,
    rerank_top_k: int,
    use_cohere: bool
) -> AsyncGenerator[str, None]:
    """
    Stream query processing progress and results
    
    Yields Server-Sent Events (SSE) format:
    data: {"type": "progress", "step": "retrieval", "message": "..."}
    """
    global orchestrator
    
    try:
        # Initialize orchestrator if needed
        if orchestrator is None:
            yield format_sse({
                "type": "progress",
                "step": "initialization",
                "status": "started",
                "message": "🔄 Initializing AI agents...",
                "timestamp": datetime.now().isoformat()
            })
            
            orchestrator = ChatbotOrchestrator(
                retrieval_top_k=top_k,
                rerank_top_k=rerank_top_k,
                enable_logging=True
            )
            
            yield format_sse({
                "type": "progress",
                "step": "initialization",
                "status": "completed",
                "message": "✅ AI agents ready",
                "timestamp": datetime.now().isoformat()
            })
            
            await asyncio.sleep(0.5)
        
        # Step 1: Query Classification (for SQL detection)
        yield format_sse({
            "type": "progress",
            "step": "classification",
            "status": "started",
            "message": "🔍 Classifying your query...",
            "timestamp": datetime.now().isoformat()
        })
        
        await asyncio.sleep(0.5)
        
        # Quick classification check
        sql_agent = TextToSQLAgent()
        classification_state = {"query": query}
        classification_result = sql_agent.classify_query(classification_state)
        
        requires_sql = classification_result.get('requires_sql', False)
        
        yield format_sse({
            "type": "progress",
            "step": "classification",
            "status": "completed",
            "message": f"✅ Query {'requires' if requires_sql else 'does not require'} SQL execution",
            "data": {
                "requires_sql": requires_sql,
                "reasoning": classification_result.get('reasoning', '')
            },
            "timestamp": datetime.now().isoformat()
        })
        
        await asyncio.sleep(0.3)
        
        # If SQL is needed, show SQL generation/execution steps
        if requires_sql:
            # Step 2: SQL Generation
            yield format_sse({
                "type": "progress",
                "step": "sql_generation",
                "status": "started",
                "message": "💾 Generating SQL query...",
                "timestamp": datetime.now().isoformat()
            })
            
            await asyncio.sleep(0.5)
            
            sql_state = sql_agent.generate_sql(classification_result)
            sql_queries = sql_state.get('sql_queries', [])
            
            yield format_sse({
                "type": "progress",
                "step": "sql_generation",
                "status": "completed",
                "message": f"✅ Generated {len(sql_queries)} SQL {'query' if len(sql_queries) == 1 else 'queries'}",
                "data": {"sql_queries": sql_queries},
                "timestamp": datetime.now().isoformat()
            })
            
            await asyncio.sleep(0.3)
            
            # Step 3: SQL Execution
            yield format_sse({
                "type": "progress",
                "step": "sql_execution",
                "status": "started",
                "message": "⚡ Executing SQL queries...",
                "timestamp": datetime.now().isoformat()
            })
            
            for i, sql_query in enumerate(sql_queries, 1):
                yield format_sse({
                    "type": "progress",
                    "step": "sql_execution",
                    "status": "executing",
                    "message": f"⚡ Executing query {i}/{len(sql_queries)}...",
                    "data": {"query_number": i, "total_queries": len(sql_queries)},
                    "timestamp": datetime.now().isoformat()
                })
                
                await asyncio.sleep(0.5)
            
            execution_state = sql_agent.execute_sql(sql_state)
            sql_results = execution_state.get('sql_results', [])
            
            total_rows = sum(r.get('row_count', 0) for r in sql_results if r.get('success'))
            
            yield format_sse({
                "type": "progress",
                "step": "sql_execution",
                "status": "completed",
                "message": f"✅ Retrieved {total_rows} rows from database",
                "data": {"total_rows": total_rows},
                "timestamp": datetime.now().isoformat()
            })
            
            await asyncio.sleep(0.3)
        
        # Step 4: Vector Retrieval
        yield format_sse({
            "type": "progress",
            "step": "retrieval",
            "status": "started",
            "message": "🔍 Retrieving relevant documents...",
            "timestamp": datetime.now().isoformat()
        })
        
        await asyncio.sleep(0.5)
        
        retrieved_chunks = orchestrator.retrieval_agent.retrieve(query, top_k=top_k)
        
        yield format_sse({
            "type": "progress",
            "step": "retrieval",
            "status": "completed",
            "message": f"✅ Retrieved {len(retrieved_chunks)} relevant chunks",
            "data": {"chunk_count": len(retrieved_chunks)},
            "timestamp": datetime.now().isoformat()
        })
        
        await asyncio.sleep(0.3)
        
        # Step 5: Reranking
        rerank_method = "Cohere API" if use_cohere else "LLM-based"
        yield format_sse({
            "type": "progress",
            "step": "reranking",
            "status": "started",
            "message": f"🎯 Reranking results using {rerank_method}...",
            "timestamp": datetime.now().isoformat()
        })
        
        await asyncio.sleep(0.5)
        
        reranked_chunks = orchestrator.reranking_agent.rerank(
            query, 
            retrieved_chunks, 
            top_k=rerank_top_k,
            use_cohere=use_cohere
        )
        
        yield format_sse({
            "type": "progress",
            "step": "reranking",
            "status": "completed",
            "message": f"✅ Reranked to top {len(reranked_chunks)} most relevant chunks",
            "data": {"reranked_count": len(reranked_chunks), "method": rerank_method},
            "timestamp": datetime.now().isoformat()
        })
        
        await asyncio.sleep(0.3)
        
        # Step 6: Generating Answer
        yield format_sse({
            "type": "progress",
            "step": "generation",
            "status": "started",
            "message": "💬 Generating final answer...",
            "timestamp": datetime.now().isoformat()
        })
        
        await asyncio.sleep(0.5)
        
        # Process complete query (this will generate the final answer)
        result = orchestrator.process_user_query(query, use_cohere_rerank=use_cohere)
        
        yield format_sse({
            "type": "progress",
            "step": "generation",
            "status": "completed",
            "message": "✅ Answer generated",
            "timestamp": datetime.now().isoformat()
        })
        
        await asyncio.sleep(0.3)
        
        # Send final answer
        yield format_sse({
            "type": "answer",
            "content": result.get('final_answer', ''),
            "metadata": {
                "confidence": result.get('confidence_score', 0),
                "retrieved_chunks": result.get('retrieved_chunks_count', 0),
                "reranked_chunks": result.get('reranked_chunks_count', 0),
                "sql_executed": result.get('sql_executed', False),
                "duration_seconds": result.get('duration_seconds', 0),
                "reranking_method": rerank_method
            },
            "timestamp": datetime.now().isoformat()
        })
        
        # Send sources
        yield format_sse({
            "type": "sources",
            "data": result.get('rag_sources', []),
            "timestamp": datetime.now().isoformat()
        })
        
        # Send SQL details if available
        if requires_sql:
            yield format_sse({
                "type": "sql_details",
                "data": {
                    "queries": result.get('sql_queries', []),
                    "answer": result.get('sql_answer', '')
                },
                "timestamp": datetime.now().isoformat()
            })
        
        # Final completion message
        yield format_sse({
            "type": "complete",
            "message": "✅ Query processing completed",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        # Stream error
        yield format_sse({
            "type": "error",
            "message": f"❌ Error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })


@app.post("/api/v1/query")
async def query_chatbot(request: QueryRequest):
    """
    Query the RAG chatbot with optional streaming
    
    Args:
        query: User's natural language question
        stream: Whether to stream the response
        top_k: Number of chunks to retrieve
        rerank_top_k: Number of chunks after reranking
        use_cohere: Whether to use Cohere for reranking
        
    Returns:
        Streaming or complete response
    """
    
    if request.stream:
        # Return streaming response
        return StreamingResponse(
            stream_query_response(
                query=request.query,
                top_k=request.top_k,
                rerank_top_k=request.rerank_top_k,
                use_cohere=request.use_cohere
            ),
            media_type="text/event-stream"
        )
    else:
        # Return complete response
        global orchestrator
        if orchestrator is None:
            orchestrator = ChatbotOrchestrator(
                retrieval_top_k=request.top_k,
                rerank_top_k=request.rerank_top_k
            )
        
        result = orchestrator.process_user_query(
            request.query,
            use_cohere_rerank=request.use_cohere
        )
        return result


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Streaming Query API",
        "orchestrator_initialized": orchestrator is not None
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 80)
    print("🚀 Starting Streaming Query API Server")
    print("=" * 80)
    print("\n📡 Server will be available at: http://localhost:8090")
    print("📖 API docs at: http://localhost:8090/docs")
    print("\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8090, log_level="info")
