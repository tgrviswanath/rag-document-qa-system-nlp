from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "RAG Document QA NLP Service"
    SERVICE_VERSION: str = "1.0.0"
    SERVICE_PORT: int = 8001
    EMBED_MODEL: str = "all-MiniLM-L6-v2"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 4

    class Config:
        env_file = ".env"


settings = Settings()
