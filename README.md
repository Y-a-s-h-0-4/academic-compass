# Academic Compass – Consolidated Guide

## Overview
Modern AI-powered learning app with Vite/React frontend and FastAPI backend (notebook-lm clone) using Google Gemini, ChromaDB embeddings, and Supabase Postgres for persistence.

## Project Structure
- frontend: `src/` (Vite/React, Tailwind, shadcn)
- backend: `notebook-lm-clone/` (FastAPI, RAG, podcast TTS)
- public assets: `public/`
- tooling: ESLint/Tailwind/Vite configs
- lockfiles: `package-lock.json`, `bun.lockb`, `uv.lock`, `pyproject.toml`

## Prerequisites
- Node 18+ and npm
- Python 3.10+ (uses virtual env `.venv` under project root)
- Google Gemini API key; Supabase Postgres URL (with SSL) if using persistence

## Environment
Create `.env` at repo root for frontend and `.env` inside `notebook-lm-clone/` for backend.

Frontend `.env` example:
```
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
VITE_NOTEBOOK_API_URL=http://localhost:8000
```

Backend `.env` example (notebook-lm-clone/.env):
```
GEMINI_API_KEY=...
FIRECRAWL_API_KEY=...
ASSEMBLYAI_API_KEY=...
SUPABASE_DB_URL=postgresql://user:pass@host:5432/postgres
ZEP_API_KEY=...
```

## Install
Frontend:
```
npm install
```

Backend (in `notebook-lm-clone/`):
```
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
pip install fastapi uvicorn psycopg2-binary edge-tts
```

## Run
Start backend (from repo root):
```
$env:PYTHONPATH="C:\Projects\academic-compass\notebook-lm-clone"; cd notebook-lm-clone; ..\.venv\Scripts\python.exe api/main.py
```

Start frontend (new terminal at repo root):
```
npm run dev -- --host --port 3000
```

## Key Behaviors
- Conversation history is persisted per user in Postgres (`conversation_history` table).
- RAG queries scoped per user; sources stored in `notebooklm_sources`.
- Podcast generation works only for uploaded files (PDF/docs). Web URLs are rejected.
- Scroll: only the chat messages area scrolls; header/sidebar/input stay fixed.

## API Notes (backend)
- `POST /api/ingest` files or `web_url` with `user_id`
- `GET /api/sources?user_id=` list sources
- `POST /api/query` { query, user_id }
- `POST /api/summary` { user_id }
- `POST /api/podcast` { source_path, user_id } (files only)
- `POST /api/conversations/save` and `GET /api/conversations/{user_id}` for history

## Frontend Notes
- Auth via Clerk; userId passed to all API calls.
- Podcast dropdown filters out web sources.
- Tailwind + shadcn components; theme tokens via CSS variables.

## Testing & Dev
- Frontend: `npm run lint`
- Backend: add pytest in `notebook-lm-clone/tests/` (not configured yet)

## Housekeeping
- Generated markdowns and legacy docs were removed; this README is the single source.
- Keep `.env` files out of version control.
