"""Application settings for the DevOps LLM Agent."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from packages.shared.env_schema._simple_yaml import (
    SimpleYAMLError,
    load as load_simple_yaml,
)


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    """Load a YAML document from *path* using the simple YAML loader."""
    if not path.exists():
        return {}

    text = path.read_text(encoding="utf-8")
    try:
        data = load_simple_yaml(text)
    except SimpleYAMLError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Failed to parse YAML file {path}: {exc}") from exc

    if isinstance(data, dict):
        return data
    raise ValueError(f"YAML file {path} must decode into a mapping")


class LLMProviderSettings(BaseModel):
    """Configuration for a single LLM provider."""

    name: str
    type: str
    enabled: bool = True
    priority: int = 0
    config: Dict[str, Any] = Field(default_factory=dict)


class AgentSettings(BaseModel):
    """Configuration for an orchestrator agent."""

    name: str
    max_steps: Optional[int] = None
    temperature: Optional[float] = None
    model: Optional[str] = None


class OrchestratorSettings(BaseModel):
    """Configuration for orchestrator agents."""

    planner: AgentSettings = Field(
        default_factory=lambda: AgentSettings(name="planner", max_steps=5, temperature=0.3)
    )
    executor: AgentSettings = Field(
        default_factory=lambda: AgentSettings(name="executor")
    )
    verifier: AgentSettings = Field(
        default_factory=lambda: AgentSettings(name="verifier", temperature=0.2)
    )


class Settings(BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    debug: bool = Field(default=False, alias="API_DEBUG")

    # Database Configuration
    database_url: str = Field(
        default="sqlite+aiosqlite:///./devops_agent.db",
        alias="DATABASE_URL"
    )
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    
    # Redis Configuration
    redis_url: str = Field(
        default="memory://redis",
        alias="REDIS_URL"
    )
    
    # Security
    secret_key: str = Field(default="dev-secret-key-change-in-production", alias="SECRET_KEY")
    allowed_hosts: List[str] = Field(default=["*"], alias="ALLOWED_HOSTS")
    cors_origins: List[str] = Field(default=["*"], alias="CORS_ORIGINS")
    
    @field_validator('allowed_hosts', 'cors_origins', mode='before')
    @classmethod
    def parse_list_from_string(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse list from string or return as-is if already a list."""
        if isinstance(v, str):
            # Handle simple wildcard or comma-separated values
            if v == "*":
                return ["*"]
            return [item.strip() for item in v.split(",")]
        return v

    # LLM Configuration
    llm_config_path: Path = Field(default=Path("config/llm.yml"))
    llm_providers: List[LLMProviderSettings] = Field(default_factory=list)

    # Orchestrator Configuration
    orchestrator: OrchestratorSettings = Field(default_factory=OrchestratorSettings)

    # Environment Profiles
    environment_profiles_dir: Path = Field(
        default=Path("environments"), alias="ENVIRONMENT_PROFILES_DIR"
    )
    environment_cache_ttl: int = Field(
        default=300, alias="ENVIRONMENT_CACHE_TTL"
    )
    
    # LLM Provider Toggles
    enable_gemini_provider: bool = Field(
        default=False, alias="ENABLE_GEMINI_PROVIDER"
    )
    enable_ollama_provider: bool = Field(
        default=False, alias="ENABLE_OLLAMA_PROVIDER"
    )
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="text", alias="LOG_FORMAT")
    
    # Observability
    prometheus_enabled: bool = Field(default=True, alias="PROMETHEUS_ENABLED")
    audit_logging: bool = Field(default=True, alias="AUDIT_LOGGING")

    def model_post_init(self, __context: Any) -> None:  # pragma: no cover - simple wiring
        super().model_post_init(__context)

        if not self.llm_providers:
            llm_config = _load_yaml_file(self.llm_config_path)
            providers_raw = llm_config.get("providers", [])
            provider_items: List[Dict[str, Any]] = []

            if isinstance(providers_raw, dict):
                for name, data in providers_raw.items():
                    entry = {"name": name}
                    if isinstance(data, dict):
                        entry.update(data)
                    provider_items.append(entry)
            elif isinstance(providers_raw, list):
                provider_items = providers_raw  # type: ignore[assignment]

            self.llm_providers = [LLMProviderSettings(**item) for item in provider_items]

        provider_overrides = {
            "gemini": self.enable_gemini_provider,
            "ollama": self.enable_ollama_provider,
        }
        for provider in self.llm_providers:
            override = provider_overrides.get(provider.name)
            if override is not None:
                provider.enabled = override

        # Ensure a deterministic local provider is always available for offline operation
        has_local = False
        for provider in self.llm_providers:
            if provider.name == 'local':
                has_local = True
                provider.enabled = True
                provider.priority = max(provider.priority, 100)
                provider.type = provider.type or 'local'
                provider.config = {
                    'mode': provider.config.get('mode', 'deterministic'),
                    'model': provider.config.get('model', 'local-simulator'),
                    **provider.config
                }
        if not has_local:
            self.llm_providers.append(
                LLMProviderSettings(
                    name='local',
                    type='local',
                    enabled=True,
                    priority=100,
                    config={'mode': 'deterministic', 'model': 'local-simulator'}
                )
            )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()


__all__ = [
    "AgentSettings",
    "LLMProviderSettings",
    "OrchestratorSettings",
    "Settings",
    "get_settings",
]
