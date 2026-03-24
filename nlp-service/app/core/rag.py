"""
RAG pipeline:
  1. Ingest: chunk text → embed → store in FAISS
  2. Query:  embed question → retrieve top-K chunks → Ollama generates answer
"""
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
from app.core.config import settings

_embeddings = None
_vectorstore: FAISS | None = None
_qa_chain = None
_doc_count = 0


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name=settings.EMBED_MODEL)
    return _embeddings


def _get_llm():
    return Ollama(model=settings.OLLAMA_MODEL, base_url=settings.OLLAMA_BASE_URL)


def _build_chain():
    global _qa_chain
    if _vectorstore is None:
        return
    retriever = _vectorstore.as_retriever(search_kwargs={"k": settings.TOP_K})
    _qa_chain = RetrievalQA.from_chain_type(
        llm=_get_llm(),
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
    )


def ingest(text: str, doc_name: str) -> dict:
    global _vectorstore, _doc_count
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )
    chunks = splitter.split_text(text)
    metadatas = [{"source": doc_name, "chunk": i} for i in range(len(chunks))]
    emb = _get_embeddings()
    if _vectorstore is None:
        _vectorstore = FAISS.from_texts(chunks, emb, metadatas=metadatas)
    else:
        _vectorstore.add_texts(chunks, metadatas=metadatas)
    _doc_count += 1
    _build_chain()
    return {"chunks_added": len(chunks), "total_docs": _doc_count}


def ask(question: str) -> dict:
    if _qa_chain is None:
        return {"answer": "No documents ingested yet. Please upload a document first.",
                "sources": []}
    result = _qa_chain.invoke({"query": question})
    sources = [
        {"source": d.metadata.get("source", ""), "chunk": d.metadata.get("chunk", 0),
         "excerpt": d.page_content[:200]}
        for d in result.get("source_documents", [])
    ]
    return {"answer": result["result"], "sources": sources}


def get_stats() -> dict:
    return {
        "total_docs": _doc_count,
        "total_chunks": _vectorstore.index.ntotal if _vectorstore else 0,
        "embed_model": settings.EMBED_MODEL,
        "llm_model": settings.OLLAMA_MODEL,
        "ready": _vectorstore is not None,
    }


def clear() -> dict:
    global _vectorstore, _qa_chain, _doc_count
    _vectorstore = None
    _qa_chain = None
    _doc_count = 0
    return {"message": "Vector store cleared"}
