from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_stats_empty():
    r = client.get("/api/v1/nlp/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total_docs"] == 0
    assert data["ready"] is False


def test_ask_no_docs():
    r = client.post("/api/v1/nlp/ask", json={"question": "What is this about?"})
    assert r.status_code == 200
    assert "No documents" in r.json()["answer"]


def test_ask_empty_question():
    r = client.post("/api/v1/nlp/ask", json={"question": "  "})
    assert r.status_code == 400


def test_ingest_txt():
    with patch("app.core.rag.HuggingFaceEmbeddings") as mock_emb, \
         patch("app.core.rag.FAISS") as mock_faiss:
        mock_emb.return_value = MagicMock()
        mock_faiss.from_texts.return_value = MagicMock(index=MagicMock(ntotal=3))
        txt_content = b"This is a test document about machine learning and NLP."
        r = client.post(
            "/api/v1/nlp/ingest",
            files={"file": ("test.txt", txt_content, "text/plain")},
        )
        assert r.status_code == 200
        assert "chunks_added" in r.json()


def test_ingest_unsupported_type():
    r = client.post(
        "/api/v1/nlp/ingest",
        files={"file": ("test.csv", b"a,b,c", "text/csv")},
    )
    assert r.status_code == 400


def test_clear():
    r = client.delete("/api/v1/nlp/documents")
    assert r.status_code == 200
    assert "cleared" in r.json()["message"]
