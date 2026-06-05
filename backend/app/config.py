import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[2]

_DEFAULT_CORS_ORIGINS = [
    "http://127.0.0.1:4175",
    "http://localhost:4175",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]


_VALID_STORAGE_BACKENDS = ("sqlite", "postgres")
_VALID_VECTOR_BACKENDS = ("chroma", "milvus")
_VALID_MULTIMODAL_BACKENDS = ("sidecar", "mineru", "paddleocr", "vision_llm")
_MIN_CACHE_TTL = 1
_MAX_CACHE_TTL = 86400
_MIN_UPLOAD_BYTES = 1
_MAX_UPLOAD_BYTES = 100 * 1024 * 1024


@dataclass(frozen=True)
class Settings:
    storage_backend: str = "sqlite"
    database_url: str = ""
    vector_backend: str = "chroma"
    database_path: Path = PROJECT_DIR / "data" / "app.db"
    chroma_dir: Path = PROJECT_DIR / "data" / "chroma"
    milvus_uri: str = ""
    milvus_token: str = ""
    milvus_collection: str = "project_a_v1"
    seed_docs_dir: Path = PROJECT_DIR / "data" / "seed_docs"
    real_docs_dir: Path = PROJECT_DIR / "data" / "real_manuals_sanitized"
    uploaded_docs_dir: Path = PROJECT_DIR / "data" / "uploaded_docs"
    prompt_path: Path = PROJECT_DIR / "prompts" / "rag_prompt_v0.1.txt"
    llm_provider: str = "xiaomi_mimo"
    llm_model: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""
    graph_retrieval_enabled: bool = False
    neo4j_uri: str = ""
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"
    cache_enabled: bool = False
    redis_url: str = ""
    cache_ttl_seconds: int = 1800
    multimodal_backend: str = "sidecar"
    mineru_command: str = "mineru"
    mineru_output_dir: Path = PROJECT_DIR / "data" / "mineru_output"
    vision_llm_model: str = ""
    vision_llm_api_key: str = ""
    vision_llm_base_url: str = ""
    auth_enabled: bool = False
    viewer_api_key: str = ""
    operator_api_key: str = ""
    admin_api_key: str = ""
    cors_allow_origins: list[str] = field(default_factory=list)
    upload_max_bytes: int = 10 * 1024 * 1024
    log_level: str = "INFO"
    job_execution_mode: str = "inprocess"
    job_poll_interval_seconds: int = 5
    job_default_timeout_seconds: int = 300
    rate_limit_enabled: bool = False
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 30
    rate_limit_exempt_paths: list[str] = field(default_factory=list)
    rate_limit_backend: str = "memory"
    rate_limit_redis_url: str = ""
    metrics_enabled: bool = False

    def validate(self) -> list[str]:
        errors: list[str] = []
        sb = self.storage_backend.strip().lower()
        if sb not in _VALID_STORAGE_BACKENDS:
            errors.append(f"STORAGE_BACKEND must be one of {_VALID_STORAGE_BACKENDS}")
        if sb == "postgres" and not self.database_url:
            errors.append("DATABASE_URL is required when STORAGE_BACKEND=postgres")
        vb = self.vector_backend.strip().lower()
        if vb not in _VALID_VECTOR_BACKENDS:
            errors.append(f"VECTOR_BACKEND must be one of {_VALID_VECTOR_BACKENDS}")
        if vb == "milvus" and not self.milvus_uri:
            errors.append("MILVUS_URI is required when VECTOR_BACKEND=milvus")
        lp = self.llm_provider.strip().lower()
        if not lp:
            errors.append("LLM_PROVIDER must not be empty")
        mb = self.multimodal_backend.strip().lower()
        if mb not in _VALID_MULTIMODAL_BACKENDS:
            errors.append(f"MULTIMODAL_BACKEND must be one of {_VALID_MULTIMODAL_BACKENDS}")
        if self.cache_enabled and not self.redis_url:
            errors.append("REDIS_URL is required when CACHE_ENABLED=true")
        if self.cache_ttl_seconds < _MIN_CACHE_TTL or self.cache_ttl_seconds > _MAX_CACHE_TTL:
            errors.append(
                f"CACHE_TTL_SECONDS must be between {_MIN_CACHE_TTL} and {_MAX_CACHE_TTL}"
            )
        if self.graph_retrieval_enabled:
            if not self.neo4j_uri:
                errors.append("NEO4J_URI is required when GRAPH_RETRIEVAL_ENABLED=true")
            if not self.neo4j_username:
                errors.append("NEO4J_USERNAME is required when GRAPH_RETRIEVAL_ENABLED=true")
            if not self.neo4j_password:
                errors.append("NEO4J_PASSWORD is required when GRAPH_RETRIEVAL_ENABLED=true")
        if self.auth_enabled:
            if not any([self.viewer_api_key, self.operator_api_key, self.admin_api_key]):
                errors.append(
                    "At least one API key (VIEWER_API_KEY, OPERATOR_API_KEY, "
                    "ADMIN_API_KEY) must be configured when AUTH_ENABLED=true"
                )
        if self.upload_max_bytes < _MIN_UPLOAD_BYTES or self.upload_max_bytes > _MAX_UPLOAD_BYTES:
            errors.append(
                f"UPLOAD_MAX_BYTES must be between {_MIN_UPLOAD_BYTES} and {_MAX_UPLOAD_BYTES}"
            )
        if self.rate_limit_backend == "redis" and not self.rate_limit_redis_url:
            errors.append("RATE_LIMIT_REDIS_URL is required when RATE_LIMIT_BACKEND=redis")
        return errors


