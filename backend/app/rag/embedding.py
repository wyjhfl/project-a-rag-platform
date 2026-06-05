import hashlib
import math
import re


class HashEmbedding:
    """Deterministic local embedding for a runnable v0.1 baseline."""

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
