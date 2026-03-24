# Project 12 - RAG Document QA System

Upload PDF / DOCX / TXT documents and ask questions about them using a local LLM (Ollama).

## Architecture

```
Frontend :3000  →  Backend :8000  →  NLP Service :8001  →  Ollama :11434
  React/MUI        FastAPI/httpx      LangChain/FAISS       llama3.2 (local)
```

## RAG Pipeline

```
File uploaded
    ↓
PyMuPDF / python-docx extracts text
    ↓
LangChain RecursiveCharacterTextSplitter chunks text (500 chars, 50 overlap)
    ↓
sentence-transformers embeds chunks → stored in FAISS
    ↓
User asks question → question embedded → top-4 chunks retrieved
    ↓
Ollama llama3.2 generates answer from retrieved chunks
    ↓
Answer + source citations returned to UI
```

## Local Run

### Step 0 - Install Ollama (one-time)
```bash
# Download from https://ollama.ai
ollama pull llama3.2   # ~2GB download
ollama serve           # starts on http://localhost:11434
```

### Step 1 - NLP Service
```bash
cd nlp-service && python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### Step 2 - Backend
```bash
cd backend && python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Step 3 - Frontend
```bash
cd frontend && npm install && npm start
```

- NLP Service docs: http://localhost:8001/docs
- Backend docs: http://localhost:8000/docs
- UI: http://localhost:3000

## Docker
```bash
# Ollama must be running on host first
docker-compose up --build
```

## Supported File Types
| Format | Library |
|---|---|
| PDF | PyMuPDF |
| DOCX | python-docx |
| TXT | built-in |

## Dataset
Use any PDF/DOCX/TXT — try SQuAD context paragraphs, Wikipedia articles, or your own documents.
