import os
import re
import tempfile
import uuid
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from src.document_processing.doc_processor import DocumentProcessor
from src.embeddings.embedding_generator import EmbeddingGenerator
from src.vector_database.milvus_vector_db import MilvusVectorDB
from src.generation.rag import RAGGenerator
from src.web_scraping.web_scraper import WebScraper


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file in notebook-lm-clone directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
logger.info(f"Loading .env from: {env_path}")

app = FastAPI(title="NotebookLM API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"]
    ,
    allow_headers=["*"],
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
DB_URL = os.getenv("SUPABASE_DB_URL") or os.getenv("SUPABASE_POSTGRES_URL") or os.getenv("DATABASE_URL")

logger.info(f"Environment loaded - DB_URL present: {bool(DB_URL)}")

UPLOAD_DIR = Path("./uploads")
OUTPUT_DIR = Path("./outputs")
CACHE_DIR = Path("./.cache")
for folder in (UPLOAD_DIR, OUTPUT_DIR, CACHE_DIR):
    folder.mkdir(parents=True, exist_ok=True)

# Mount static files directory for audio/podcast outputs (after OUTPUT_DIR is defined)
app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")

# In-memory fallback registry keyed by user_id when DB unavailable
sources_registry: Dict[str, List[dict]] = {}


