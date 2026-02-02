# CodexMesh Frontend

React-based Single Page Application (SPA) for the CodexMesh Control Plane.

## Purpose
Provides a modern, responsive UI for interacting with CodexMesh APIs.

## Tech Stack
- **React 18**
- **TypeScript**
- **Tailwind CSS**
- **Vite** (Build tool & dev server)
- **Lucide React** (Icons)

## Development
To start the development server with hot reload:
1. Ensure the CodexMesh backend is running on `http://localhost:8000`.
2. Install dependencies: `npm install`
3. Start dev server: `npm run dev`
4. Access at `http://localhost:5173`

The dev server is configured to proxy `/api` and `/api/v1/events` (SSE) requests to the backend.

## Production Build
To create a production build:
```bash
npm run build
```
The build artifacts are output to `../static/dist` so they can be served by the FastAPI backend.

## Structure
- `src/api/`: API client, types, and SSE hooks.
- `src/components/`: React components (Cards, Layout, UI primitives).
- `src/App.tsx`: Main application component with Context Provider.
- `src/main.tsx`: Application entry point.
