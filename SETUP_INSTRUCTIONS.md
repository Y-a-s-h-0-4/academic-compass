# Academic Compass - Setup Instructions

A course assistant application that helps students with coursework using RAG (Retrieval-Augmented Generation), vector embeddings, and text-to-speech.

## Prerequisites

- **Node.js**: v18+ (with npm or bun)
- **Python**: 3.13+
- **PostgreSQL**: Database (Supabase recommended)
- **Git**: For cloning the repository

## Quick Start for Your Friend

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd academic-compass
```

### Step 2: Setup Environment Variables

Create two `.env` files:

#### File 1: Root `.env` (for frontend)
```
# Frontend - Vite config
VITE_NOTEBOOK_API_URL=http://localhost:8000
```

#### File 2: `notebook-lm-clone/.env` (for backend)
```
# Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# Firecrawl (for web scraping)
FIRECRAWL_API_KEY=your_firecrawl_api_key_here

# Database (PostgreSQL via Supabase)
SUPABASE_DB_URL=your_database_url_here
# Format: postgresql://user:password@host:port/database

# Optional: Alternative database URL
DATABASE_URL=postgresql://user:password@host:port/database
```

### Step 3: Install Dependencies

#### Frontend (Node.js)
```bash
npm install
# or if using bun
bun install
```

#### Backend (Python)
```bash
cd notebook-lm-clone
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Step 4: Setup Database (PostgreSQL)

Ensure you have a PostgreSQL database running. The application will automatically create tables on first run.

If using Supabase:
1. Create a Supabase account
2. Create a new project
3. Copy the connection string
4. Add it to your `.env` as `SUPABASE_DB_URL`

### Step 5: Run the Application

#### Terminal 1: Start Backend (Python)
```bash
cd notebook-lm-clone
source venv/bin/activate  # or venv\Scripts\activate on Windows
python -m uvicorn api.main:app --reload --port 8000
```

The backend will start at: `http://localhost:8000`

#### Terminal 2: Start Frontend (Node.js)
```bash
npm run dev
# or
bun run dev
```

The frontend will start at: `http://localhost:5173`

### Step 6: Open in Browser

Visit: `http://localhost:5173`

## Features

✅ **Upload Documents**: PDF, web pages, or text notes
✅ **Vector Search**: ChromaDB for semantic search with embeddings
✅ **RAG System**: Retrieval-Augmented Generation with Gemini-1.5-Flash
✅ **Voice Input**: Speech-to-text with auto-submit (2 sec silence)
✅ **Text-to-Speech**: Read responses aloud with Edge-TTS
✅ **Streaming Responses**: Typewriter effect for real-time feedback
✅ **Conversation History**: Persisted in PostgreSQL
✅ **Citation Tracking**: Automatic citation references

## Project Structure

```
academic-compass/
├── src/                           # Frontend (React + TypeScript)
│   ├── app/                      # App routes
│   ├── components/               # UI components (shadcn/ui)
│   ├── features/                 # Feature modules
│   ├── lib/                      # API client
│   └── context/                  # React context
├── notebook-lm-clone/            # Backend (FastAPI + Python)
│   ├── api/                      # API endpoints
│   ├── src/
│   │   ├── document_processing/  # PDF/document parsing
│   │   ├── embeddings/           # FastEmbed integration
│   │   ├── generation/           # RAG pipeline
│   │   ├── vector_database/      # ChromaDB wrapper
│   │   ├── web_scraping/         # Firecrawl integration
│   │   └── audio_processing/     # Edge-TTS for voice
│   └── tests/                    # Test files
├── .gitignore
├── package.json
└── SETUP_INSTRUCTIONS.md
```

## Technology Stack

### Frontend
- React 18 + TypeScript
- Vite (build tool)
- TailwindCSS (styling)
- shadcn/ui (components)
- Clerk (authentication)
- Web Speech API (voice input)

### Backend
- FastAPI (Python web framework)
- PostgreSQL (conversation history)
- ChromaDB (vector database)
- Google Gemini 1.5 Flash (LLM)
- FastEmbed (embeddings: BAAI/bge-small-en-v1.5)
- Edge-TTS (text-to-speech)
- Firecrawl (web scraping)
- PyMuPDF (PDF processing)

## Common Issues & Solutions

### Port 8000 Already in Use
```bash
# Find and kill process on port 8000
# On Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# On macOS/Linux:
lsof -i :8000
kill -9 <PID>
```

### Python Virtual Environment Issues
```bash
# Recreate venv
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Database Connection Error
- Verify `SUPABASE_DB_URL` is correct
- Check database is running
- Ensure credentials have proper permissions

### Missing Dependencies
```bash
# Reinstall frontend
npm install

# Reinstall backend
pip install -r requirements.txt --upgrade
```

## API Endpoints

- `POST /api/ingest` - Ingest documents
- `GET /api/sources/{user_id}` - List user sources
- `POST /api/query` - Query documents
- `POST /api/query/stream` - Streaming query with TTS
- `POST /api/conversations/save` - Save message
- `GET /api/conversations/{user_id}` - Get conversation history

## How to Use

1. **Sign In**: Use Clerk authentication
2. **Upload Sources**: Add PDFs, web pages, or notes
3. **Ask Questions**: Type or use voice input
4. **Get Answers**: Streaming responses with citations
5. **Listen**: Audio playback automatically starts

## Troubleshooting

### Frontend Won't Load
- Check `VITE_NOTEBOOK_API_URL` is set correctly
- Verify backend is running on port 8000

### Backend Won't Start
- Check all environment variables are set
- Verify Python 3.13+ is installed
- Check database connection

### Voice Input Not Working
- Use Chrome, Edge, or Safari
- Check microphone permissions
- Ensure secure context (HTTPS or localhost)

## Development

### Run Backend Tests
```bash
cd notebook-lm-clone
pytest tests/
```

### Build Frontend
```bash
npm run build
```

## Deployment

See deployment docs for production setup (Docker, Vercel, Railway, etc.)

## Support

For issues or questions, check the documentation or contact the development team.

---

**Created**: January 2026
**Status**: In Active Development
