from pathlib import Path

from app.config import Settings
from app.rag.embedding import Embedding, EmbeddingConfig, build_embedding
from app.rag.vector_store import ChromaVectorStore, MilvusVectorStore, VectorStore


def build_embedding_from_settings(settings: Settings) -> Embedding:
    return build_embedding(
        EmbeddingConfig(
            provider=settings.embedding_provider,
            model=settings.embedding_model,
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
            dimension=settings.embedding_dimension,
        )
    )


def build_vector_store(settings: Settings, chroma_dir: Path | None = None) -> VectorStore:
    backend = settings.vector_backend.strip().lower()
    embedding = build_embedding_from_settings(settings)
    if backend == "chroma":
        return ChromaVectorStore(chroma_dir or settings.chroma_dir, embedding=embedding)
    if backend == "milvus":
        return MilvusVectorStore(
            uri=settings.milvus_uri,
            token=settings.milvus_token,
            collection_name=settings.milvus_collection,
            embedding=embedding,
        )
    raise ValueError("VECTOR_BACKEND must be either 'chroma' or 'milvus'.")
