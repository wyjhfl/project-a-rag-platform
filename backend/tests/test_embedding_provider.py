import pytest
from app.rag.embedding import ApiEmbedding, EmbeddingConfig, HashEmbedding, build_embedding


class FakeHttpClient:
    def __init__(self, dimension: int = 4) -> None:
        self.dimension = dimension
        self.calls: list[dict] = []

    def post_json(self, url: str, headers: dict, payload: dict, timeout: float) -> dict:
        self.calls.append({"url": url, "headers": headers, "payload": payload})
        return {
            "data": [
                {"index": index, "embedding": [float(index + 1)] * self.dimension}
                for index in range(len(payload["input"]))
            ]
        }


def _config(**overrides) -> EmbeddingConfig:
    defaults = dict(
        provider="openai_compatible",
        model="bge-m3",
        api_key="test-key-placeholder",
        base_url="https://embedding.example.com/v1",
        dimension=4,
        batch_size=2,
    )
    defaults.update(overrides)
    return EmbeddingConfig(**defaults)


def test_api_embedding_posts_openai_compatible_payload():
    client = FakeHttpClient()
    embedding = ApiEmbedding(_config(), http_client=client)

    vectors = embedding.embed_documents(["chunk one", "chunk two"])

    assert len(vectors) == 2
    assert all(len(vector) == 4 for vector in vectors)
    call = client.calls[0]
    assert call["url"] == "https://embedding.example.com/v1/embeddings"
    assert call["headers"]["Authorization"] == "Bearer test-key-placeholder"
    assert call["payload"] == {"model": "bge-m3", "input": ["chunk one", "chunk two"]}


def test_api_embedding_batches_requests():
    client = FakeHttpClient()
    embedding = ApiEmbedding(_config(batch_size=2), http_client=client)

    vectors = embedding.embed_documents(["a", "b", "c"])

    assert len(vectors) == 3
    assert len(client.calls) == 2
    assert client.calls[0]["payload"]["input"] == ["a", "b"]
    assert client.calls[1]["payload"]["input"] == ["c"]


def test_api_embedding_rejects_dimension_mismatch():
    client = FakeHttpClient(dimension=8)
    embedding = ApiEmbedding(_config(dimension=4), http_client=client)

    with pytest.raises(RuntimeError, match="dimension mismatch"):
        embedding.embed_query("VFD-4500 OC-17")


def test_api_embedding_requires_full_configuration():
    with pytest.raises(ValueError):
        ApiEmbedding(_config(api_key=""))


def test_build_embedding_falls_back_to_hash_when_not_configured():
    embedding = build_embedding(EmbeddingConfig())
    assert isinstance(embedding, HashEmbedding)
    assert embedding.dimension == 384

    configured = build_embedding(_config())
    assert isinstance(configured, ApiEmbedding)


def test_hash_embedding_stays_deterministic():
    embedding = HashEmbedding()
    first = embedding.embed_query("A100 E-17 报警")
    second = embedding.embed_query("A100 E-17 报警")
    assert first == second
    assert len(first) == embedding.dimension
