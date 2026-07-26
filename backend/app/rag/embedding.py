import hashlib
import math
import re
from dataclasses import dataclass
from typing import Protocol

from app.rag.llm import HttpJsonClient, UrllibJsonClient


class Embedding(Protocol):
    dimension: int

    def embed_query(self, text: str) -> list[float]:
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str = ""
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    dimension: int = 384
    timeout: float = 30.0
    batch_size: int = 16

    @property
    def is_enabled(self) -> bool:
        return bool(self.model and self.api_key and self.base_url)


class ApiEmbedding:
    """OpenAI-compatible /embeddings client (works with BGE, Qwen, OpenAI, etc.)."""

    def __init__(
        self,
        config: EmbeddingConfig,
        http_client: HttpJsonClient | None = None,
    ) -> None:
        if not config.is_enabled:
            raise ValueError(
                "ApiEmbedding requires EMBEDDING_MODEL, EMBEDDING_API_KEY and EMBEDDING_BASE_URL."
            )
        self.config = config
        self.dimension = config.dimension
        self.http_client = http_client or UrllibJsonClient()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        batch_size = max(1, self.config.batch_size)
        for start in range(0, len(texts), batch_size):
            vectors.extend(self._embed_batch(texts[start : start + batch_size]))
        return vectors

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        url = self.config.base_url.rstrip("/") + "/embeddings"
        response = self.http_client.post_json(
            url=url,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            payload={"model": self.config.model, "input": texts},
            timeout=self.config.timeout,
        )
        rows = response.get("data") or []
        if len(rows) != len(texts):
            raise RuntimeError(
                f"Embedding API returned {len(rows)} vectors for {len(texts)} inputs."
            )
        ordered = sorted(rows, key=lambda row: int(row.get("index", 0)))
        vectors = [list(map(float, row.get("embedding") or [])) for row in ordered]
        for vector in vectors:
            if not vector:
                raise RuntimeError("Embedding API returned an empty vector.")
            if len(vector) != self.dimension:
                raise RuntimeError(
                    f"Embedding dimension mismatch: expected {self.dimension}, "
                    f"got {len(vector)}. Set EMBEDDING_DIMENSION to match the model."
                )
        return vectors


def build_embedding(config: EmbeddingConfig | None) -> "ApiEmbedding | HashEmbedding":
    """Prefer the configured embedding API; fall back to the deterministic local hash
    embedding so tests and offline demos stay runnable without network credentials."""
    if config and config.is_enabled:
        return ApiEmbedding(config)
    return HashEmbedding(dimension=config.dimension if config else 384)


class HashEmbedding:
    """Deterministic local fallback embedding (no network, stable across runs)."""

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def embed_query(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in self._tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def _tokens(self, text: str) -> list[str]:
        lowered = text.lower()
        code_tokens = [token.replace("-", "") for token in re.findall(r"[a-z]+-?\d+|\d+", lowered)]
        words = re.findall(r"[a-z0-9]+", lowered)
        chinese_chars = re.findall(r"[\u4e00-\u9fff]", lowered)
        chinese_bigrams = [
            "".join(chinese_chars[index : index + 2])
            for index in range(max(len(chinese_chars) - 1, 0))
        ]
        return (code_tokens * 8) + (words * 3) + chinese_chars + chinese_bigrams
