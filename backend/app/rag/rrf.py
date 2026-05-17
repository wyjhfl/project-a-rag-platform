from app.rag.chunker import DocumentChunk


def reciprocal_rank_fusion(
    ranked_results: list[list[DocumentChunk]],
    top_k: int = 4,
    rank_constant: int = 60,
) -> list[DocumentChunk]:
    scores: dict[str, float] = {}
    chunks_by_key: dict[str, DocumentChunk] = {}

    for results in ranked_results:
        for rank, chunk in enumerate(results, start=1):
            key = chunk_key(chunk)
            chunks_by_key.setdefault(key, chunk)
            scores[key] = scores.get(key, 0.0) + 1.0 / (rank_constant + rank)

    ordered_keys = sorted(scores, key=lambda key: scores[key], reverse=True)
    return [chunks_by_key[key] for key in ordered_keys[:top_k]]


def chunk_key(chunk: DocumentChunk) -> str:
    source = chunk.metadata.get("source", "")
    index = chunk.metadata.get("chunk_index", "")
    document_id = chunk.metadata.get("document_id", source)
    return f"{document_id}:{source}:{index}"