def sanitize_collection_name(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", value or "default")
    return safe[:48] or "default"


def get_db_connection():
    if not DB_URL:
        logger.warning("SUPABASE_DB_URL not set; falling back to in-memory registry")
        return None
    return psycopg2.connect(DB_URL, sslmode="require")


def ensure_sources_table():
    """Create tables if they don't exist. Non-blocking if DB unavailable."""
    try:
        conn = get_db_connection()
        if not conn:
            logger.warning("Database unavailable - tables not created")
            return
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS notebooklm_sources (
                        id UUID PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        name TEXT,
                        path TEXT,
                        type TEXT,
                        chunks INT,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    """
                )
                # Create conversation history table
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversation_history (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        sources JSONB,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS idx_conversation_user_time 
                    ON conversation_history(user_id, created_at DESC);
                    """
                )
        conn.close()
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        # Don't crash the app if table creation fails


def save_source_record(source: dict):
    conn = get_db_connection()
    if not conn:
        # Fallback to in-memory cache
        user_bucket = sources_registry.setdefault(source["user_id"], [])
        user_bucket.append(source)
        return
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO notebooklm_sources (id, user_id, name, path, type, chunks)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    name = EXCLUDED.name,
                    path = EXCLUDED.path,
                    type = EXCLUDED.type,
                    chunks = EXCLUDED.chunks;
                """,
                (
                    source["id"],
                    source["user_id"],
                    source.get("name"),
                    source.get("path"),
                    source.get("type"),
                    source.get("chunks", 0),
                ),
            )
    conn.close()


def fetch_sources_for_user(user_id: str) -> List[dict]:
    conn = get_db_connection()
    if not conn:
        return sources_registry.get(user_id, [])
    with conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                "SELECT id, user_id, name, path, type, chunks, created_at FROM notebooklm_sources WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            )
            rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


class QueryRequest(BaseModel):
    query: str
    top_k: int = 8
    user_id: str


class SummaryRequest(BaseModel):
    max_chunks: int = 12
    summary_length: str = "medium"
    user_id: str


class PodcastRequest(BaseModel):
    query: str
    source_path: Optional[str] = None
    user_id: str


# Shared components and per-user pipelines
doc_processor = DocumentProcessor()
embedding_generator = EmbeddingGenerator()
web_scraper = WebScraper(FIRECRAWL_API_KEY) if FIRECRAWL_API_KEY else None

user_pipelines: Dict[str, Dict[str, object]] = {}

ensure_sources_table()


def get_user_pipeline(user_id: str) -> Dict[str, object]:
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    if user_id in user_pipelines:
        return user_pipelines[user_id]

    safe_id = sanitize_collection_name(user_id)
    collection_name = f"notebook_lm_{safe_id}"
    db_path = CACHE_DIR / f"milvus_{safe_id}.db"

    vector_db = MilvusVectorDB(
        db_path=str(db_path),
        collection_name=collection_name,
        embedding_dim=embedding_generator.get_embedding_dimension(),
    )
    rag_generator = RAGGenerator(
        embedding_generator=embedding_generator,
        vector_db=vector_db,
        openai_api_key=OPENAI_API_KEY,
    )

    user_pipelines[user_id] = {
        "vector_db": vector_db,
        "rag_generator": rag_generator,
    }
    return user_pipelines[user_id]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/ingest")
async def ingest(
    files: Optional[List[UploadFile]] = File(default=None),
    web_url: Optional[str] = Form(default=None),
    user_id: str = Form(...),
):
    if not files and not web_url:
        raise HTTPException(status_code=400, detail="Provide files or web_url")

    user_pipeline = get_user_pipeline(user_id)

    ingested = []
    try:
        # Handle file uploads
        if files:
            for file in files:
                suffix = Path(file.filename).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=UPLOAD_DIR) as tmp:
                    content = await file.read()
                    tmp.write(content)
                    tmp_path = Path(tmp.name)
                chunks = doc_processor.process_document(str(tmp_path))
                embeddings = embedding_generator.generate_embeddings(chunks)
                user_pipeline["vector_db"].insert_embeddings(embeddings)
                source_id = str(uuid.uuid4())
                source_record = {
                    "id": source_id,
                    "user_id": user_id,
                    "name": file.filename,
                    "path": str(tmp_path),
                    "type": suffix.lstrip("."),
                    "chunks": len(chunks),
                }
                save_source_record(source_record)
                ingested.append({"id": source_id, "name": file.filename, "chunks": len(chunks)})

        # Handle web URL ingestion
        if web_url:
            if not web_scraper:
                raise HTTPException(status_code=400, detail="Web scraping not configured (missing FIRECRAWL_API_KEY)")
            chunks = web_scraper.scrape_url(web_url)
            embeddings = embedding_generator.generate_embeddings(chunks)
            user_pipeline["vector_db"].insert_embeddings(embeddings)
            source_id = str(uuid.uuid4())
            source_record = {
                "id": source_id,
                "user_id": user_id,
                "name": web_url,
                "path": web_url,
                "type": "web",
                "chunks": len(chunks),
            }
            save_source_record(source_record)
            ingested.append({"id": source_id, "name": web_url, "chunks": len(chunks)})

        return {"status": "ok", "ingested": ingested}
    except Exception as e:
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sources")
def list_sources(user_id: str):
    sources = fetch_sources_for_user(user_id)
    return {"sources": sources}


@app.post("/api/query")
def query_rag(req: QueryRequest):
    user_pipeline = get_user_pipeline(req.user_id)
    result = user_pipeline["rag_generator"].generate_response(
        query=req.query,
        top_k=req.top_k,
    )
    return {
        "answer": result.response,
        "sources": result.sources_used,
        "retrieval_count": result.retrieval_count,
    }


@app.post("/api/query/stream")
async def query_stream(req: QueryRequest):
    """
    Streaming version: sends text character by character for typewriter effect with TTS
    """
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=400, detail="OpenAI API key not configured")

    logger.info(f"Query streaming request: {req.query[:50]}..., user: {req.user_id}")
    
    try:
        # Get user pipeline for RAG
        user_pipeline = get_user_pipeline(req.user_id)
        
        # Generate RAG response
        rag_result = user_pipeline["rag_generator"].generate_response(
            query=req.query,
            top_k=req.top_k,
        )
        
        answer_text = rag_result.response
        sources = rag_result.sources_used
        
        # Generate audio in background (non-blocking)
        import threading
        audio_url = None
        
        def generate_audio():
            nonlocal audio_url
            # Import TTS generator here to avoid circular imports
            try:
                from src.podcast.text_to_speech import PodcastTTSGenerator
                tts_gen = PodcastTTSGenerator()
                audio_file_path = tts_gen.generate_single_audio(
                    text=answer_text,
                    output_dir=str(OUTPUT_DIR / "tts"),
                    voice="en-US-AriaNeural"
                )
                # Convert to URL path with actual filename
                audio_filename = Path(audio_file_path).name
                audio_url = f"/outputs/tts/{audio_filename}"
            except Exception as e:
                logger.error(f"TTS generation failed: {e}")
        
        audio_thread = threading.Thread(target=generate_audio)
        audio_thread.start()
        
        # Stream the response
        async def generate():
            import json
            
            # First send metadata
            metadata = {
                "type": "metadata",
                "sources": sources,
                "retrieval_count": rag_result.retrieval_count
            }
            yield f"data: {json.dumps(metadata)}\n\n"
            
            # Wait for audio to be ready FIRST before starting typewriter
            audio_thread.join(timeout=10)
            
            # Send audio URL first if available
            if audio_url:
                audio_data = {
                    "type": "audio",
                    "file": audio_url
                }
                yield f"data: {json.dumps(audio_data)}\n\n"
                # Small delay to ensure audio starts playing
                await asyncio.sleep(0.1)
            
            # Now stream text character by character
            for char in answer_text:
                yield f"data: {json.dumps({'type': 'text', 'content': char})}\n\n"
                await asyncio.sleep(0.02)  # Small delay for typewriter effect
            
            yield "data: {\"type\": \"done\"}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
        
    except Exception as e:
        logger.error(f"Error in query streaming: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/summary")
def summary(req: SummaryRequest):
    user_pipeline = get_user_pipeline(req.user_id)
    result = user_pipeline["rag_generator"].generate_summary(
        max_chunks=req.max_chunks,
        summary_length=req.summary_length,
    )
    return {
        "summary": result.response,
        "sources": result.sources_used,
        "retrieval_count": result.retrieval_count,
    }




# Conversation History Endpoints
class ConversationMessage(BaseModel):
    user_id: str
    role: str  # "user" or "assistant"
    content: str
    sources: Optional[List[dict]] = None


@app.post("/api/conversations/save")
def save_conversation_message(msg: ConversationMessage):
    """Save a conversation message to the database."""
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database unavailable"}
    
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO conversation_history (user_id, role, content, sources)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, created_at;
                    """,
                    (
                        msg.user_id,
                        msg.role,
                        msg.content,
                        json.dumps(msg.sources) if msg.sources else None,
                    ),
                )
                result = cur.fetchone()
                return {
                    "status": "success",
                    "id": str(result[0]),
                    "created_at": result[1].isoformat(),
                }
    except Exception as e:
        logger.error(f"Error saving conversation message: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/api/conversations/{user_id}")
