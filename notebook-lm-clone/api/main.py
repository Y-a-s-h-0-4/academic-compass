import os
import re
import tempfile
import uuid
import json
import hashlib
import logging
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, RedirectResponse
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
DB_URL = os.getenv("SUPABASE_DB_URL") or os.getenv("SUPABASE_POSTGRES_URL") or os.getenv("DATABASE_URL")
LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or "").strip().lower() or None
LLM_MODEL = (os.getenv("LLM_MODEL") or "").strip() or None
GEMINI_IMAGE_METADATA_MODEL = (os.getenv("GEMINI_IMAGE_METADATA_MODEL") or "").strip() or None
GEMINI_IMAGE_METADATA_TIMEOUT_SEC = os.getenv("GEMINI_IMAGE_METADATA_TIMEOUT_SEC")
GEMINI_IMAGE_MAX_CAPTION_CHARS = os.getenv("GEMINI_IMAGE_MAX_CAPTION_CHARS")

logger.info(f"Environment loaded - DB_URL present: {bool(DB_URL)}")

UPLOAD_DIR = Path("./uploads")
OUTPUT_DIR = Path("./outputs")
CACHE_DIR = Path("./.cache")
for folder in (UPLOAD_DIR, OUTPUT_DIR, CACHE_DIR):
    folder.mkdir(parents=True, exist_ok=True)

# Mount static files directory for audio/podcast outputs (after OUTPUT_DIR is defined)
app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# In-memory fallback registry keyed by user_id -> chat_id when DB unavailable
sources_registry: Dict[str, Dict[str, List[dict]]] = {}
learning_scores_registry: Dict[str, Dict[str, dict]] = {}
learning_attempts_registry: Dict[str, List[dict]] = {}


def sanitize_collection_name(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", value or "default")
    return safe[:48] or "default"


def normalize_chat_id(chat_id: Optional[str]) -> str:
    value = (chat_id or "").strip()
    return value or "default"


def build_pipeline_identity(user_id: str, chat_id: str) -> str:
    safe_user = sanitize_collection_name(user_id)[:20]
    safe_chat = sanitize_collection_name(chat_id)[:20]
    digest = hashlib.sha1(f"{user_id}:{chat_id}".encode("utf-8")).hexdigest()[:10]
    return f"{safe_user}_{safe_chat}_{digest}"


def get_memory_sources_bucket(user_id: str, chat_id: str) -> List[dict]:
    user_bucket = sources_registry.setdefault(user_id, {})
    return user_bucket.setdefault(chat_id, [])


def get_memory_learning_scores_bucket(user_id: str) -> Dict[str, dict]:
    return learning_scores_registry.setdefault(user_id, {})


def get_memory_learning_attempts_bucket(user_id: str) -> List[dict]:
    return learning_attempts_registry.setdefault(user_id, [])


def get_db_connection():
    if not DB_URL:
        logger.warning("SUPABASE_DB_URL not set; falling back to in-memory registry")
        return None
    try:
        return psycopg2.connect(DB_URL, sslmode="require")
    except Exception as e:
        logger.error(f"Database connection failed; falling back to in-memory registry: {e}")
        return None


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
                        chat_id TEXT NOT NULL DEFAULT 'default',
                        name TEXT,
                        path TEXT,
                        type TEXT,
                        chunks INT,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    """
                )
                # Backward-compatible migration for existing tables.
                cur.execute("ALTER TABLE notebooklm_sources ADD COLUMN IF NOT EXISTS chat_id TEXT;")
                cur.execute(
                    "UPDATE notebooklm_sources SET chat_id = 'default' WHERE chat_id IS NULL OR chat_id = '';"
                )
                cur.execute("ALTER TABLE notebooklm_sources ALTER COLUMN chat_id SET DEFAULT 'default';")
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_sources_user_chat_time
                    ON notebooklm_sources(user_id, chat_id, created_at DESC);
                    """
                )
                # Create conversation history table
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversation_history (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id TEXT NOT NULL,
                        chat_id TEXT NOT NULL DEFAULT 'default',
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        sources JSONB,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    """
                )
                cur.execute("ALTER TABLE conversation_history ADD COLUMN IF NOT EXISTS chat_id TEXT;")
                cur.execute(
                    "UPDATE conversation_history SET chat_id = 'default' WHERE chat_id IS NULL OR chat_id = '';"
                )
                cur.execute("ALTER TABLE conversation_history ALTER COLUMN chat_id SET DEFAULT 'default';")
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_conversation_user_chat_time
                    ON conversation_history(user_id, chat_id, created_at DESC);
                    """
                )

                # Learning scores aggregated by user + course
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS learning_course_scores (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id TEXT NOT NULL,
                        chat_id TEXT NOT NULL DEFAULT 'default',
                        course_id TEXT NOT NULL,
                        course_name TEXT,
                        total_attempts INT NOT NULL DEFAULT 0,
                        total_questions INT NOT NULL DEFAULT 0,
                        total_correct INT NOT NULL DEFAULT 0,
                        average_score DOUBLE PRECISION NOT NULL DEFAULT 0,
                        best_score DOUBLE PRECISION NOT NULL DEFAULT 0,
                        latest_score DOUBLE PRECISION NOT NULL DEFAULT 0,
                        latest_feedback TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW(),
                        UNIQUE(user_id, course_id)
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_learning_scores_user_updated
                    ON learning_course_scores(user_id, updated_at DESC);
                    """
                )

                # Raw attempt history for future tests/analytics
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS learning_quiz_attempts (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id TEXT NOT NULL,
                        chat_id TEXT NOT NULL DEFAULT 'default',
                        course_id TEXT NOT NULL,
                        course_name TEXT,
                        total_questions INT NOT NULL,
                        correct_answers INT NOT NULL,
                        score DOUBLE PRECISION NOT NULL,
                        feedback TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_learning_attempts_user_time
                    ON learning_quiz_attempts(user_id, created_at DESC);
                    """
                )
        conn.close()
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        # Don't crash the app if table creation fails


