# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

FastWhisper is a recording-to-meeting-minutes service. It transcribes audio using faster-whisper, identifies speakers via pyannote, and generates structured meeting minutes using an LLM (Qwen/OpenAI-compatible).

## Common Commands

```bash
# Use the dev script (recommended)
./dev.sh all        # Start all services (backend + frontend)
./dev.sh backend    # Start backend only
./dev.sh frontend   # Start frontend only
./dev.sh stop       # Stop all services
./dev.sh status     # Check service status

# Docker deployment
docker-compose up -d

# Manual backend startup
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Manual frontend startup
cd frontend && npm install && npm run dev

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

# Run tests
pytest
```

## Architecture

### Backend Data Flow
1. **Upload** → Audio file saved to `storage/uploads/`
2. **Whisper Transcription** → Speech-to-text with timestamps
3. **Speaker Diarization** → Identify who spoke when (pyannote)
4. **Alignment** → Match transcripts to speakers
5. **LLM Generation** → Produce structured meeting minutes

### Frontend Stack
- **Vue 3** + Vite + TailwindCSS
- **Pinia** for state management
- **Vue Router** for navigation
- Dark theme with card-based UI

### Key Backend Services (singleton pattern)

| Service | File | Purpose |
|---------|------|---------|
| `WhisperService` | `app/services/whisper_service.py` | Audio transcription using faster-whisper |
| `DiarizationService` | `app/services/diarization_service.py` | Speaker separation using pyannote |
| `LLMService` | `app/services/llm_service.py` | Meeting minutes generation via OpenAI-compatible API |
| `TranscriptAligner` | `app/services/aligner_service.py` | Aligns transcript segments with speaker segments |
| `TaskProcessor` | `app/workers/processor.py` | Background worker that processes pending tasks |

### Frontend Structure

| Path | Purpose |
|------|---------|
| `frontend/src/api/index.js` | Axios instance and API endpoints |
| `frontend/src/stores/task.js` | Pinia store for task state |
| `frontend/src/components/` | Reusable UI components |
| `frontend/src/views/` | Page-level components |

### Database Models (`app/models/task.py`)

- **Task**: Main entity tracking processing status, progress, and configuration
- **TranscriptSegment**: Individual speech segments with speaker info
- **MeetingMinutes**: Generated summary, key points, action items, decisions

### API Structure

- Entry point: `app/main.py` (FastAPI app with lifespan management)
- Routes: `app/api/v1/tasks.py` (task CRUD, progress, minutes endpoints)
- Auth: Token-based via `API_TOKEN` environment variable

## Configuration

Environment variables are defined in `app/core/config.py`. Key settings:

- `WHISPER_MODEL`: Model size (tiny/base/small/medium/large-v3)
- `WHISPER_DEVICE`: cuda/cpu
- `HUGGINGFACE_TOKEN`: Required for pyannote diarization model
- `LLM_PROVIDER`: qwen/openai
- `MAX_CONCURRENT_TASKS`: Worker concurrency limit

Frontend config (`frontend/.env`):
- `VITE_API_TOKEN`: API authentication token

## GPU Requirements

The service requires NVIDIA GPU for optimal performance. Docker Compose is configured with GPU support. For CPU-only, set `WHISPER_DEVICE=cpu`.