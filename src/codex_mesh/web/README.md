# CodexMesh Web Module

This module provides the "Control Plane" for CodexMesh — a central dashboard for project management, file browsing, and AI-assisted code review.

## Purpose and Responsibilities
- **Dashboard**: Visualize project indexing status and progress.
- **Project Management**: Connect to different projects dynamically.
- **File Browser**: Interactive navigation of the connected codebase.
- **AI Reviewer**: Chat interface with a Gemini-powered coding assistant.
- **Chat Management**: CRUD for chat threads (create, rename, clone, delete) and messages.
- **Persistence**: Chat history is stored in a local SQLite database (`chats.sqlite`) for cross-session memory.

## Directory Structure
- `frontend/`: React + TypeScript + Tailwind source code.
- `static/`: Static assets. `static/dist` contains the production build.
- `app.py`: FastAPI application factory.
- `routes.py`: API endpoints definition.
- `server.py`: Entry point for running the web server.

## Installation and Activation
The web interface requires the `web` extra:
```bash
uv sync --extra web
```

To run the web server:
```bash
uv run python -m codex_mesh.web.server
```

## Frontend Build
The web UI is a React application. Before the first run or after changes, it must be built:
```bash
cd src/codex_mesh/web/frontend
npm install
npm run build
```
The build artifacts will be placed in `src/codex_mesh/web/static/dist`.

## Configuration
- **Host**: `0.0.0.0` (default)
- **Port**: `8000` (default)
- **CORS**: Enabled for all origins (`*`) by default for local development.

## Dependencies
- **Backend**: `fastapi`, `uvicorn`, `sse-starlette`
- **Frontend**: `react`, `typescript`, `tailwind`, `vite`, `lucide-react`
