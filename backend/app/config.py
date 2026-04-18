"""
Application configuration loaded from environment variables.
"""
import os
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # Supabase
    supabase_url: str = Field(default="https://foijpyqxfqlsugjzjtef.supabase.co")
    supabase_key: str = Field(default="")
    supabase_db_url: str = Field(default="")

    # LLM
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.1:8b")
    groq_api_key: str = Field(default="")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Qdrant
    qdrant_url: str = Field(default="http://localhost:6333")

    # App
    app_env: str = Field(default="development")
    log_level: str = Field(default="DEBUG")
    upload_dir: str = Field(default="./uploads")

    # Monitoring
    prometheus_enabled: bool = Field(default=True)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
