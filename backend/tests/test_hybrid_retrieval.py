from app.rag.chunker import DocumentChunk
from app.rag.hybrid import HybridRetriever, VectorRetriever
from app.rag.keyword import BM25Retriever
from app.rag.reranker import LocalReranker
from app.rag.rrf import reciprocal_rank_fusion


def chunk(source: str, content: str, index: int = 0) -> DocumentChunk:
    return DocumentChunk(
        content=content,
        metadata={"source": source, "document_id": source, "chunk_index": index},
    )


def test_bm25_retriever_prioritizes_model_and_fault_code():
    chunks = [
        chunk(
            "air_compressor_a100.txt",
            "A100 空压机 E-17 表示供压异常，需要检查过滤器和压力传感器。",
        ),
        chunk(
            "plc_x200.txt",
            "PLC-X200 RUN 指示灯闪烁时，应检查 CPU 模式和 24V 供电。",
        ),
    ]

    retriever = BM25Retriever(chunks)
    results = retriever.search("A100 出现 E-17 报警怎么排查？", top_k=2)

    assert results[0].metadata["source"] == "air_compressor_a100.txt"


def test_rrf_fuses_ranked_results_without_raw_score_calibration():
    first = [
        chunk("a.txt", "alpha", 0),
        chunk("b.txt", "beta", 0),
    ]
    second = [
        chunk("b.txt", "beta", 0),
        chunk("c.txt", "gamma", 0),
    ]

    fused = reciprocal_rank_fusion([first, second], top_k=3)

    assert [item.metadata["source"] for item in fused] == ["b.txt", "a.txt", "c.txt"]


def test_local_reranker_promotes_chunk_with_more_query_terms():
    chunks = [
        chunk("generic.txt", "压力异常可能和传感器、管路、过滤器有关。"),
        chunk("air_compressor_a100.txt", "A100 空压机 E-17 供压异常，先检查过滤器。"),
    ]

    reranked = LocalReranker().rerank("A100 E-17 过滤器", chunks, top_k=2)

    assert reranked[0].metadata["source"] == "air_compressor_a100.txt"


def test_local_reranker_prefers_exact_fault_code_over_same_device_other_fault():
    chunks = [
        chunk(
            "real_vfd_4500_voltage.md",
            "VFD-4500 UV-1 表示输入欠压，应检查输入电源、接触器和进线端子。",
        ),
        chunk(
            "real_vfd_4500_voltage.md",
            "VFD-4500 OV-2 表示减速过压，应检查减速时间和制动电阻。",
            1,
        ),
    ]

    reranked = LocalReranker().rerank("VFD-4500 UV-1 需要检查哪些供电项？", chunks, top_k=2)

    assert "UV-1" in reranked[0].content


def test_hybrid_retriever_uses_keyword_vector_rrf_and_rerank(tmp_path):
    chunks = [
        chunk(
            "air_compressor_a100.txt",
            "A100 空压机 E-17 表示供压异常，需要检查过滤器和压力传感器。",
        ),
        chunk(
            "plc_x200.txt",
            "PLC-X200 RUN 指示灯闪烁时，应检查 CPU 模式和 24V 供电。",
        ),
    ]

    class FakeVectorStore:
        def search(self, query: str, top_k: int = 4) -> list[DocumentChunk]:
            return [chunks[1], chunks[0]][:top_k]

    retriever = HybridRetriever(
        keyword_retriever=BM25Retriever(chunks),
        vector_retriever=VectorRetriever(FakeVectorStore()),
        reranker=LocalReranker(),
    )

    results = retriever.search("A100 出现 E-17 报警怎么排查？", top_k=1, candidate_k=2)

    assert results[0].metadata["source"] == "air_compressor_a100.txt"
