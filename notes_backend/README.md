# Notes Backend (FastAPI)

A simple Notes API allowing users to create, view, edit, and delete notes. Built with FastAPI and SQLite (via SQLAlchemy).

## Features
- CRUD for notes:
  - POST /notes
  - GET /notes
  - GET /notes/{id}
  - PUT /notes/{id}
  - PATCH /notes/{id}
  - DELETE /notes/{id}
- SQLite persistence stored at `notes_backend/data/notes.db`
- OpenAPI docs at `/docs`
- CORS enabled for development
- Basic validation via Pydantic models
- DB initialization at startup

## Installation

Ensure Python 3.10+ is available.

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running

From the `notes_backend` directory:

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 3001
```

Open API docs at:
- http://localhost:3001/docs

## Models

- Note:
  - id: integer
  - title: string (1..255)
  - content: string (min 1)
  - created_at: datetime
  - updated_at: datetime

## Development Notes

- Tables are created automatically on startup.
- This service uses an on-disk SQLite DB for convenience. For production, use a managed RDBMS.
