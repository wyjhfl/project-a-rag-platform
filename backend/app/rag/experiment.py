from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from app.rag.chunker import DocumentChunk, chunk_text
from app.rag.documents import load_text_documents
from app.rag.hybrid import VectorRetriever
from app.rag.keyword import BM25Retriever
from app.rag.reranker import LocalReranker
from app.rag.rrf import reciprocal_rank_fusion
from app.rag.vector_store import ChromaVectorStore


def run_retrieval_experiment(
    docs_dir: Path,
    cases: list[dict[str, str]],
    chroma_dir: Path | None = None,
    top_k: int = 4,
    candidate_k: int = 8,
) -> dict[str, Any]:
    with TemporaryDirectory() as temp_dir:
        vector_dir = chroma_dir or Path(temp_dir) / "chroma"
        chunks = _load_chunks(docs_dir)
        vector_store = ChromaVectorStore(vector_dir, collection_name="project_a_v02_experiment")
        vector_store.reset()
        vector_store.add_chunks(chunks)

        keyword_retriever = BM25Retriever(chunks)
        vector_retriever = VectorRetriever(vector_store)
        reranker = LocalReranker()

        rows = []
        for case in cases:
            question = case["question"]
            expected_source = case.get("expected_source", "")

            vector_results = vector_retriever.search(question, top_k=top_k)
            keyword_results = keyword_retriever.search(question, top_k=candidate_k)
            hybrid_candidates = reciprocal_rank_fusion(
                [
                    keyword_results,
                    vector_retriever.search(question, top_k=candidate_k),
                ],
                top_k=candidate_k,
            )
            hybrid_results = hybrid_candidates[:top_k]
            reranked_results = reranker.rerank(question, hybrid_candidates, top_k=top_k)

            rows.append(
                {
                    "question": question,
                    "expected_source": expected_source,
                    "results": {
                        "pure_vector": _serialize_results(vector_results),
                        "hybrid": _serialize_results(hybrid_results),
                        "hybrid_rerank": _serialize_results(reranked_results),
                    },
                    "hits": {
                        "pure_vector": _contains_source(vector_results, expected_source),
                        "hybrid": _contains_source(hybrid_results, expected_source),
                        "hybrid_rerank": _contains_source(reranked_results, expected_source),
                    },
                }
            )

        strategies = ["pure_vector", "hybrid", "hybrid_rerank"]
        return {
            "summary": {
                "case_count": len(rows),
                "top_k": top_k,
                "candidate_k": candidate_k,
                "strategies": strategies,
                "top1_hit_count": {
                    strategy: _top1_hit_count(rows, strategy) for strategy in strategies
                },
                "topk_hit_count": {
                    strategy: sum(1 for row in rows if row["hits"][strategy])
                    for strategy in strategies
                },
            },
            "cases": rows,
        }


def _load_chunks(docs_dir: Path) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for document in load_text_documents(docs_dir):
        chunks.extend(
            chunk_text(
                text=document.content,
                source=document.source,
                document_id=document.document_id,
            )
        )
    return chunks


def _serialize_results(chunks: list[DocumentChunk]) -> list[dict[str, Any]]:
    return [
        {
            "source": chunk.metadata["source"],
            "chunk_index": chunk.metadata["chunk_index"],
            "content_preview": chunk.content[:120],
        }
        for chunk in chunks
    ]


def _contains_source(chunks: list[DocumentChunk], expected_source: str) -> bool:
    if not expected_source:
        return False
    return any(chunk.metadata.get("source") == expected_source for chunk in chunks)


def _top1_hit_count(rows: list[dict[str, Any]], strategy: str) -> int:
    hits = 0
    for row in rows:
        results = row["results"][strategy]
        if results and results[0]["source"] == row["expected_source"]:
            hits += 1
    return hits
