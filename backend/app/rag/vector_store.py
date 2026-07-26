from pathlib import Path
from typing import Protocol

import chromadb

from app.rag.chunker import DocumentChunk
from app.rag.embedding import Embedding, HashEmbedding


class VectorStore(Protocol):
    def reset(self) -> None:
        pass

    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        pass

    def search(self, query: str, top_k: int = 4) -> list[DocumentChunk]:
        pass


class ChromaVectorStore:
    def __init__(
        self,
        persist_dir: Path,
        collection_name: str = "project_a_v01",
        embedding: Embedding | None = None,
    ) -> None:
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.embedding = embedding or HashEmbedding()
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def reset(self) -> None:
        not_found_error = getattr(chromadb.errors, "NotFoundError", ValueError)
        try:
            self.client.delete_collection(self.collection_name)
        except (ValueError, not_found_error):
            pass
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            return

        ids = [
            f"{chunk.metadata['document_id']}-{chunk.metadata['chunk_index']}"
            for chunk in chunks
        ]
        self.collection.upsert(
            ids=ids,
            documents=[chunk.content for chunk in chunks],
            embeddings=self.embedding.embed_documents([chunk.content for chunk in chunks]),
            metadatas=[chunk.metadata for chunk in chunks],
        )

    def search(self, query: str, top_k: int = 4) -> list[DocumentChunk]:
        result = self.collection.query(
            query_embeddings=[self.embedding.embed_query(query)],
            n_results=top_k,
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]

        return [
            DocumentChunk(content=document, metadata=dict(metadata))
            for document, metadata in zip(documents, metadatas, strict=False)
            if document and metadata
        ]


class MilvusVectorStore:
    def __init__(
        self,
        uri: str,
        token: str = "",
        collection_name: str = "project_a_v1",
        dimension: int = 384,
        embedding: Embedding | None = None,
    ) -> None:
        if not uri:
            raise ValueError("VECTOR_BACKEND=milvus requires MILVUS_URI.")
        from pymilvus import DataType, MilvusClient

        self.uri = uri
        self.token = token
        self.collection_name = collection_name
        self.embedding = embedding or HashEmbedding(dimension=dimension)
        self.dimension = self.embedding.dimension
        self.client = MilvusClient(uri=uri, token=token or None)
        self._data_type = DataType
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        if self.client.has_collection(self.collection_name):
            return
        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field("id", self._data_type.VARCHAR, is_primary=True, max_length=256)
        schema.add_field("vector", self._data_type.FLOAT_VECTOR, dim=self.dimension)
        schema.add_field("content", self._data_type.VARCHAR, max_length=65535)
        schema.add_field("source", self._data_type.VARCHAR, max_length=1024)
        schema.add_field("document_id", self._data_type.VARCHAR, max_length=128)
        schema.add_field("chunk_index", self._data_type.INT64)
        schema.add_field("section", self._data_type.VARCHAR, max_length=1024)
        schema.add_field("chunk_strategy", self._data_type.VARCHAR, max_length=128)

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="HNSW",
            metric_type="COSINE",
            params={"M": 16, "efConstruction": 128},
        )
        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
            consistency_level="Strong",
        )

    def reset(self) -> None:
        if self.client.has_collection(self.collection_name):
            self.client.drop_collection(self.collection_name)
        self._ensure_collection()

    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            return
        vectors = self.embedding.embed_documents([chunk.content for chunk in chunks])
        rows = []
        for chunk, vector in zip(chunks, vectors, strict=False):
            metadata = chunk.metadata
            rows.append(
                {
                    "id": f"{metadata['document_id']}-{metadata['chunk_index']}",
                    "vector": vector,
                    "content": chunk.content,
                    "source": str(metadata.get("source", "")),
                    "document_id": str(metadata.get("document_id", "")),
                    "chunk_index": int(metadata.get("chunk_index", 0)),
                    "section": str(metadata.get("section", "")),
                    "chunk_strategy": str(metadata.get("chunk_strategy", "")),
                }
            )
        self.client.insert(collection_name=self.collection_name, data=rows)
        self.client.flush(collection_name=self.collection_name)

    def search(self, query: str, top_k: int = 4) -> list[DocumentChunk]:
        results = self.client.search(
            collection_name=self.collection_name,
            data=[self.embedding.embed_query(query)],
            anns_field="vector",
            limit=top_k,
            search_params={"metric_type": "COSINE", "params": {"ef": 64}},
            output_fields=[
                "content",
                "source",
                "document_id",
                "chunk_index",
                "section",
                "chunk_strategy",
            ],
        )
        chunks: list[DocumentChunk] = []
        for hit in results[0] if results else []:
            entity = hit.get("entity", {})
            content = entity.get("content", "")
            if not content:
                continue
            chunks.append(
                DocumentChunk(
                    content=content,
                    metadata={
                        "source": entity.get("source", ""),
                        "document_id": entity.get("document_id", ""),
                        "chunk_index": int(entity.get("chunk_index", 0)),
                        "section": entity.get("section", ""),
                        "chunk_strategy": entity.get("chunk_strategy", ""),
                    },
                )
            )
        return chunks
