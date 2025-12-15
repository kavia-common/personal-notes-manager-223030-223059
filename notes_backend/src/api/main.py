import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Path, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# Database configuration using SQLite (lightweight persistence).
# Do not hardcode in production; here it's fine for local container persistence.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "data"))
os.makedirs(DB_DIR, exist_ok=True)
DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'notes.db')}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite with threads in FastAPI
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class NoteORM(Base):
    """SQLAlchemy ORM model for the notes table."""
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# Pydantic models for request/response validation and documentation

class NoteBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Short title of the note")
    content: str = Field(..., min_length=1, description="Content body of the note")


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Updated title of the note")
    content: Optional[str] = Field(None, min_length=1, description="Updated content of the note")


class NoteOut(NoteBase):
    id: int = Field(..., description="Unique identifier for the note")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


# DB dependency
def get_db():
    """
    Provides a SQLAlchemy database session and ensures it's closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# FastAPI app initialization with metadata and tags
app = FastAPI(
    title="Notes Backend API",
    description="A simple Notes API allowing users to create, view, edit, and delete notes.",
    version="1.0.0",
    openapi_tags=[
        {"name": "health", "description": "Operations for service health and info"},
        {"name": "notes", "description": "CRUD operations for notes"},
    ],
)

# Enable CORS for all origins for development purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production restrict origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event to initialize/migrate database
@app.on_event("startup")
def on_startup():
    """
    Initialize SQLite database and create tables if they do not exist.
    """
    Base.metadata.create_all(bind=engine)


# PUBLIC_INTERFACE
@app.get("/", tags=["health"], summary="Health Check", operation_id="health_check")
def health_check():
    """Health check endpoint to verify service availability."""
    return {"message": "Healthy"}


# CRUD Endpoints for Notes

# PUBLIC_INTERFACE
@app.post(
    "/notes",
    response_model=NoteOut,
    status_code=status.HTTP_201_CREATED,
    tags=["notes"],
    summary="Create a new note",
    description="Create and persist a new note with a title and content.",
    operation_id="create_note",
    responses={
        201: {"description": "Note created successfully"},
        422: {"description": "Validation error"},
    },
)
def create_note(payload: NoteCreate, db: Session = Depends(get_db)) -> NoteOut:
    """
    Create a new note in the database.

    Parameters:
    - payload: NoteCreate with title and content

    Returns:
    - NoteOut: The created note including id and timestamps
    """
    now = datetime.utcnow()
    note = NoteORM(
        title=payload.title.strip(),
        content=payload.content.strip(),
        created_at=now,
        updated_at=now,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return NoteOut.model_validate(note)


# PUBLIC_INTERFACE
@app.get(
    "/notes",
    response_model=List[NoteOut],
    tags=["notes"],
    summary="List notes",
    description="Retrieve all notes sorted by newest updated first.",
    operation_id="list_notes",
)
def list_notes(db: Session = Depends(get_db)) -> List[NoteOut]:
    """
    List all notes in the database.

    Returns:
    - List[NoteOut]: List of notes
    """
    notes = db.query(NoteORM).order_by(NoteORM.updated_at.desc()).all()
    return [NoteOut.model_validate(n) for n in notes]


# PUBLIC_INTERFACE
@app.get(
    "/notes/{note_id}",
    response_model=NoteOut,
    tags=["notes"],
    summary="Get a single note",
    description="Retrieve a single note by its unique id.",
    operation_id="get_note",
    responses={
        404: {"description": "Note not found"},
    },
)
def get_note(
    note_id: int = Path(..., ge=1, description="ID of the note to retrieve"),
    db: Session = Depends(get_db),
) -> NoteOut:
    """
    Retrieve a single note.

    Parameters:
    - note_id: integer id for the note

    Returns:
    - NoteOut: The requested note
    """
    note = db.query(NoteORM).filter(NoteORM.id == note_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return NoteOut.model_validate(note)


# PUBLIC_INTERFACE
@app.put(
    "/notes/{note_id}",
    response_model=NoteOut,
    tags=["notes"],
    summary="Update a note (full)",
    description="Replace title and content of the note.",
    operation_id="update_note_put",
    responses={
        404: {"description": "Note not found"},
    },
)
def update_note_put(
    payload: NoteCreate,
    note_id: int = Path(..., ge=1, description="ID of the note to update"),
    db: Session = Depends(get_db),
) -> NoteOut:
    """
    Fully update a note (title and content).

    Parameters:
    - note_id: id of the note to update
    - payload: NoteCreate with new title and content

    Returns:
    - NoteOut: Updated note
    """
    note = db.query(NoteORM).filter(NoteORM.id == note_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    note.title = payload.title.strip()
    note.content = payload.content.strip()
    note.updated_at = datetime.utcnow()

    db.add(note)
    db.commit()
    db.refresh(note)
    return NoteOut.model_validate(note)


# PUBLIC_INTERFACE
@app.patch(
    "/notes/{note_id}",
    response_model=NoteOut,
    tags=["notes"],
    summary="Update a note (partial)",
    description="Partially update title and/or content of the note.",
    operation_id="update_note_patch",
    responses={
        404: {"description": "Note not found"},
    },
)
def update_note_patch(
    payload: NoteUpdate,
    note_id: int = Path(..., ge=1, description="ID of the note to update"),
    db: Session = Depends(get_db),
) -> NoteOut:
    """
    Partially update fields of a note.

    Parameters:
    - note_id: id of the note to update
    - payload: NoteUpdate with optional title/content

    Returns:
    - NoteOut: Updated note
    """
    note = db.query(NoteORM).filter(NoteORM.id == note_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    updated = False
    if payload.title is not None:
        note.title = payload.title.strip()
        updated = True
    if payload.content is not None:
        note.content = payload.content.strip()
        updated = True

    if updated:
        note.updated_at = datetime.utcnow()
        db.add(note)
        db.commit()
        db.refresh(note)

    return NoteOut.model_validate(note)


# PUBLIC_INTERFACE
@app.delete(
    "/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["notes"],
    summary="Delete a note",
    description="Delete a note by id. Returns no content on success.",
    operation_id="delete_note",
    responses={
        204: {"description": "Note deleted"},
        404: {"description": "Note not found"},
    },
)
def delete_note(
    note_id: int = Path(..., ge=1, description="ID of the note to delete"),
    db: Session = Depends(get_db),
):
    """
    Delete a note.

    Parameters:
    - note_id: id of the note to delete

    Returns:
    - 204 No Content
    """
    note = db.query(NoteORM).filter(NoteORM.id == note_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    db.delete(note)
    db.commit()
    return None


# Entry-point to run with: uvicorn src.api.main:app --host 0.0.0.0 --port 3001