def save_learning_score(
    user_id: str,
    chat_id: str,
    course_id: str,
    course_name: str,
    total_questions: int,
    correct_answers: int,
    feedback: Optional[str] = None,
) -> Dict[str, Any]:
    chat_scope = normalize_chat_id(chat_id)
    safe_course_id = sanitize_collection_name(course_id)[:64] or chat_scope
    safe_course_name = (course_name or "").strip() or safe_course_id
    questions = max(int(total_questions), 1)
    correct = max(0, min(int(correct_answers), questions))
    score = round((correct / questions) * 100, 2)

    conn = get_db_connection()
    if not conn:
        bucket = get_memory_learning_scores_bucket(user_id)
        existing = bucket.get(safe_course_id)
        if existing:
            total_attempts = int(existing.get("total_attempts", 0)) + 1
            total_q = int(existing.get("total_questions", 0)) + questions
            total_c = int(existing.get("total_correct", 0)) + correct
            average_score = round((total_c / total_q) * 100, 2) if total_q else 0.0
            best_score = max(float(existing.get("best_score", 0)), score)
        else:
            total_attempts = 1
            total_q = questions
            total_c = correct
            average_score = score
            best_score = score

        result = {
            "user_id": user_id,
            "chat_id": chat_scope,
            "course_id": safe_course_id,
            "course_name": safe_course_name,
            "total_attempts": total_attempts,
            "total_questions": total_q,
            "total_correct": total_c,
            "average_score": average_score,
            "best_score": best_score,
            "latest_score": score,
            "latest_feedback": feedback or "",
        }
        bucket[safe_course_id] = result
        get_memory_learning_attempts_bucket(user_id).append(
            {
                "user_id": user_id,
                "chat_id": chat_scope,
                "course_id": safe_course_id,
                "course_name": safe_course_name,
                "total_questions": questions,
                "correct_answers": correct,
                "score": score,
                "feedback": feedback or "",
            }
        )
        return result

    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO learning_quiz_attempts (
                        user_id, chat_id, course_id, course_name, total_questions, correct_answers, score, feedback
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        user_id,
                        chat_scope,
                        safe_course_id,
                        safe_course_name,
                        questions,
                        correct,
                        score,
                        feedback,
                    ),
                )

                cur.execute(
                    """
                    INSERT INTO learning_course_scores (
                        user_id,
                        chat_id,
                        course_id,
                        course_name,
                        total_attempts,
                        total_questions,
                        total_correct,
                        average_score,
                        best_score,
                        latest_score,
                        latest_feedback,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (user_id, course_id) DO UPDATE SET
                        chat_id = EXCLUDED.chat_id,
                        course_name = COALESCE(NULLIF(EXCLUDED.course_name, ''), learning_course_scores.course_name),
                        total_attempts = learning_course_scores.total_attempts + 1,
                        total_questions = learning_course_scores.total_questions + EXCLUDED.total_questions,
                        total_correct = learning_course_scores.total_correct + EXCLUDED.total_correct,
                        average_score = ROUND(
                            ((learning_course_scores.total_correct + EXCLUDED.total_correct)::numeric
                            / NULLIF((learning_course_scores.total_questions + EXCLUDED.total_questions), 0)) * 100,
                            2
                        )::double precision,
                        best_score = GREATEST(learning_course_scores.best_score, EXCLUDED.latest_score),
                        latest_score = EXCLUDED.latest_score,
                        latest_feedback = EXCLUDED.latest_feedback,
                        updated_at = NOW()
                    RETURNING
                        user_id,
                        chat_id,
                        course_id,
                        course_name,
                        total_attempts,
                        total_questions,
                        total_correct,
                        average_score,
                        best_score,
                        latest_score,
                        latest_feedback,
                        updated_at;
                    """,
                    (
                        user_id,
                        chat_scope,
                        safe_course_id,
                        safe_course_name,
                        questions,
                        correct,
                        score,
                        score,
                        score,
                        feedback,
                    ),
                )
                row = cur.fetchone()
                return dict(row) if row else {}
    finally:
        conn.close()


