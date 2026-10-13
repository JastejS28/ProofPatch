from functools import lru_cache
from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


ROOT_DIR = (
    Path(__file__)
    .resolve()
    .parents[3]
)


class Settings(BaseSettings):
    app_name: str = "ProofPatch"
    app_env: str = "development"

    database_url: str

    workspace_root: Path = Path(
        "workspace"
    )

    git_clone_timeout_seconds: int = 60
    github_request_timeout_seconds: int = 10

    # -------------------------
    # LLM provider
    # -------------------------

    llm_provider: str = (
        "gemini_ollama"
    )

    # -------------------------
    # Ollama
    # -------------------------

    ollama_model: str = "qwen3:4b"

    ollama_host: str = (
        "http://localhost:11434"
    )

    ollama_timeout_seconds: int = 120

    # -------------------------
    # Gemini
    # -------------------------

    gemini_api_key: str | None = None

    gemini_model: str = (
        "gemini-3.5-flash"
    )

    gemini_timeout_seconds: int = 30

    gemini_retry_attempts: int = 1

    # -------------------------
    # Planning
    # -------------------------

    planning_token_budget: int = 6000
    max_hypotheses: int = 3

    # -------------------------
    # Docker sandbox
    # -------------------------

    sandbox_image: str = (
        "proofpatch-sandbox:latest"
    )

    sandbox_cpu_limit: float = 1.0
    sandbox_memory_mb: int = 1024
    sandbox_pids_limit: int = 128

    benchmark_processes: int = 3
    benchmark_values: int = 5
    benchmark_warmups: int = 1

    benchmark_min_time_seconds: float = 0.05
    benchmark_timeout_seconds: int = 240

    benchmark_input_size: int = 2000

    performance_threshold_percent: float = 10.0

    validation_timeout_seconds: int = 120

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()