import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[2]


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
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "1800")),
        multimodal_backend=os.getenv("MULTIMODAL_BACKEND", "sidecar"),
        mineru_command=os.getenv("MINERU_COMMAND", "mineru"),
        mineru_output_dir=Path(
            os.getenv("MINERU_OUTPUT_DIR", PROJECT_DIR / "data" / "mineru_output")
        ),
        vision_llm_model=os.getenv("VISION_LLM_MODEL", os.getenv("LLM_MODEL", "")),
        vision_llm_api_key=os.getenv("VISION_LLM_API_KEY", os.getenv("LLM_API_KEY", "")),
        vision_llm_base_url=os.getenv("VISION_LLM_BASE_URL", os.getenv("LLM_BASE_URL", "")),
    )


def _env_bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}
