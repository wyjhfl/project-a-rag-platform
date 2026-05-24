import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.cache.redis_cache import RedisCache
from app.models import ChatResponse, Citation, IngestResponse
from app.rag.agentic import AgenticRetriever, AgenticSearchResult
from app.rag.chunker import semantic_chunk_text
from app.rag.costing import TokenCostEstimator
from app.rag.documents import load_documents
from app.rag.generator import ExtractiveGenerator
from app.rag.graph import LocalGraphRetriever
from app.rag.hybrid import HybridRetriever
from app.rag.llm import LLMConfig, LLMGenerator
from app.rag.prompting import build_rag_prompt, load_prompt_template
from app.rag.query_enhancement import QueryEnhancer, QueryRoute, QueryRouter
from app.rag.rrf import reciprocal_rank_fusion
from app.rag.scoring import (
    extract_device_models,
    extract_fault_codes,
    normalize_device_text,
    score_chunk_relevance,
    tokenize,
)
from app.rag.security import PromptInjectionGuard, SecurityDecision
from app.rag.tracing import end_trace, record_trace_event, start_trace, summarize_chunks
from app.rag.vector_store import ChromaVectorStore, VectorStore
from app.storage.base import Store


@dataclass
class RagPipeline:
    chroma_dir: Path
    store: Store
    prompt_path: Path | None = None
    llm_config: LLMConfig | None = None
    graph_retriever: LocalGraphRetriever | None = None
    cache: RedisCache | None = None
    vector_store: VectorStore | None = None

    def __post_init__(self) -> None:
        self.vector_store = self.vector_store or ChromaVectorStore(self.chroma_dir)
        self.generator = ExtractiveGenerator()
        self.llm_generator = LLMGenerator(self.llm_config or LLMConfig())
        self.prompt_template = load_prompt_template(self.prompt_path) if self.prompt_path else ""
        self.hybrid_retriever: HybridRetriever | None = None
        self.query_enhancer = QueryEnhancer()
        self.query_router = QueryRouter()
        self.security_guard = PromptInjectionGuard()
        self.agentic_retriever = AgenticRetriever()
        self.cost_estimator = TokenCostEstimator()
        self.last_agentic_result: AgenticSearchResult | None = None
        self.last_trace: dict | None = None

    def ingest_directory(self, directory: Path) -> IngestResponse:
        documents = load_documents(directory)
        total_chunks = 0
        indexed_chunks = []
        self.vector_store.reset()

        for document in documents:
            chunks = semantic_chunk_text(
                text=document.content,
                source=document.source,
                document_id=document.document_id,
            )
            self.vector_store.add_chunks(chunks)
            indexed_chunks.extend(chunks)
            self.store.add_document(
                document_id=document.document_id,
                source=document.source,
                path=str(document.path),
                chunk_count=len(chunks),
            )
            total_chunks += len(chunks)

        self.hybrid_retriever = HybridRetriever.from_chunks(indexed_chunks, self.vector_store)
        if self.graph_retriever:
            self.graph_retriever.index_chunks(indexed_chunks)
        if self.cache:
            self.cache.bump_docs_version()
        return IngestResponse(document_count=len(documents), chunk_count=total_chunks)

    def answer(self, question: str, top_k: int = 4) -> ChatResponse:
        start_trace(
            "project-a-v12-rag-answer",
            {"question": question, "top_k": top_k},
        )
        security_result = self.security_guard.inspect(question)
        record_trace_event(
            "security_check",
            inputs={"question": question},
            outputs={"decision": security_result.decision.value},
        )
        if security_result.decision == SecurityDecision.BLOCK:
            blocked_answer = (
                "该问题包含疑似 Prompt 注入或越权指令，已拒绝执行。"
                "请改为描述设备型号、故障码或可见报警现象。"
            )
            response = ChatResponse(
                answer=blocked_answer,
                citations=[],
            )
            self.last_trace = end_trace()
            return response

        cache_key = self._chat_cache_key(question, top_k)
        cached = self.cache.get_json(cache_key) if self.cache else None
        if cached:
            record_trace_event(
                "cache_hit",
                inputs={"cache_key": cache_key},
                outputs={"cached": True},
            )
            response = ChatResponse.model_validate(cached)
            self.last_trace = end_trace()
            return response

        chunks = self.search(question, top_k=top_k)
        if self._is_insufficient(question, chunks):
            answer = (
                "当前资料不足，无法确认该故障的处理方式。"
                "请补充准确设备型号、故障码或上传对应设备手册。"
            )
            self.store.add_chat_record(question=question, answer=answer, citations="[]")
            response = ChatResponse(answer=answer, citations=[], insufficient=True)
            if self.cache:
                self.cache.set_json(cache_key, response.model_dump())
            record_trace_event(
                "answer_decision",
                inputs={"question": question},
                outputs={
                    "insufficient": True,
                    "llm_used": False,
                    "citation_count": 0,
                },
            )
            self.last_trace = end_trace()
            return response

        answer_chunks = self._select_answer_chunks(question, chunks, top_k=top_k)
        record_trace_event(
            "answer_context_filter",
            inputs={"question": question, "candidate_count": len(chunks)},
            outputs={"selected_chunks": summarize_chunks(answer_chunks)},
        )

        context = self._build_llm_context(answer_chunks)
        prompt_text = ""
        if self.prompt_template:
            prompt_text = build_rag_prompt(
                question=question,
                context=context,
                template=self.prompt_template,
            )

        llm_result = self.llm_generator.generate(
            question=question,
            context=context,
            prompt=prompt_text,
        )
        llm_answer = (
            llm_result.answer
            if self._accept_llm_answer(question, llm_result.answer, answer_chunks)
            else ""
        )
        llm_used = bool(llm_answer)
        answer = llm_answer or self.generator.generate(question, answer_chunks)
        safety_warning = self._needs_safety_warning(question, answer)
        if safety_warning:
            answer = self._append_safety_warning(answer)
        citations = [
            Citation(
                source=str(chunk.metadata["source"]),
                chunk_index=int(chunk.metadata["chunk_index"]),
                content=chunk.content,
            )
            for chunk in answer_chunks
        ]
        self.store.add_chat_record(
            question=question,
            answer=answer,
            citations=json.dumps(
                [citation.model_dump() for citation in citations],
                ensure_ascii=False,
            ),
        )
        self.store.add_token_usage(
            self.cost_estimator.estimate(
                module="chat",
                prompt=f"{question}\n\n{context}",
                completion=answer,
            )
        )
        response = ChatResponse(
            answer=answer,
            citations=citations,
            llm_used=llm_used,
            insufficient=False,
            safety_warning=safety_warning,
        )
        record_trace_event(
            "answer_decision",
            inputs={"question": question},
            outputs={
                "llm_used": llm_used,
                "insufficient": False,
                "safety_warning": safety_warning,
                "citations": [citation.model_dump() for citation in citations],
            },
            metadata={
                "llm_error": llm_result.error[:300],
                "agentic_quality_score": (
                    self.last_agentic_result.quality_score if self.last_agentic_result else 0.0
                ),
                "agentic_retried": (
                    self.last_agentic_result.retried if self.last_agentic_result else False
                ),
            },
        )
        if self.cache:
            self.cache.set_json(cache_key, response.model_dump())
        self.last_trace = end_trace()
        return response

    def stream_answer(self, question: str, top_k: int = 4):
        chunks = self.search(question, top_k=top_k)
        for token in self.generator.stream(question, chunks):
            yield token

    def search(self, question: str, top_k: int = 4):
        security_result = self.security_guard.inspect(question)
        if security_result.decision == SecurityDecision.BLOCK:
            return []

        result = self.agentic_retriever.search(question, self._base_search, top_k=top_k)
        self.last_agentic_result = result
        record_trace_event(
            "agentic_search",
            inputs={"question": question, "top_k": top_k},
            outputs={
                "quality_score": result.quality_score,
                "retried": result.retried,
                "rewritten_query": result.rewritten_query,
                "contradictions": result.contradictions,
                "chunks": summarize_chunks(result.chunks),
            },
        )
        return result.chunks

    def _base_search(self, question: str, top_k: int = 4):
        enhanced_query = self.query_router.build_enhanced_query(question, self.query_enhancer)
        record_trace_event(
            "query_route",
            inputs={"question": question, "top_k": top_k},
            outputs={
                "route": enhanced_query.route.value,
                "retrieval_queries": enhanced_query.retrieval_queries,
            },
        )
        if self.hybrid_retriever:
            if enhanced_query.route == QueryRoute.ENHANCED_RETRIEVAL:
                hybrid_results = self._search_multiple_queries(
                    enhanced_query.retrieval_queries,
                    top_k=top_k,
                )
            else:
                hybrid_results = self.hybrid_retriever.search(question, top_k=top_k)
            return self._fuse_graph_results(question, hybrid_results, top_k=top_k)
        vector_results = self.vector_store.search(question, top_k=top_k)
        record_trace_event(
            "vector_only_search",
            inputs={"question": question, "top_k": top_k},
            outputs={"results": summarize_chunks(vector_results)},
        )
        return vector_results

    def _fuse_graph_results(self, question: str, chunks, top_k: int = 4):
        if not self.graph_retriever:
            return chunks
        graph_chunks = self.graph_retriever.search(question, top_k=top_k)
        if not graph_chunks:
            return chunks
        fused = reciprocal_rank_fusion([chunks, graph_chunks], top_k=top_k)
        record_trace_event(
            "graph_fusion",
            inputs={"question": question, "top_k": top_k},
            outputs={
                "hybrid_chunks": summarize_chunks(chunks),
                "graph_chunks": summarize_chunks(graph_chunks),
                "fused_chunks": summarize_chunks(fused),
            },
        )
        return fused

    def _search_multiple_queries(self, queries: list[str], top_k: int = 4):
        if not self.hybrid_retriever:
            return []

        seen: set[tuple[str, int]] = set()
        merged = []
        per_query_k = max(top_k, 4)
        for query in queries:
            for chunk in self.hybrid_retriever.search(query, top_k=per_query_k):
                key = (
                    str(chunk.metadata.get("source", "")),
                    int(chunk.metadata.get("chunk_index", 0)),
                )
                if key in seen:
                    continue
                seen.add(key)
                merged.append(chunk)
                if len(merged) >= top_k:
                    return merged
        return merged

    def _is_insufficient(self, question: str, chunks) -> bool:
        if not chunks:
            return True
        device_models = extract_device_models(question)
        if not device_models:
            return False

        matched = [
            chunk
            for chunk in chunks
            if any(
                normalize_device_text(model)
                in normalize_device_text(
                    f"{chunk.metadata.get('source', '')}\n{chunk.content}"
                )
                for model in device_models
            )
        ]
        if not matched:
            return True
        if self.last_agentic_result and self.last_agentic_result.quality_score < 0.18:
            return True
        return False

    def _select_answer_chunks(self, question: str, chunks, top_k: int = 4):
        if not chunks:
            return []

        scored = sorted(
            chunks,
            key=lambda chunk: score_chunk_relevance(question, chunk),
            reverse=True,
        )
        selected_limit = max(1, min(top_k, 2))
        selected = scored[:selected_limit]
        query_fault_codes = extract_fault_codes(question)
        if query_fault_codes:
            exact_fault_match = [
                chunk
                for chunk in scored
                if any(
                    normalize_device_text(code)
                    in normalize_device_text(f"{chunk.metadata.get('source', '')}\n{chunk.content}")
                    for code in query_fault_codes
                )
            ]
            if exact_fault_match:
                return exact_fault_match[:selected_limit]

        device_models = extract_device_models(question)
        if not device_models:
            return selected

        same_device = [
            chunk
            for chunk in scored
            if any(
                normalize_device_text(model)
                in normalize_device_text(f"{chunk.metadata.get('source', '')}\n{chunk.content}")
                for model in device_models
            )
        ]
        return same_device[:selected_limit] or selected

    def _accept_llm_answer(self, question: str, answer: str, chunks) -> bool:
        cleaned = answer.strip()
        if not cleaned or not chunks:
            return False
        rejection_markers = [
            "无法访问文件",
            "未提供资料",
            "没有上下文",
            "encoding",
            "乱码",
        ]
        if any(marker.lower() in cleaned.lower() for marker in rejection_markers):
            return False

        context_text = "\n".join(
            f"{chunk.metadata.get('source', '')}\n{chunk.content}"
            for chunk in chunks
        )
        answer_tokens = {token for token in tokenize(cleaned) if len(token) > 1}
        context_tokens = {token for token in tokenize(context_text) if len(token) > 1}
        overlap = answer_tokens & context_tokens

        query_models = extract_device_models(question)
        query_fault_codes = extract_fault_codes(question)
        model_hit = not query_models or any(
            model.upper() in cleaned.upper()
            for model in query_models
        )
        code_hit = not query_fault_codes or any(
            code.upper() in cleaned.upper()
            for code in query_fault_codes
        )
        context_overlap_ok = len(overlap) >= 2 or (len(overlap) >= 1 and (model_hit or code_hit))
        partial_boundary_markers = [
            "\u5f53\u524d\u8d44\u6599\u4e0d\u8db3",
            "\u65e0\u6cd5\u786e\u8ba4",
            "\u672a\u63d0\u53ca",
            "\u672a\u5305\u542b",
            "\u9700\u7ed3\u5408\u73b0\u573a",
        ]
        action_markers = [
            "\u5efa\u8bae\u52a8\u4f5c",
            "\u6392\u67e5",
            "\u68c0\u67e5",
            "1.",
            "1\u3001",
            "1\uff0e",
        ]
        has_partial_boundary = any(marker in cleaned for marker in partial_boundary_markers)
        has_grounded_actions = any(marker in cleaned for marker in action_markers)
        if has_partial_boundary and (
            has_grounded_actions and context_overlap_ok and model_hit and code_hit
        ):
            return True

        if "当前资料不足，无法确认" in cleaned:
            return False
        return context_overlap_ok and (model_hit or code_hit or len(overlap) >= 3)

    def _build_llm_context(self, chunks) -> str:
        parts = []
        for index, chunk in enumerate(chunks, start=1):
            parts.append(
                f"资料片段 {index}\n"
                f"正文：{chunk.content}"
            )
        return "\n\n".join(parts)

    def _chat_cache_key(self, question: str, top_k: int) -> str:
        docs_version = self.cache.current_docs_version() if self.cache else 0
        normalized = re.sub(r"\s+", " ", question.strip().lower())
        digest = hashlib.sha256(f"{docs_version}:{top_k}:{normalized}".encode("utf-8")).hexdigest()
        return f"project_a:chat:{digest}"

    def _needs_safety_warning(self, question: str, answer: str) -> bool:
        dangerous_terms = [
            "冒烟",
            "异味",
            "鼓包",
            "短路",
            "带压",
            "继续带载",
            "强制重启",
            "直接重启",
        ]
        if not any(term in question for term in dangerous_terms):
            return False
        return True

    def _append_safety_warning(self, answer: str) -> str:
        warning = (
            "安全边界：该场景存在高风险，禁止直接重启或继续带载运行；"
            "应先停机、隔离现场并升级人工确认。"
        )
        if warning in answer:
            return answer
        return f"{answer}\n\n{warning}"
