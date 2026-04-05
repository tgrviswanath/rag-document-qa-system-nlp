import asyncio
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from app.core.loader import extract_text
from app.core.rag import ingest, ask, get_stats, clear

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_EXTS = {"pdf", "docx", "doc", "txt"}

router = APIRouter(prefix="/api/v1/nlp", tags=["rag"])


class QuestionInput(BaseModel):
    question: str


@router.post("/ingest")
async def ingest_doc(file: UploadFile = File(...)):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 20MB")
    try:
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, extract_text, file.filename, content)
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from file")
        return await loop.run_in_executor(None, ingest, text, file.filename)
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask")
async def ask_question(body: QuestionInput):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, ask, body.question)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
def stats():
    return get_stats()


@router.delete("/documents")
def clear_store():
    return clear()
