import math
from collections import Counter

from app.rag.chunker import DocumentChunk
from app.rag.scoring import tokenize


class BM25Retriever:
    def __init__(self, chunks: list[DocumentChunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self._token_counts = [Counter(tokenize(chunk.content)) for chunk in chunks]
        self._doc_lengths = [sum(counts.values()) for counts in self._token_counts]
        self._avg_doc_length = (
            sum(self._doc_lengths) / len(self._doc_lengths) if self._doc_lengths else 0.0
        )
        self._doc_frequency = Counter[str]()
        for counts in self._token_counts:
            self._doc_frequency.update(counts.keys())

    def search(self, query: str, top_k: int = 4) -> list[DocumentChunk]:
        if not self.chunks or top_k <= 0:
            return []

        query_tokens = tokenize(query)
        scored = [
            (self._score(query_tokens, index), chunk)
            for index, chunk in enumerate(self.chunks)
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk for score, chunk in scored[:top_k] if score > 0]

    def _score(self, query_tokens: list[str], index: int) -> float:
        counts = self._token_counts[index]
        doc_length = self._doc_lengths[index]
        score = 0.0
        total_docs = len(self.chunks)

        for token in query_tokens:
            term_frequency = counts.get(token, 0)
            if term_frequency == 0:
                continue
            doc_frequency = self._doc_frequency[token]
            idf = math.log(1 + (total_docs - doc_frequency + 0.5) / (doc_frequency + 0.5))
            denominator = term_frequency + self.k1 * (
                1 - self.b + self.b * doc_length / max(self._avg_doc_length, 1.0)
            )
            score += idf * (term_frequency * (self.k1 + 1)) / denominator

        return score
