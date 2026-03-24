from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    APP_NAME: str = "RAG Document QA Backend"
    APP_VERSION: str = "1.0.0"
    APP_PORT: int = 8000
    NLP_SERVICE_URL: str = "http://localhost:8001"
    ALLOWED_ORIGINS: str = '["http://localhost:3000"]'

    @property
    def origins(self) -> List[str]:
        return json.loads(self.ALLOWED_ORIGINS)

    class Config:
        env_file = ".env"


settings = Settings()
