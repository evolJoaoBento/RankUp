from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MECATECA_", extra="ignore")

    env: str = "dev"
    database_url: str = "postgresql+asyncpg://mecateca:mecateca@localhost:5432/mecateca"

    jwt_secret: str = "dev-secret-change-me"
    jwt_access_ttl_min: int = 15
    jwt_refresh_ttl_days: int = 30
    jwt_alg: str = "HS256"

    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    free_tutor_msgs_per_day: int = 20

    # seed the demo discipline (Philosophy) + its curriculum tests at boot.
    # Schools running their own content can turn this off.
    seed_demo: bool = True

    # where uploaded material assets (pdf/markdown/files) are stored on disk
    upload_dir: str = "var/uploads"
    max_upload_mb: int = 25

    # LLM backend: "gateway" (local Claude CLI, default) | "ollama" | "anthropic" | "fake"
    llm_backend: str = "gateway"

    # OpenAI-compatible local gateway -> Claude Code CLI (no API billing)
    gateway_base_url: str = "http://localhost:8010/v1"
    gateway_model: str = ""  # empty = CLI default; or e.g. claude-sonnet-4-5-20250929

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    ollama_think: str = "auto"  # auto | on | off  (qwen3 etc. support a thinking mode)
    ollama_num_ctx: int = 8192  # cap KV-cache so 8B fits 8GB VRAM (qwen3 default ctx is ~40k)
    ollama_num_gpu: int = -1  # GPU layers; -1 = Ollama auto, 0 = CPU-only (stable on small VRAM)

    # read from the bare ANTHROPIC_API_KEY env var (no prefix)
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_label(self) -> str:
        if self.llm_backend == "ollama":
            return f"ollama:{self.ollama_model}"
        if self.llm_backend == "gateway":
            return f"gateway:{self.gateway_model or 'default'}"
        return self.llm_backend


@lru_cache
def get_settings() -> Settings:
    return Settings()