def fetch_learning_score_summary(user_id: str) -> Dict[str, Any]:
    conn = get_db_connection()
    if not conn:
        course_rows = list(get_memory_learning_scores_bucket(user_id).values())
        total_attempts = sum(int(row.get("total_attempts", 0)) for row in course_rows)
        total_questions = sum(int(row.get("total_questions", 0)) for row in course_rows)
        total_correct = sum(int(row.get("total_correct", 0)) for row in course_rows)
        overall_avg = round((total_correct / total_questions) * 100, 2) if total_questions else 0.0
        best_score = max((float(row.get("best_score", 0)) for row in course_rows), default=0.0)
        return {
            "user_id": user_id,
            "overall": {
                "total_attempts": total_attempts,
                "average_score": overall_avg,
                "best_score": round(best_score, 2),
                "total_courses": len(course_rows),
            },
            "courses": sorted(course_rows, key=lambda row: row.get("average_score", 0), reverse=True),
        }

    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        user_id,
                        chat_id,
                        course_id,
                        course_name,
                        total_attempts,
                        total_questions,
                        total_correct,
                        average_score,
                        best_score,
                        latest_score,
                        latest_feedback,
                        updated_at
                    FROM learning_course_scores
                    WHERE user_id = %s
                    ORDER BY updated_at DESC;
                    """,
                    (user_id,),
                )
                rows = [dict(row) for row in cur.fetchall()]

                cur.execute(
                    """
                    SELECT
                        COALESCE(SUM(total_attempts), 0) AS total_attempts,
                        COALESCE(SUM(total_questions), 0) AS total_questions,
                        COALESCE(SUM(total_correct), 0) AS total_correct,
                        COALESCE(MAX(best_score), 0) AS best_score,
                        COUNT(*) AS total_courses
                    FROM learning_course_scores
                    WHERE user_id = %s;
                    """,
                    (user_id,),
                )
                overall_row = dict(cur.fetchone() or {})

        total_questions = int(overall_row.get("total_questions") or 0)
        total_correct = int(overall_row.get("total_correct") or 0)
        average_score = round((total_correct / total_questions) * 100, 2) if total_questions else 0.0

        return {
            "user_id": user_id,
            "overall": {
                "total_attempts": int(overall_row.get("total_attempts") or 0),
                "average_score": average_score,
                "best_score": round(float(overall_row.get("best_score") or 0), 2),
                "total_courses": int(overall_row.get("total_courses") or 0),
            },
            "courses": rows,
        }
    finally:
        conn.close()


def save_source_record(source: dict):
    chat_id = normalize_chat_id(source.get("chat_id"))
    conn = get_db_connection()
    if not conn:
        # Fallback to in-memory cache
        get_memory_sources_bucket(source["user_id"], chat_id).append({**source, "chat_id": chat_id})
        return

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO notebooklm_sources (id, user_id, chat_id, name, path, type, chunks)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        chat_id = EXCLUDED.chat_id,
                        name = EXCLUDED.name,
                        path = EXCLUDED.path,
                        type = EXCLUDED.type,
                        chunks = EXCLUDED.chunks;
                    """,
                    (
                        source["id"],
                        source["user_id"],
                        chat_id,
                        source.get("name"),
                        source.get("path"),
                        source.get("type"),
                        source.get("chunks", 0),
                    ),
                )
    except Exception as e:
        logger.error(f"Failed to save source in DB; using in-memory fallback: {e}")
        get_memory_sources_bucket(source["user_id"], chat_id).append({**source, "chat_id": chat_id})
    finally:
        conn.close()


