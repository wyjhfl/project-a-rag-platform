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
from app.rag.security import PromptInjectionGuard, SecurityDecision
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
        security_result = self.security_guard.inspect(question)
        if security_result.decision == SecurityDecision.BLOCK:
            blocked_answer = (
                "该问题包含疑似 Prompt 注入或越权指令，已拒绝执行。"
                "请改为描述设备型号、故障码或可见报警现象。"
            )
            return ChatResponse(
                answer=blocked_answer,
                citations=[],
            )

        cache_key = self._chat_cache_key(question, top_k)
        cached = self.cache.get_json(cache_key) if self.cache else None
        if cached:
            return ChatResponse.model_validate(cached)

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
            return response

        context = "\n\n".join(chunk.content for chunk in chunks)
        if self.prompt_template:
            build_rag_prompt(question=question, context=context, template=self.prompt_template)

        llm_result = self.llm_generator.generate(question=question, context=context)
        llm_used = bool(llm_result.answer)
        answer = llm_result.answer or self.generator.generate(question, chunks)
        safety_warning = self._needs_safety_warning(question, answer)
        if safety_warning:
            answer = self._append_safety_warning(answer)
        citations = [
            Citation(
                source=str(chunk.metadata["source"]),
                chunk_index=int(chunk.metadata["chunk_index"]),
                content=chunk.content,
            )
            for chunk in chunks
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
        if self.cache:
            self.cache.set_json(cache_key, response.model_dump())
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
        return result.chunks

    def _base_search(self, question: str, top_k: int = 4):
        enhanced_query = self.query_router.build_enhanced_query(question, self.query_enhancer)
        if self.hybrid_retriever:
            if enhanced_query.route == QueryRoute.ENHANCED_RETRIEVAL:
                hybrid_results = self._search_multiple_queries(
                    enhanced_query.retrieval_queries,
                    top_k=top_k,
                )
            else:
                hybrid_results = self.hybrid_retriever.search(question, top_k=top_k)
            return self._fuse_graph_results(question, hybrid_results, top_k=top_k)
        return self.vector_store.search(question, top_k=top_k)

    def _fuse_graph_results(self, question: str, chunks, top_k: int = 4):
        if not self.graph_retriever:
            return chunks
        graph_chunks = self.graph_retriever.search(question, top_k=top_k)
        if not graph_chunks:
            return chunks
        return reciprocal_rank_fusion([chunks, graph_chunks], top_k=top_k)

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
        device_models = self._extract_device_models(question)
        if not device_models:
            return False

        matched = [
            chunk
            for chunk in chunks
            if any(
                self._normalize_device_text(model)
                in self._normalize_device_text(
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

    def _extract_device_models(self, text: str) -> list[str]:
        patterns = [
            r"\bUPS[-_]?\d+[A-Z]?\b",
            r"\bVFD[-_]?\d{2,4}\b",
            r"\bVFD\d{2,4}\b",
            r"\bPFX\d{2,4}\b",
            r"\bPLCLOGO\b",
            r"\bPLC\d{2,4}\b",
            r"\bPLC[-_]?[A-Z]?\d{2,4}\b",
            r"\bCW\d{2,4}\b",
            r"\bA\d{2,4}\b",
            r"\bZX[-_]?\d{2,4}\b",
        ]
        models: list[str] = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                model = match.group(0).upper()
                if model not in models:
                    models.append(model)
        return models

    def _normalize_device_text(self, text: str) -> str:
        return re.sub(r"[^A-Z0-9]", "", text.upper())

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
