from app.config import Settings
from app.rag.vector_store import ChromaVectorStore, MilvusVectorStore, VectorStore


def build_vector_store(settings: Settings) -> VectorStore:
    backend = settings.vector_backend.strip().lower()
    if backend == "chroma":
        return ChromaVectorStore(settings.chroma_dir)
    if backend == "milvus":
        return MilvusVectorStore(
            uri=settings.milvus_uri,
            token=settings.milvus_token,
            collection_name=settings.milvus_collection,
        )
    raise ValueError("VECTOR_BACKEND must be either 'chroma' or 'milvus'.")
