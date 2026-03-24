from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from app.core.loader import extract_text
from app.core.rag import ingest, ask, get_stats, clear

router = APIRouter(prefix="/api/v1/nlp", tags=["rag"])


class QuestionInput(BaseModel):
    question: str


@router.post("/ingest")
async def ingest_doc(file: UploadFile = File(...)):
    allowed = {"pdf", "docx", "doc", "txt"}
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    text = extract_text(file.filename, content)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from file")
    return ingest(text, file.filename)


@router.post("/ask")
def ask_question(body: QuestionInput):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    return ask(body.question)


@router.get("/stats")
def stats():
    return get_stats()


@router.delete("/documents")
def clear_store():
    return clear()
