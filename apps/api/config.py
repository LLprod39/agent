"""Configuration management for the API."""

import os
from typing import Any, Dict, List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""

    # API settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_debug: bool = Field(default=False, env="API_DEBUG")

    # Security settings
    secret_key: str = Field(default="dev-secret-key", env="SECRET_KEY")
    allowed_hosts: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")

    # Database settings
    database_url: str = Field(default="sqlite:///./devops_agent.db", env="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")

    # LLM provider settings
    llm_providers: List[Dict[str, Any]] = Field(
        default=[
            {
                "name": "gemini",
                "type": "gemini",
                "priority": 1,
                "enabled": True,
                "config": {
                    "api_key": os.getenv("GEMINI_API_KEY", ""),
                    "model": "gemini-1.5-flash",
                },
            },
            {
                "name": "ollama",
                "type": "ollama",
                "priority": 2,
                "enabled": True,
                "config": {"base_url": "http://localhost:11434", "model": "llama3"},
            },
        ],
        env="LLM_PROVIDERS",
    )

    # Orchestrator settings
    orchestrator_config: Dict[str, Any] = Field(
        default={
            "planner": {"name": "planner", "temperature": 0.3, "max_tokens": 2000},
            "executor": {"name": "executor", "timeout": 30.0, "retry_count": 3},
            "verifier": {"name": "verifier", "temperature": 0.2, "max_tokens": 1500},
        },
        env="ORCHESTRATOR_CONFIG",
    )

    # Tool executor settings
    tool_executors: Dict[str, Any] = Field(
        default={
            "ssh": {"timeout": 30.0, "retry_count": 3, "retry_delay": 1.0},
            "kubectl": {"timeout": 60.0, "retry_count": 2, "retry_delay": 2.0},
            "docker": {"timeout": 120.0, "retry_count": 2, "retry_delay": 1.0},
        },
        env="TOOL_EXECUTORS",
    )

    # Environment profiles
    environment_profiles_dir: str = Field(
        default="environments", env="ENVIRONMENT_PROFILES_DIR"
    )

    # Logging settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT"
    )

    # Rate limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