def get_conversation_history(user_id: str, limit: int = 100):
    """Retrieve conversation history for a user."""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, role, content, sources, created_at
                    FROM conversation_history
                    WHERE user_id = %s
                    ORDER BY created_at ASC
                    LIMIT %s;
                    """,
                    (user_id, limit),
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": str(row[0]),
                        "role": row[1],
                        "content": row[2],
                        "sources": json.loads(row[3]) if isinstance(row[3], str) else row[3] if row[3] else None,
                        "timestamp": row[4].isoformat(),
                    }
                    for row in rows
                ]
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.delete("/api/conversations/{user_id}")
def delete_conversation_history(user_id: str, older_than_days: Optional[int] = None):
    """Delete conversation history for a user. Optionally delete messages older than N days."""
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database unavailable"}
    
    try:
        with conn:
            with conn.cursor() as cur:
                if older_than_days:
                    cur.execute(
                        """
                        DELETE FROM conversation_history
                        WHERE user_id = %s
                        AND created_at < NOW() - INTERVAL '%s days';
                        """,
                        (user_id, older_than_days),
                    )
                else:
                    cur.execute(
                        """
                        DELETE FROM conversation_history
                        WHERE user_id = %s;
                        """,
                        (user_id,),
                    )
                deleted_count = cur.rowcount
                return {
                    "status": "success",
                    "deleted_count": deleted_count,
                }
    except Exception as e:
        logger.error(f"Error deleting conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
