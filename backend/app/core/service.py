import httpx
from app.core.config import settings

NLP_URL = settings.NLP_SERVICE_URL


async def ingest_doc(filename: str, content: bytes, content_type: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{NLP_URL}/api/v1/nlp/ingest",
            files={"file": (filename, content, content_type)},
            timeout=120.0,
        )
        r.raise_for_status()
        return r.json()


async def ask_question(question: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{NLP_URL}/api/v1/nlp/ask",
            json={"question": question},
            timeout=120.0,
        )
        r.raise_for_status()
        return r.json()


async def get_stats() -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{NLP_URL}/api/v1/nlp/stats", timeout=10.0)
        r.raise_for_status()
        return r.json()


async def clear_store() -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.delete(f"{NLP_URL}/api/v1/nlp/documents", timeout=10.0)
        r.raise_for_status()
        return r.json()
