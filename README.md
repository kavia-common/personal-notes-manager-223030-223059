# personal-notes-manager-223030-223059

This workspace contains the Notes Backend built with FastAPI.

- Service: notes_backend
- Run locally:
  - `cd notes_backend`
  - `pip install -r requirements.txt`
  - `uvicorn src.api.main:app --host 0.0.0.0 --port 3001`
- API Docs: http://localhost:3001/docs

The backend persists data using SQLite (SQLAlchemy) and exposes REST endpoints for notes CRUD.