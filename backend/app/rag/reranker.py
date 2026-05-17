from collections import Counter

from app.rag.chunker import DocumentChunk
from app.rag.scoring import tokenize


class LocalReranker:
    """Local lexical reranker used when no external BGE model is configured."""

    def rerank(
        self,
        query: str,
        chunks: list[DocumentChunk],
        top_k: int = 4,
    ) -> list[DocumentChunk]:
        query_counts = Counter(tokenize(query))
        if not query_counts:
            return chunks[:top_k]

        scored = [(self._score(query_counts, chunk), chunk) for chunk in chunks]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in scored[:top_k]]

    def _score(self, query_counts: Counter[str], chunk: DocumentChunk) -> float:
        chunk_counts = Counter(tokenize(chunk.content))
        overlap = sum(
            min(count, chunk_counts.get(token, 0))
            for token, count in query_counts.items()
        )
        code_bonus = sum(
            2.0
            for token in query_counts
            if any(char.isdigit() for char in token) and chunk_counts.get(token, 0)
        )
        return overlap + code_bonus


class BGEReranker:
    """Optional BGE reranker adapter with a deterministic local fallback."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name
        self._fallback = LocalReranker()
        self._model = None
        if model_name:
            try:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(model_name)
            except ImportError:
                self._model = None

    def rerank(
        self,
        query: str,
        chunks: list[DocumentChunk],
        top_k: int = 4,
    ) -> list[DocumentChunk]:
        if not self._model:
            return self._fallback.rerank(query, chunks, top_k=top_k)

        pairs = [(query, chunk.content) for chunk in chunks]
        scores = self._model.predict(pairs)
        scored = sorted(zip(scores, chunks, strict=False), key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in scored[:top_k]]
