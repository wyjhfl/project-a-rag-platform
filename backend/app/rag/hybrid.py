from typing import Protocol

from app.rag.chunker import DocumentChunk
from app.rag.keyword import BM25Retriever
from app.rag.reranker import BGEReranker
from app.rag.rrf import reciprocal_rank_fusion
from app.rag.tracing import trace_retrieval


class Retriever(Protocol):
    def search(self, query: str, top_k: int = 4) -> list[DocumentChunk]:
        ...


class Reranker(Protocol):
    def rerank(
        self,
        query: str,
        chunks: list[DocumentChunk],
        top_k: int = 4,
    ) -> list[DocumentChunk]:
        ...


class VectorRetriever:
    def __init__(self, vector_store: Retriever) -> None:
        self.vector_store = vector_store

    def search(self, query: str, top_k: int = 4) -> list[DocumentChunk]:
        return self.vector_store.search(query, top_k=top_k)


class HybridRetriever:
    def __init__(
        self,
        keyword_retriever: Retriever,
        vector_retriever: Retriever,
        reranker: Reranker | None = None,
    ) -> None:
        self.keyword_retriever = keyword_retriever
        self.vector_retriever = vector_retriever
        self.reranker = reranker or BGEReranker()

    @classmethod
    def from_chunks(cls, chunks: list[DocumentChunk], vector_store: Retriever) -> "HybridRetriever":
        return cls(
            keyword_retriever=BM25Retriever(chunks),
            vector_retriever=VectorRetriever(vector_store),
            reranker=BGEReranker(),
        )

    @trace_retrieval("project-a-v02-hybrid-retrieval")
    def search(
        self,
        query: str,
        top_k: int = 4,
        candidate_k: int | None = None,
    ) -> list[DocumentChunk]:
        if top_k <= 0:
            return []

        candidate_count = candidate_k or max(top_k * 4, 8)
        keyword_results = self.keyword_retriever.search(query, top_k=candidate_count)
        vector_results = self.vector_retriever.search(query, top_k=candidate_count)
        fused = reciprocal_rank_fusion(
            [keyword_results, vector_results],
            top_k=candidate_count,
        )

        if not fused:
            return []

        return self.reranker.rerank(query, fused, top_k=top_k)