def fetch_sources_for_user(user_id: str, chat_id: Optional[str]) -> List[dict]:
    chat_scope = normalize_chat_id(chat_id)
    conn = get_db_connection()
    if not conn:
        return get_memory_sources_bucket(user_id, chat_scope)

    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, user_id, chat_id, name, path, type, chunks, created_at
                    FROM notebooklm_sources
                    WHERE user_id = %s AND chat_id = %s
                    ORDER BY created_at DESC
                    """,
                    (user_id, chat_scope),
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch sources from DB; using in-memory fallback: {e}")
        return get_memory_sources_bucket(user_id, chat_scope)
    finally:
        conn.close()


def fetch_source_for_user(user_id: str, source_id: str, chat_id: Optional[str] = None) -> Optional[dict]:
    """Fetch a single source by id for a user, optionally scoped to a chat."""
    chat_scope = normalize_chat_id(chat_id) if chat_id else None
    conn = get_db_connection()

    if not conn:
        user_bucket = sources_registry.get(user_id, {})
        if chat_scope:
            for item in user_bucket.get(chat_scope, []):
                if str(item.get("id")) == source_id:
                    return item
            return None

        for items in user_bucket.values():
            for item in items:
                if str(item.get("id")) == source_id:
                    return item
        return None

    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                if chat_scope:
                    cur.execute(
                        """
                        SELECT id, user_id, chat_id, name, path, type, chunks, created_at
                        FROM notebooklm_sources
                        WHERE id::text = %s AND user_id = %s AND chat_id = %s
                        LIMIT 1;
                        """,
                        (source_id, user_id, chat_scope),
                    )
                    row = cur.fetchone()
                    if row:
                        return dict(row)

                cur.execute(
                    """
                    SELECT id, user_id, chat_id, name, path, type, chunks, created_at
                    FROM notebooklm_sources
                    WHERE id::text = %s AND user_id = %s
                    LIMIT 1;
                    """,
                    (source_id, user_id),
                )
                row = cur.fetchone()
                return dict(row) if row else None
    except Exception as e:
        logger.error(f"Failed to fetch source in DB: {e}")
        return None
    finally:
        conn.close()


def delete_source_for_user(user_id: str, chat_id: str, source_id: str) -> Optional[dict]:
    """Delete one source record and return the deleted row payload for vector cleanup."""
    chat_scope = normalize_chat_id(chat_id)
    conn = get_db_connection()

    if not conn:
        bucket = get_memory_sources_bucket(user_id, chat_scope)
        for idx, item in enumerate(bucket):
            if str(item.get("id")) == source_id:
                return bucket.pop(idx)
        return None

    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    """
                    DELETE FROM notebooklm_sources
                    WHERE id::text = %s AND user_id = %s AND chat_id = %s
                    RETURNING id, user_id, chat_id, name, path, type, chunks;
                    """,
                    (source_id, user_id, chat_scope),
                )
                row = cur.fetchone()
                if row:
                    return dict(row)

                # Fallback: allow delete by source id + user across chats.
                cur.execute(
                    """
                    DELETE FROM notebooklm_sources
                    WHERE id::text = %s AND user_id = %s
                    RETURNING id, user_id, chat_id, name, path, type, chunks;
                    """,
                    (source_id, user_id),
                )
                row = cur.fetchone()
                return dict(row) if row else None
    except Exception as e:
        logger.error(f"Failed to delete source in DB: {e}")
        raise
    finally:
        conn.close()


class QueryRequest(BaseModel):
    query: str
    top_k: int = 8
    user_id: str
    chat_id: str = "default"


NO_INFO_FALLBACK = "I don't have information about this in the course materials."


def _adapt_image_only_answer(answer: str, sources: List[dict]) -> str:
    cleaned = (answer or "").strip()
    if cleaned.lower().rstrip(".") != NO_INFO_FALLBACK.lower().rstrip("."):
        return answer

    visual_refs: List[str] = []
    for source in sources or []:
        if source.get("asset_type") != "image":
            continue
        reference = str(source.get("reference") or "").strip()
        if reference and reference not in visual_refs:
            visual_refs.append(reference)

    if not visual_refs:
        return answer

    refs_preview = ", ".join(visual_refs[:4])
    return (
        "I couldn't find enough text details for this question, "
        f"but I found relevant extracted images you can review below {refs_preview}."
    )


class SummaryRequest(BaseModel):
    max_chunks: int = 12
    summary_length: str = "medium"
    user_id: str
    chat_id: str = "default"


class PodcastRequest(BaseModel):
    query: str
    source_path: Optional[str] = None
    user_id: str
    chat_id: str = "default"


class LearningAidRequest(BaseModel):
    user_id: str
    chat_id: str = "default"
    topic: Optional[str] = None
    difficulty_level: str = "Intermediate"
    learning_objective: Optional[str] = None
    num_questions: int = 5
    num_cards: int = 10
    max_chunks: int = 12


class LearningScoreSubmissionRequest(BaseModel):
    user_id: str
    chat_id: str = "default"
    course_id: Optional[str] = None
    course_name: Optional[str] = None
    total_questions: int
    correct_answers: int
    feedback: Optional[str] = None


# Shared components and per-user pipelines
doc_processor = DocumentProcessor(
    gemini_api_key=GEMINI_API_KEY or None,
    image_metadata_model=GEMINI_IMAGE_METADATA_MODEL,
    image_metadata_timeout_sec=float(GEMINI_IMAGE_METADATA_TIMEOUT_SEC) if GEMINI_IMAGE_METADATA_TIMEOUT_SEC else None,
    image_max_caption_chars=int(GEMINI_IMAGE_MAX_CAPTION_CHARS) if GEMINI_IMAGE_MAX_CAPTION_CHARS else None,
)
embedding_generator = EmbeddingGenerator()
web_scraper = WebScraper(
    FIRECRAWL_API_KEY,
    gemini_api_key=GEMINI_API_KEY or None,
    image_metadata_model=GEMINI_IMAGE_METADATA_MODEL,
    image_metadata_timeout_sec=float(GEMINI_IMAGE_METADATA_TIMEOUT_SEC) if GEMINI_IMAGE_METADATA_TIMEOUT_SEC else None,
    image_max_caption_chars=int(GEMINI_IMAGE_MAX_CAPTION_CHARS) if GEMINI_IMAGE_MAX_CAPTION_CHARS else None,
) if FIRECRAWL_API_KEY else None

user_pipelines: Dict[str, Dict[str, object]] = {}

ensure_sources_table()


def get_user_pipeline(user_id: str, chat_id: Optional[str] = None) -> Dict[str, object]:
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    chat_scope = normalize_chat_id(chat_id)
    pipeline_key = f"{user_id}::{chat_scope}"

    if pipeline_key in user_pipelines:
        return user_pipelines[pipeline_key]

    identity = build_pipeline_identity(user_id, chat_scope)
    collection_name = f"notebook_lm_{identity}"
    db_path = CACHE_DIR / f"milvus_{identity}.db"

    vector_db = MilvusVectorDB(
        db_path=str(db_path),
        collection_name=collection_name,
        embedding_dim=embedding_generator.get_embedding_dimension(),
    )
    rag_generator = RAGGenerator(
        embedding_generator=embedding_generator,
        vector_db=vector_db,
        openai_api_key=OPENAI_API_KEY or None,
        gemini_api_key=GEMINI_API_KEY or None,
        provider=LLM_PROVIDER,
        model_name=LLM_MODEL,
    )

    user_pipelines[pipeline_key] = {
        "vector_db": vector_db,
        "rag_generator": rag_generator,
    }
    return user_pipelines[pipeline_key]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/ingest")
async def ingest(
    files: Optional[List[UploadFile]] = File(default=None),
    web_url: Optional[str] = Form(default=None),
    user_id: str = Form(...),
    chat_id: str = Form("default"),
):
    if not files and not web_url:
        raise HTTPException(status_code=400, detail="Provide files or web_url")

    chat_scope = normalize_chat_id(chat_id)
    user_pipeline = get_user_pipeline(user_id, chat_scope)

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
                chunks = doc_processor.process_document(str(tmp_path), source_name=file.filename)
                embeddings = embedding_generator.generate_embeddings(chunks)
                user_pipeline["vector_db"].insert_embeddings(embeddings)
                source_id = str(uuid.uuid4())
                source_record = {
                    "id": source_id,
                    "user_id": user_id,
                    "chat_id": chat_scope,
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
                "chat_id": chat_scope,
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
def list_sources(user_id: str, chat_id: str = "default"):
    sources = fetch_sources_for_user(user_id, chat_id)
    return {"sources": sources}


@app.delete("/api/sources/{source_id}")
def delete_source(source_id: str, user_id: str, chat_id: str = "default"):
    chat_scope = normalize_chat_id(chat_id)
    deleted_source = delete_source_for_user(user_id, chat_scope, source_id)

    if not deleted_source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Best-effort vector cleanup to keep retrieval aligned with source list.
    removed_vectors = 0
    try:
        user_pipeline = get_user_pipeline(user_id, chat_scope)
        source_name = (deleted_source.get("name") or "").strip()
        if source_name:
            removed_vectors = user_pipeline["vector_db"].delete_by_source_file(source_name)
    except Exception as e:
        logger.warning(f"Vector cleanup for source {source_id} failed: {e}")

    return {
        "status": "ok",
        "deleted_source_id": source_id,
        "removed_vectors": removed_vectors,
    }


@app.get("/api/sources/{source_id}/view")
def view_source(source_id: str, user_id: str, chat_id: Optional[str] = None):
    source = fetch_source_for_user(user_id=user_id, source_id=source_id, chat_id=chat_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    source_type = (source.get("type") or "").lower()
    source_path = (source.get("path") or "").strip()
    source_name = source.get("name") or "source"

    if source_type == "web":
        if not source_path:
            raise HTTPException(status_code=404, detail="Web source URL unavailable")
        return RedirectResponse(url=source_path)

    if not source_path:
        raise HTTPException(status_code=404, detail="Source file path unavailable")

    path_obj = Path(source_path)
    if not path_obj.exists() or not path_obj.is_file():
        raise HTTPException(status_code=404, detail="Source file not found on server")

    media_type = None
    suffix = path_obj.suffix.lower()
    if suffix == ".pdf":
        media_type = "application/pdf"

    return FileResponse(
        path=str(path_obj),
        media_type=media_type,
        filename=source_name,
    )


@app.post("/api/query")
def query_rag(req: QueryRequest):
    user_pipeline = get_user_pipeline(req.user_id, req.chat_id)
    result = user_pipeline["rag_generator"].generate_response(
        query=req.query,
        top_k=req.top_k,
    )
    return {
        "answer": _adapt_image_only_answer(result.response, result.sources_used),
        "sources": result.sources_used,
        "retrieval_count": result.retrieval_count,
    }


@app.post("/api/query/stream")
async def query_stream(req: QueryRequest):
    """
    Streaming version: sends text character by character for typewriter effect with TTS
    """
    if not OPENAI_API_KEY and not GEMINI_API_KEY:
        raise HTTPException(status_code=400, detail="No LLM key configured. Set GEMINI_API_KEY or OPENAI_API_KEY")

    logger.info(f"Query streaming request: {req.query[:50]}..., user: {req.user_id}")
    
    try:
        # Get user pipeline for RAG
        user_pipeline = get_user_pipeline(req.user_id, req.chat_id)
        
        # Generate RAG response
        rag_result = user_pipeline["rag_generator"].generate_response(
            query=req.query,
            top_k=req.top_k,
        )
        
        answer_text = _adapt_image_only_answer(rag_result.response, rag_result.sources_used)
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
    user_pipeline = get_user_pipeline(req.user_id, req.chat_id)
    result = user_pipeline["rag_generator"].generate_summary(
        max_chunks=req.max_chunks,
        summary_length=req.summary_length,
    )
    return {
        "summary": result.response,
        "sources": result.sources_used,
        "retrieval_count": result.retrieval_count,
    }


def _clean_llm_json(raw: str) -> str:
    """Strip markdown code fences and whitespace from LLM JSON output."""
    text = raw.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()


@app.post("/api/generate/quiz")
def generate_quiz(req: LearningAidRequest):
    user_pipeline = get_user_pipeline(req.user_id, req.chat_id)
    result = user_pipeline["rag_generator"].generate_quiz(
        num_questions=req.num_questions,
        max_chunks=req.max_chunks,
    )
    cleaned = _clean_llm_json(result.response)
    return {
        "content": cleaned,
        "sources": result.sources_used,
        "retrieval_count": result.retrieval_count,
    }


@app.post("/api/generate/flashcards")
def generate_flashcards(req: LearningAidRequest):
    user_pipeline = get_user_pipeline(req.user_id, req.chat_id)
    result = user_pipeline["rag_generator"].generate_flashcards(
        num_cards=req.num_cards,
        max_chunks=req.max_chunks,
    )
    cleaned = _clean_llm_json(result.response)
    return {
        "content": cleaned,
        "sources": result.sources_used,
        "retrieval_count": result.retrieval_count,
    }


@app.post("/api/generate/mindmap")
def generate_mindmap(req: LearningAidRequest):
    user_pipeline = get_user_pipeline(req.user_id, req.chat_id)
    result = user_pipeline["rag_generator"].generate_mindmap(
        max_chunks=req.max_chunks,
        topic=req.topic,
        difficulty_level=req.difficulty_level,
        learning_objective=req.learning_objective,
    )
    cleaned = _clean_llm_json(result.response)
    return {
        "content": cleaned,
        "sources": result.sources_used,
        "retrieval_count": result.retrieval_count,
    }


@app.post("/api/generate/summary")
def generate_summary_aid(req: LearningAidRequest):
    user_pipeline = get_user_pipeline(req.user_id, req.chat_id)
    result = user_pipeline["rag_generator"].generate_summary(
        max_chunks=req.max_chunks,
        summary_length="medium",
    )
    return {
        "content": result.response,
        "sources": result.sources_used,
        "retrieval_count": result.retrieval_count,
    }


@app.post("/api/learning/scores")
def submit_learning_score(req: LearningScoreSubmissionRequest):
    if not req.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    if req.total_questions <= 0:
        raise HTTPException(status_code=400, detail="total_questions must be > 0")
    if req.correct_answers < 0:
        raise HTTPException(status_code=400, detail="correct_answers must be >= 0")

    chat_scope = normalize_chat_id(req.chat_id)
    resolved_course_id = (req.course_id or chat_scope).strip() or chat_scope
    resolved_course_name = (req.course_name or "").strip() or resolved_course_id

    try:
        score_row = save_learning_score(
            user_id=req.user_id,
            chat_id=chat_scope,
            course_id=resolved_course_id,
            course_name=resolved_course_name,
            total_questions=req.total_questions,
            correct_answers=req.correct_answers,
            feedback=req.feedback,
        )
        return {
            "status": "ok",
            "score": score_row,
        }
    except Exception as e:
        logger.error(f"Failed to submit learning score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/learning/scores")
def get_learning_scores(user_id: str):
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    try:
        return fetch_learning_score_summary(user_id)
    except Exception as e:
        logger.error(f"Failed to fetch learning scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))




# Conversation History Endpoints
class ConversationMessage(BaseModel):
    user_id: str
    chat_id: str = "default"
    role: str  # "user" or "assistant"
    content: str
    sources: Optional[List[dict]] = None


@app.post("/api/conversations/save")
def save_conversation_message(msg: ConversationMessage):
    """Save a conversation message to the database."""
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database unavailable"}
    
    chat_scope = normalize_chat_id(msg.chat_id)

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO conversation_history (user_id, chat_id, role, content, sources)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, created_at;
                    """,
                    (
                        msg.user_id,
                        chat_scope,
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
def get_conversation_history(user_id: str, chat_id: str = "default", limit: int = 100):
    """Retrieve conversation history for a user."""
    conn = get_db_connection()
    if not conn:
        return []

    chat_scope = normalize_chat_id(chat_id)
    
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, role, content, sources, created_at
                    FROM conversation_history
                    WHERE user_id = %s AND chat_id = %s
                    ORDER BY created_at ASC
                    LIMIT %s;
                    """,
                    (user_id, chat_scope, limit),
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
def delete_conversation_history(
    user_id: str,
    chat_id: Optional[str] = None,
    older_than_days: Optional[int] = None,
):
    """Delete conversation history for a user. Optionally delete messages older than N days."""
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database unavailable"}

    chat_scope = normalize_chat_id(chat_id) if chat_id else None
    
    try:
        with conn:
            with conn.cursor() as cur:
                if older_than_days:
                    if chat_scope:
                        cur.execute(
                            """
                            DELETE FROM conversation_history
                            WHERE user_id = %s
                            AND chat_id = %s
                            AND created_at < NOW() - INTERVAL '%s days';
                            """,
                            (user_id, chat_scope, older_than_days),
                        )
                    else:
                        cur.execute(
                            """
                            DELETE FROM conversation_history
                            WHERE user_id = %s
                            AND created_at < NOW() - INTERVAL '%s days';
                            """,
                            (user_id, older_than_days),
                        )
                else:
                    if chat_scope:
                        cur.execute(
                            """
                            DELETE FROM conversation_history
                            WHERE user_id = %s AND chat_id = %s;
                            """,
                            (user_id, chat_scope),
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
