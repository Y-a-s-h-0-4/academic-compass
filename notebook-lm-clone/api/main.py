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
session_feedback_reports_registry: Dict[str, List[dict]] = {}


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


def get_memory_session_feedback_reports_bucket(user_id: str) -> List[dict]:
    return session_feedback_reports_registry.setdefault(user_id, [])


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

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS learning_session_feedback_reports (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id TEXT NOT NULL,
                        chat_id TEXT NOT NULL DEFAULT 'default',
                        course_id TEXT,
                        course_name TEXT,
                        topic TEXT,
                        session_score DOUBLE PRECISION,
                        report JSONB NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_session_feedback_reports_user_time
                    ON learning_session_feedback_reports(user_id, created_at DESC);
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


def _safe_parse_json(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    if value is None or value == "":
        return fallback
    if isinstance(value, (dict, list, tuple, set)):
        return fallback
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _safe_int(value: Any, fallback: int = 0) -> int:
    if value is None or value == "":
        return fallback
    if isinstance(value, (dict, list, tuple, set)):
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _safe_text(value: Any, fallback: str = "") -> str:
    if isinstance(value, (dict, list, tuple, set)):
        return fallback
    text = str(value or "").strip()
    return text or fallback


def _extract_concept_tags(item: Dict[str, Any], topic_fallback: str) -> List[str]:
    tags: List[str] = []
    raw_tags = item.get("concept_tags")
    if isinstance(raw_tags, list):
        tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()]

    if not tags:
        concept_tested = _safe_text(item.get("concept_tested"), "")
        if concept_tested:
            tags = [concept_tested]

    if not tags:
        question_type = _safe_text(item.get("question_type"), "")
        if question_type:
            tags = [question_type]

    if not tags:
        tags = [topic_fallback]

    # Keep unique order
    seen: set = set()
    unique_tags: List[str] = []
    for tag in tags:
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_tags.append(tag)
    return unique_tags


def _coerce_question_item(raw_item: Dict[str, Any], index: int, topic_fallback: str) -> Dict[str, Any]:
    evaluation = raw_item.get("evaluation") if isinstance(raw_item.get("evaluation"), dict) else {}

    score = _safe_float(raw_item.get("score"), _safe_float(evaluation.get("score"), 0.0))
    max_score = _safe_float(raw_item.get("max_score"), _safe_float(evaluation.get("max_score"), 1.0))
    if max_score <= 0:
        max_score = 1.0
    score = max(0.0, min(score, max_score))

    correct_points = raw_item.get("correct_points") if isinstance(raw_item.get("correct_points"), list) else evaluation.get("correct_points")
    incorrect_points = raw_item.get("incorrect_points") if isinstance(raw_item.get("incorrect_points"), list) else evaluation.get("incorrect_points")
    missing_points = raw_item.get("missing_points") if isinstance(raw_item.get("missing_points"), list) else evaluation.get("missing_points")

    correct_points = [str(point).strip() for point in (correct_points or []) if str(point).strip()]
    incorrect_points = [str(point).strip() for point in (incorrect_points or []) if str(point).strip()]
    missing_points = [str(point).strip() for point in (missing_points or []) if str(point).strip()]

    if score == max_score:
        verdict = "fully_correct"
    elif score > 0:
        verdict = "partially_correct"
    else:
        verdict = "incorrect"

    return {
        "question_id": _safe_text(raw_item.get("question_id"), f"q{index + 1}"),
        "question": _safe_text(raw_item.get("question"), f"Question {index + 1}"),
        "question_type": _safe_text(raw_item.get("question_type"), "mcq"),
        "concept_tested": _safe_text(raw_item.get("concept_tested"), ""),
        "difficulty": _safe_text(raw_item.get("difficulty"), "mixed"),
        "student_answer": _safe_text(raw_item.get("student_answer"), ""),
        "reference_answer": _safe_text(raw_item.get("reference_answer"), ""),
        "score": score,
        "max_score": max_score,
        "correct_points": correct_points,
        "incorrect_points": incorrect_points,
        "missing_points": missing_points,
        "concept_tags": _extract_concept_tags(raw_item, topic_fallback),
        "evaluation": evaluation,
    }


def _aggregate_session_metrics(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    fully_correct_count = sum(1 for item in items if float(item.get("score") or 0) == float(item.get("max_score") or 0))
    partially_correct_count = sum(1 for item in items if 0 < float(item.get("score") or 0) < float(item.get("max_score") or 0))
    incorrect_count = sum(1 for item in items if float(item.get("score") or 0) == 0)

    total_score = round(sum(float(item.get("score") or 0) for item in items), 2)
    total_max_score = round(sum(float(item.get("max_score") or 0) for item in items), 2)
    overall_percentage = round((total_score / total_max_score) * 100, 2) if total_max_score > 0 else 0.0

    if overall_percentage >= 90:
        tier = "Excellent - Strong mastery demonstrated"
    elif overall_percentage >= 75:
        tier = "Good - Solid understanding with minor gaps"
    elif overall_percentage >= 50:
        tier = "Developing - Key concepts need reinforcement"
    else:
        tier = "Needs Attention - Foundational review recommended"

    return {
        "fully_correct_count": fully_correct_count,
        "partially_correct_count": partially_correct_count,
        "incorrect_count": incorrect_count,
        "total_score": total_score,
        "total_max_score": total_max_score,
        "overall_percentage": overall_percentage,
        "tier": tier,
    }


def _build_question_results_from_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    payload: List[Dict[str, Any]] = []
    for idx, item in enumerate(items):
        payload.append(
            {
                "question_index": idx + 1,
                "question": item.get("question", f"Question {idx + 1}"),
                "what_you_got_right": item.get("correct_points", []),
                "what_was_incorrect": [
                    {
                        "student_claim": point,
                        "correction": "Re-check this claim against the reference answer and concept rule.",
                    }
                    for point in item.get("incorrect_points", [])
                ],
                "what_you_missed": item.get("missing_points", []),
                "question_tip": _safe_text(
                    item.get("evaluation", {}).get("study_tip") if isinstance(item.get("evaluation"), dict) else "",
                    "Review this concept using one worked example and then retry a similar question.",
                ),
            }
        )
    return payload


def _build_concept_rollup(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    rollup: Dict[str, Dict[str, Any]] = {}
    for item in items:
        for tag in item.get("concept_tags", []):
            node = rollup.setdefault(
                tag,
                {
                    "concept": tag,
                    "score": 0.0,
                    "max_score": 0.0,
                    "correct_points": [],
                    "incorrect_points": [],
                    "missing_points": [],
                    "question_refs": [],
                },
            )
            node["score"] += float(item.get("score") or 0)
            node["max_score"] += float(item.get("max_score") or 0)
            node["correct_points"].extend(item.get("correct_points", []))
            node["incorrect_points"].extend(item.get("incorrect_points", []))
            node["missing_points"].extend(item.get("missing_points", []))
            node["question_refs"].append(item.get("question_id", "q?"))
    return rollup


def _fallback_strength_areas(concept_rollup: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    strengths: List[Dict[str, Any]] = []
    for concept, node in concept_rollup.items():
        max_score = float(node.get("max_score") or 0)
        if max_score <= 0:
            continue
        pct = (float(node.get("score") or 0) / max_score) * 100
        if pct >= 75:
            strengths.append(
                {
                    "concept": concept,
                    "evidence": f"Strong performance in {', '.join(node.get('question_refs', []))}",
                    "acknowledgement": "You demonstrated clear understanding of this concept.",
                }
            )

    if strengths:
        return strengths

    # Emerging strengths fallback from partial understanding.
    candidates = []
    for concept, node in concept_rollup.items():
        max_score = float(node.get("max_score") or 0)
        if max_score <= 0:
            continue
        pct = (float(node.get("score") or 0) / max_score) * 100
        if pct > 0 or node.get("correct_points"):
            candidates.append((pct, concept, node))

    candidates.sort(key=lambda item: item[0], reverse=True)
    for _, concept, node in candidates[:2]:
        strengths.append(
            {
                "concept": concept,
                "evidence": f"Emerging performance in {', '.join(node.get('question_refs', []))}",
                "acknowledgement": "You are showing partial understanding that can become a strong area with focused practice.",
            }
        )
    if not strengths:
        strengths.append(
            {
                "concept": "Emerging Strengths",
                "evidence": "No concept reached consistent mastery in this session.",
                "acknowledgement": "That is okay - your responses still reveal a starting base to build on through targeted practice.",
            }
        )
    return strengths


def _fallback_weak_areas(concept_rollup: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    weak: List[Dict[str, Any]] = []
    for concept, node in concept_rollup.items():
        max_score = float(node.get("max_score") or 0)
        if max_score <= 0:
            continue
        pct = (float(node.get("score") or 0) / max_score) * 100
        incorrect_points = node.get("incorrect_points", [])
        missing_points = node.get("missing_points", [])
        if pct < 60 or incorrect_points or missing_points:
            severity = "Critical Gap" if pct < 40 else "Moderate Gap" if pct < 60 else "Minor Gap"
            weak.append(
                {
                    "concept": concept,
                    "description": "; ".join((incorrect_points + missing_points)[:2]) or "This concept needs targeted reinforcement.",
                    "exposed_by": ", ".join(node.get("question_refs", [])),
                    "significance": "This concept influences performance across related questions.",
                    "severity": severity,
                }
            )

    if weak:
        return weak

    # No obvious weak areas from scores: infer from recurring missing/incorrect phrases.
    return [
        {
            "concept": "Concept Reinforcement",
            "description": "Review nuanced differences between related concepts to avoid future confusion.",
            "exposed_by": "Session-wide pattern",
            "significance": "Improves reliability under exam-like pressure.",
            "severity": "Minor Gap",
        }
    ]


def _fallback_improvement_plan(weak_areas: List[Dict[str, Any]], topic_fallback: str) -> List[Dict[str, Any]]:
    plan: List[Dict[str, Any]] = []
    for area in weak_areas[:5]:
        concept = _safe_text(area.get("concept"), topic_fallback)
        severity = _safe_text(area.get("severity"), "Moderate Gap")
        difficulty = "hard" if severity == "Critical Gap" else "medium"
        plan.append(
            {
                "concept": concept,
                "study_suggestion": f"Re-study the core rules and edge cases for {concept}, then apply them in a worked example.",
                "activity_type": "quiz",
                "difficulty_level": "Hard" if difficulty == "hard" else "Medium",
                "resource_type": "targeted practice",
                "system_action": {
                    "action_type": "quiz",
                    "label": f"Generate {concept} Quiz",
                    "settings": {
                        "topic": concept,
                        "difficulty": difficulty,
                    },
                },
            }
        )
    return plan


def _calculate_learning_trend(user_id: str, course_id: str, current_score: float) -> str:
    conn = get_db_connection()
    if not conn:
        attempts = [
            row for row in get_memory_learning_attempts_bucket(user_id)
            if str(row.get("course_id") or "") == str(course_id or "")
        ]
        previous = float(attempts[-1].get("score") or 0) if attempts else None
    else:
        previous = None
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT score
                        FROM learning_quiz_attempts
                        WHERE user_id = %s AND course_id = %s
                        ORDER BY created_at DESC
                        LIMIT 1;
                        """,
                        (user_id, course_id),
                    )
                    row = cur.fetchone()
                    if row:
                        previous = float(row[0] or 0)
        except Exception as e:
            logger.error(f"Failed to calculate learning trend from DB: {e}")
        finally:
            conn.close()

    if previous is None:
        return "stable"

    delta = float(current_score) - float(previous)
    if delta >= 2.0:
        return "improved"
    if delta <= -2.0:
        return "declined"
    return "stable"


def _normalize_question_result_item(item: Dict[str, Any], index: int) -> Dict[str, Any]:
    question = str(item.get("question") or f"Question {index + 1}").strip() or f"Question {index + 1}"
    got_right = item.get("what_you_got_right")
    was_incorrect = item.get("what_was_incorrect")
    missed = item.get("what_you_missed")
    question_tip = str(item.get("question_tip") or "Review the core concept and solve one similar problem today.").strip()

    normalized_incorrect: List[Dict[str, str]] = []
    if isinstance(was_incorrect, list):
        for entry in was_incorrect:
            if isinstance(entry, dict):
                claim = str(entry.get("student_claim") or "").strip()
                correction = str(entry.get("correction") or "").strip()
                if claim or correction:
                    normalized_incorrect.append({
                        "student_claim": claim or "Needs correction",
                        "correction": correction or "Refer to the concept explanation.",
                    })
            elif isinstance(entry, str) and entry.strip():
                normalized_incorrect.append({
                    "student_claim": entry.strip(),
                    "correction": "Refer to the concept explanation.",
                })

    return {
        "question_index": int(item.get("question_index") or index + 1),
        "question": question,
        "what_you_got_right": [str(x).strip() for x in (got_right if isinstance(got_right, list) else []) if str(x).strip()],
        "what_was_incorrect": normalized_incorrect,
        "what_you_missed": [str(x).strip() for x in (missed if isinstance(missed, list) else []) if str(x).strip()],
        "question_tip": question_tip or "Review the core concept and solve one similar problem today.",
    }


def _build_fallback_session_feedback_report(
    session_questions: List[Dict[str, Any]],
    overall_score: float,
    learning_trend: str,
) -> Dict[str, Any]:
    normalized_results = []
    for idx, item in enumerate(session_questions):
        eval_obj = item.get("evaluation") if isinstance(item.get("evaluation"), dict) else {}
        correct_points = eval_obj.get("correct_points") if isinstance(eval_obj.get("correct_points"), list) else []
        incorrect_points = eval_obj.get("incorrect_points") if isinstance(eval_obj.get("incorrect_points"), list) else []
        missing_points = eval_obj.get("missing_points") if isinstance(eval_obj.get("missing_points"), list) else []
        tip = str(eval_obj.get("study_tip") or "Practice this concept with one applied example.").strip()

        normalized_results.append(
            {
                "question_index": idx + 1,
                "question": str(item.get("question") or f"Question {idx + 1}"),
                "what_you_got_right": [str(x) for x in correct_points if str(x).strip()],
                "what_was_incorrect": [
                    {
                        "student_claim": str(x),
                        "correction": "Re-check the underlying concept and compare with the reference answer.",
                    }
                    for x in incorrect_points if str(x).strip()
                ],
                "what_you_missed": [str(x) for x in missing_points if str(x).strip()],
                "question_tip": tip or "Practice this concept with one applied example.",
            }
        )

    return {
        "question_results": normalized_results,
        "performance_summary": {
            "overall_score": round(overall_score, 2),
            "overall_percentage": round(overall_score, 2),
            "fully_correct_count": 0,
            "partially_correct_count": 0,
            "incorrect_count": len(session_questions),
            "estimated_conceptual_coverage": "Moderate",
            "one_sentence_assessment": "Session completed. Review weak concepts and retry focused practice.",
        },
        "strength_areas": [],
        "weak_areas": [],
        "improvement_plan": [
            {
                "concept": "Core topic review",
                "study_suggestion": "Generate a focused medium-difficulty quiz on your weakest concept.",
                "activity_type": "quiz",
                "difficulty_level": "Medium",
                "resource_type": "topic practice",
                "system_action": {
                    "action_type": "quiz",
                    "label": "Practice weakest concept",
                    "settings": {
                        "difficulty": "medium",
                    },
                },
            }
        ],
        "next_step": "Attempt another short quiz and compare your score trend.",
        "learning_trend": learning_trend,
    }


def save_session_feedback_report_record(
    user_id: str,
    chat_id: str,
    course_id: Optional[str],
    course_name: Optional[str],
    topic: Optional[str],
    report: Dict[str, Any],
    session_score: Optional[float] = None,
) -> Dict[str, Any]:
    chat_scope = normalize_chat_id(chat_id)
    payload = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "chat_id": chat_scope,
        "course_id": course_id,
        "course_name": course_name,
        "topic": topic,
        "session_score": session_score,
        "report": report,
    }

    conn = get_db_connection()
    if not conn:
        get_memory_session_feedback_reports_bucket(user_id).append(payload)
        return payload

    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO learning_session_feedback_reports (
                        id, user_id, chat_id, course_id, course_name, topic, session_score, report
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, chat_id, course_id, course_name, topic, session_score, report, created_at;
                    """,
                    (
                        payload["id"],
                        user_id,
                        chat_scope,
                        course_id,
                        course_name,
                        topic,
                        session_score,
                        json.dumps(report),
                    ),
                )
                row = cur.fetchone()
                return dict(row) if row else payload
    finally:
        conn.close()


def fetch_session_feedback_reports(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    if not conn:
        bucket = get_memory_session_feedback_reports_bucket(user_id)
        return list(reversed(bucket[-max(1, int(limit)):]))

    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, user_id, chat_id, course_id, course_name, topic, session_score, report, created_at
                    FROM learning_session_feedback_reports
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s;
                    """,
                    (user_id, max(1, int(limit))),
                )
                return [dict(row) for row in cur.fetchall()]
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
    rag_context: Optional[str] = None
    quiz_difficulty: str = "Mixed"
    question_types: Optional[List[str]] = None
    topic_focus: Optional[str] = None
    existing_questions: Optional[List[str]] = None
    previous_questions: Optional[List[str]] = None
    card_mode: str = "Question->Answer"
    existing_cards: Optional[List[str]] = None


class LearningScoreSubmissionRequest(BaseModel):
    user_id: str
    chat_id: str = "default"
    course_id: Optional[str] = None
    course_name: Optional[str] = None
    total_questions: int
    correct_answers: int
    feedback: Optional[str] = None


class SessionQuestionPayload(BaseModel):
    question: str
    question_type: Optional[str] = None
    reference_answer: str
    student_answer: str
    evaluation: Dict[str, Any] = {}


class SessionFeedbackReportRequest(BaseModel):
    user_id: str
    chat_id: str = "default"
    course_id: Optional[str] = None
    course_name: Optional[str] = None
    topic: Optional[str] = None
    retrieved_context_chunks: List[str] = []
    session_questions: List[SessionQuestionPayload]
    previous_score: Optional[float] = None


class SaveSessionFeedbackReportRequest(BaseModel):
    user_id: str
    chat_id: str = "default"
    course_id: Optional[str] = None
    course_name: Optional[str] = None
    topic: Optional[str] = None
    report: Dict[str, Any]
    session_score: Optional[float] = None


# Shared components and per-user pipelines
doc_processor = DocumentProcessor()
embedding_generator = EmbeddingGenerator()
web_scraper = WebScraper(FIRECRAWL_API_KEY) if FIRECRAWL_API_KEY else None

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
    result = user_pipeline["rag_generator"].generate_quiz_from_config({
        "number_of_questions": req.num_questions,
        "max_chunks": req.max_chunks,
        "difficulty": req.quiz_difficulty,
        "question_types": req.question_types,
        "topic": req.topic_focus or req.topic,
        "rag_context": req.rag_context,
        "previous_questions": req.previous_questions or req.existing_questions,
    })
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
        card_mode=req.card_mode,
        topic_focus=req.topic_focus,
        existing_cards=req.existing_cards,
    )
    cleaned = _clean_llm_json(result.response)
    return {
        "content": cleaned,
        "sources": result.sources_used,
        "retrieval_count": result.retrieval_count,
    }


@app.post("/api/generate/mindmap")
def generate_mindmap(req: LearningAidRequest):
    try:
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
    except Exception as e:
        logger.exception("Error in mindmap generation")
        fallback = {
            "id": "root",
            "label": req.topic or "Mind Map",
            "children": [],
        }
        return {
            "content": json.dumps(fallback),
            "sources": [],
            "retrieval_count": 0,
            "error": str(e),
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


@app.post("/api/learning/session-feedback-report")
def generate_session_feedback_report(req: SessionFeedbackReportRequest):
    if not req.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    if not req.session_questions:
        raise HTTPException(status_code=400, detail="session_questions is required")

    chat_scope = normalize_chat_id(req.chat_id)
    resolved_course_id = (req.course_id or chat_scope).strip() or chat_scope
    resolved_course_name = (req.course_name or "").strip() or resolved_course_id
    resolved_topic = (req.topic or resolved_course_name).strip() or resolved_course_name

    question_items = [
        _coerce_question_item(item.model_dump(), index, resolved_topic)
        for index, item in enumerate(req.session_questions)
    ]
    metrics = _aggregate_session_metrics(question_items)
    learning_trend = _calculate_learning_trend(req.user_id, resolved_course_id, float(metrics["overall_percentage"]))

    llm_payload = {
        "topic": resolved_topic,
        "course_name": resolved_course_name,
        "difficulty_mix": {
            "easy": sum(1 for item in question_items if _safe_text(item.get("difficulty")).lower() == "easy"),
            "medium": sum(1 for item in question_items if _safe_text(item.get("difficulty")).lower() == "medium"),
            "hard": sum(1 for item in question_items if _safe_text(item.get("difficulty")).lower() == "hard"),
            "mixed": sum(1 for item in question_items if _safe_text(item.get("difficulty")).lower() == "mixed"),
        },
        "metrics": metrics,
        "question_evaluations": question_items,
    }
    logger.info("Evaluation Payload: %s", json.dumps(llm_payload)[:8000])

    parsed: Dict[str, Any] = {}
    try:
        user_pipeline = get_user_pipeline(req.user_id, req.chat_id)
        llm_result = user_pipeline["rag_generator"].generate_session_feedback_report(
            session_questions=question_items,
            retrieved_context_chunks=req.retrieved_context_chunks,
            topic=resolved_topic,
            course_name=resolved_course_name,
            previous_score=req.previous_score,
        )
        response_text = _safe_text(getattr(llm_result, "response", ""), "")
        if response_text and not response_text.lower().startswith("error:"):
            cleaned = _clean_llm_json(response_text)
            parsed = _safe_parse_json(cleaned)
    except Exception as e:
        logger.error(f"Session feedback LLM generation failed, using fallback: {e}")
        parsed = {}

    if not parsed:
        parsed = _build_fallback_session_feedback_report(
            session_questions=question_items,
            overall_score=float(metrics["overall_percentage"]),
            learning_trend=learning_trend,
        )

    parsed["question_results"] = _build_question_results_from_items(question_items)

    concept_rollup = _build_concept_rollup(question_items)
    fallback_strengths = _fallback_strength_areas(concept_rollup)
    fallback_weaks = _fallback_weak_areas(concept_rollup)
    fallback_plan = _fallback_improvement_plan(fallback_weaks, resolved_topic)

    strength_areas = [item for item in (parsed.get("strength_areas") or []) if isinstance(item, dict)]
    weak_areas = [item for item in (parsed.get("weak_areas") or []) if isinstance(item, dict)]
    improvement_plan = [item for item in (parsed.get("improvement_plan") or []) if isinstance(item, dict)]

    if not strength_areas:
        strength_areas = fallback_strengths
    if not weak_areas:
        weak_areas = fallback_weaks
    if not improvement_plan:
        improvement_plan = fallback_plan

    parsed["performance_summary"] = {
        "overall_score": float(metrics["total_score"]),
        "total_score": float(metrics["total_score"]),
        "total_max_score": float(metrics["total_max_score"]),
        "overall_percentage": float(metrics["overall_percentage"]),
        "fully_correct_count": int(metrics["fully_correct_count"]),
        "partially_correct_count": int(metrics["partially_correct_count"]),
        "incorrect_count": int(metrics["incorrect_count"]),
        "estimated_conceptual_coverage": "High" if metrics["overall_percentage"] >= 75 else "Moderate" if metrics["overall_percentage"] >= 50 else "Low",
        "one_sentence_assessment": _safe_text(parsed.get("performance_summary", {}).get("one_sentence_assessment") if isinstance(parsed.get("performance_summary"), dict) else "", metrics["tier"]),
        "performance_tier": metrics["tier"],
    }

    parsed["strength_areas"] = strength_areas
    parsed["weak_areas"] = weak_areas
    parsed["improvement_plan"] = improvement_plan
    parsed["next_step"] = _safe_text(
        parsed.get("next_step"),
        f"Start with { _safe_text(weak_areas[0].get('concept') if weak_areas else resolved_topic, resolved_topic) } and run a targeted practice quiz.",
    )
    parsed["learning_trend"] = learning_trend

    return {
        "topic": resolved_topic,
        "course_name": resolved_course_name,
        "report": parsed,
    }


@app.post("/api/learning/session-feedback-report/save")
def save_session_feedback_report(req: SaveSessionFeedbackReportRequest):
    if not req.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    chat_scope = normalize_chat_id(req.chat_id)
    try:
        row = save_session_feedback_report_record(
            user_id=req.user_id,
            chat_id=chat_scope,
            course_id=req.course_id,
            course_name=req.course_name,
            topic=req.topic,
            report=req.report,
            session_score=req.session_score,
        )
        return {
            "status": "ok",
            "report": row,
        }
    except Exception as e:
        logger.error(f"Failed to save session feedback report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/learning/session-feedback-reports")
def get_session_feedback_reports(user_id: str, limit: int = 10):
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    try:
        rows = fetch_session_feedback_reports(user_id=user_id, limit=limit)
        return {"reports": rows}
    except Exception as e:
        logger.error(f"Failed to fetch session feedback reports: {e}")
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
