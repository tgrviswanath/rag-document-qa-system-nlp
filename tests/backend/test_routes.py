from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app

client = TestClient(app)

MOCK_STATS = {"total_docs": 1, "total_chunks": 5, "embed_model": "all-MiniLM-L6-v2",
              "llm_model": "llama3.2", "ready": True}
MOCK_ANSWER = {"answer": "This document is about NLP.", "sources": [
    {"source": "test.txt", "chunk": 0, "excerpt": "This is a test document about NLP."}
]}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200


@patch("app.core.service.get_stats", new_callable=AsyncMock, return_value=MOCK_STATS)
def test_stats(mock_stats):
    r = client.get("/api/v1/stats")
    assert r.status_code == 200
    assert r.json()["ready"] is True


@patch("app.core.service.ask_question", new_callable=AsyncMock, return_value=MOCK_ANSWER)
def test_ask(mock_ask):
    r = client.post("/api/v1/ask", json={"question": "What is this about?"})
    assert r.status_code == 200
    assert "answer" in r.json()


@patch("app.core.service.clear_store", new_callable=AsyncMock, return_value={"message": "cleared"})
def test_clear(mock_clear):
    r = client.delete("/api/v1/documents")
    assert r.status_code == 200