def get_settings() -> Settings:
    load_dotenv(PROJECT_DIR / ".env", override=False)
    return Settings(
        storage_backend=os.getenv("STORAGE_BACKEND", "sqlite"),
        database_url=os.getenv("DATABASE_URL", os.getenv("APP_DATABASE_URL", "")),
        vector_backend=os.getenv("VECTOR_BACKEND", "chroma"),
        database_path=Path(os.getenv("APP_DATABASE_PATH", PROJECT_DIR / "data" / "app.db")),
        chroma_dir=Path(os.getenv("CHROMA_PERSIST_DIR", PROJECT_DIR / "data" / "chroma")),
        milvus_uri=os.getenv("MILVUS_URI", ""),
        milvus_token=os.getenv("MILVUS_TOKEN", ""),
        milvus_collection=os.getenv("MILVUS_COLLECTION", "project_a_v1"),
        seed_docs_dir=Path(os.getenv("SEED_DOCS_DIR", PROJECT_DIR / "data" / "seed_docs")),
        real_docs_dir=Path(
            os.getenv("REAL_DOCS_DIR", PROJECT_DIR / "data" / "real_manuals_sanitized")
        ),
        uploaded_docs_dir=Path(
            os.getenv("UPLOADED_DOCS_DIR", PROJECT_DIR / "data" / "uploaded_docs")
        ),
        prompt_path=Path(
            os.getenv("RAG_PROMPT_PATH", PROJECT_DIR / "prompts" / "rag_prompt_v0.1.txt")
        ),
        llm_provider=os.getenv("LLM_PROVIDER", "xiaomi_mimo"),
        llm_model=os.getenv("LLM_MODEL", ""),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_base_url=os.getenv("LLM_BASE_URL", ""),
        graph_retrieval_enabled=_env_bool("GRAPH_RETRIEVAL_ENABLED"),
        neo4j_uri=os.getenv("NEO4J_URI", ""),
        neo4j_username=os.getenv("NEO4J_USERNAME", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", ""),
        neo4j_database=os.getenv("NEO4J_DATABASE", "neo4j"),
        cache_enabled=_env_bool("CACHE_ENABLED"),
        redis_url=os.getenv("REDIS_URL", ""),
        cache_ttl_seconds=_env_int("CACHE_TTL_SECONDS", 1800),
        multimodal_backend=os.getenv("MULTIMODAL_BACKEND", "sidecar"),
        mineru_command=os.getenv("MINERU_COMMAND", "mineru"),
        mineru_output_dir=Path(
            os.getenv("MINERU_OUTPUT_DIR", PROJECT_DIR / "data" / "mineru_output")
        ),
        vision_llm_model=os.getenv("VISION_LLM_MODEL", os.getenv("LLM_MODEL", "")),
        vision_llm_api_key=os.getenv("VISION_LLM_API_KEY", os.getenv("LLM_API_KEY", "")),
        vision_llm_base_url=os.getenv("VISION_LLM_BASE_URL", os.getenv("LLM_BASE_URL", "")),
        auth_enabled=_env_bool("AUTH_ENABLED"),
        viewer_api_key=os.getenv("VIEWER_API_KEY", ""),
        operator_api_key=os.getenv("OPERATOR_API_KEY", ""),
        admin_api_key=os.getenv("ADMIN_API_KEY", ""),
        cors_allow_origins=_parse_cors_origins(
            os.getenv("CORS_ALLOW_ORIGINS")
        ),
        upload_max_bytes=_env_int("UPLOAD_MAX_BYTES", 10 * 1024 * 1024),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        job_execution_mode=os.getenv("JOB_EXECUTION_MODE", "inprocess"),
        job_poll_interval_seconds=_env_int("JOB_POLL_INTERVAL_SECONDS", 5),
        job_default_timeout_seconds=_env_int("JOB_DEFAULT_TIMEOUT_SECONDS", 300),
        rate_limit_enabled=_env_bool("RATE_LIMIT_ENABLED"),
        rate_limit_requests_per_minute=_env_int("RATE_LIMIT_REQUESTS_PER_MINUTE", 60),
        rate_limit_burst=_env_int("RATE_LIMIT_BURST", 30),
        rate_limit_exempt_paths=_parse_list(os.getenv("RATE_LIMIT_EXEMPT_PATHS", "")),
        rate_limit_backend=os.getenv("RATE_LIMIT_BACKEND", "memory"),
        rate_limit_redis_url=os.getenv("RATE_LIMIT_REDIS_URL", ""),
        metrics_enabled=_env_bool("METRICS_ENABLED"),
    )


def _parse_cors_origins(raw: str | None) -> list[str]:
    if raw is None or raw.strip() == "":
        return list(_DEFAULT_CORS_ORIGINS)
    raw = raw.strip()
    if raw == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _parse_list(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _env_bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "")
    if not raw:
        return default
    try:
        return int(raw)
    except (ValueError, TypeError):
        return -1
