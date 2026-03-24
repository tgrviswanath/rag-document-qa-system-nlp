from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from app.core.service import ingest_doc, ask_question, get_stats, clear_store
import httpx

router = APIRouter(prefix="/api/v1", tags=["rag"])


class QuestionInput(BaseModel):
    question: str


def _handle(e: Exception):
    if isinstance(e, httpx.ConnectError):
        raise HTTPException(status_code=503, detail="NLP service unavailable")
    if isinstance(e, httpx.HTTPStatusError):
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    try:
        content = await file.read()
        return await ingest_doc(file.filename, content, file.content_type or "application/octet-stream")
    except Exception as e:
        _handle(e)


@router.post("/ask")
async def ask(body: QuestionInput):
    try:
        return await ask_question(body.question)
    except Exception as e:
        _handle(e)


@router.get("/stats")
async def stats():
    try:
        return await get_stats()
    except Exception as e:
        _handle(e)


@router.delete("/documents")
async def clear():
    try:
        return await clear_store()
    except Exception as e:
        _handle(e)
