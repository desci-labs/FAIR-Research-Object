from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    FILE_STORAGE_DIR: Path
    NO_TOKEN_DIRECTORY: Path

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()