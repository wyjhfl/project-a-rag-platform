import re
from dataclasses import dataclass, field
from typing import Callable

from app.rag.chunker import DocumentChunk

SearchFn = Callable[[str, int], list[DocumentChunk]]


@dataclass(frozen=True)
class AgenticSearchResult:
    chunks: list[DocumentChunk]
    quality_score: float
    retried: bool = False
    rewritten_query: str = ""
    contradictions: list[str] = field(default_factory=list)


class AgenticRetriever:
    """Small v0.5 retrieval controller: judge, rewrite, retry, then flag conflicts."""

    def search(self, question: str, search_fn: SearchFn, top_k: int = 4) -> AgenticSearchResult:
        first_chunks = search_fn(question, top_k)
        first_score = self._quality_score(question, first_chunks)
        chunks = self._prioritize_same_device(question, first_chunks)
        retried = False
        rewritten_query = ""
        best_score = first_score

        if first_score < 0.34:
            retried = True
            rewritten_query = self.rewrite_query(question)
            retry_chunks = search_fn(rewritten_query, top_k)
            retry_score = self._quality_score(question, retry_chunks)
            chunks = self._prioritize_same_device(
                question,
                self._merge_chunks(retry_chunks, first_chunks, top_k=top_k),
            )
            best_score = max(first_score, retry_score)

        return AgenticSearchResult(
            chunks=chunks[:top_k],
            quality_score=round(best_score, 4),
            retried=retried,
            rewritten_query=rewritten_query,
            contradictions=self.detect_contradictions(chunks),
        )

    def rewrite_query(self, question: str) -> str:
        tokens = self._tokens(question)
        hints = []
        if any(token.startswith("A") for token in tokens) or "空压机" in question:
            hints.append("空压机")
        if "UPS" in question.upper() or "电池" in question:
            hints.append("UPS 电池")
        if any(term in question for term in ["过热", "过温", "温度", "跳停"]):
            hints.append("过温 跳停 排查")
        if any(term in question for term in ["冒烟", "异味", "鼓包"]):
            hints.append("高风险 停机 人工升级")
        return " ".join([question, *hints]).strip()

    def detect_contradictions(self, chunks: list[DocumentChunk]) -> list[str]:
        text = "\n".join(chunk.content for chunk in chunks)
        has_stop = any(term in text for term in ["停机", "断电", "禁止重启", "升级人工"])
        has_restart = any(term in text for term in ["可以重启", "重启观察", "继续运行"])
        if has_stop and has_restart:
            return ["检索上下文同时出现停机/升级人工与重启/继续运行建议，需要人工交叉验证。"]
        return []

    def _quality_score(self, question: str, chunks: list[DocumentChunk]) -> float:
        if not chunks:
            return 0.0
        query_tokens = set(self._tokens(question))
        if not query_tokens:
            return 0.0
        context_tokens = set(self._tokens("\n".join(chunk.content for chunk in chunks)))
        overlap = query_tokens & context_tokens
        source_bonus = 0.12 if self._source_matches(question, chunks) else 0.0
        return min(1.0, len(overlap) / len(query_tokens) + source_bonus)

    def _source_matches(self, question: str, chunks: list[DocumentChunk]) -> bool:
        normalized_question = question.lower()
        for chunk in chunks:
            source = str(chunk.metadata.get("source", "")).lower()
            for token in self._tokens(normalized_question):
                if len(token) >= 3 and token.lower() in source:
                    return True
        return False

    def _merge_chunks(
        self,
        primary: list[DocumentChunk],
        secondary: list[DocumentChunk],
        top_k: int,
    ) -> list[DocumentChunk]:
        seen: set[tuple[str, int]] = set()
        merged: list[DocumentChunk] = []
        for chunk in [*primary, *secondary]:
            key = (
                str(chunk.metadata.get("source", "")),
                int(chunk.metadata.get("chunk_index", 0)),
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(chunk)
            if len(merged) >= top_k:
                break
        return merged

    def _prioritize_same_device(
        self,
        question: str,
        chunks: list[DocumentChunk],
    ) -> list[DocumentChunk]:
        device_models = self._extract_device_models(question)
        if not device_models or not chunks:
            return chunks

        matched = [
            chunk
            for chunk in chunks
            if self._chunk_matches_any_device(chunk, device_models)
        ]
        if not matched:
            return chunks
        return sorted(
            matched,
            key=lambda chunk: self._specificity_score(question, chunk),
            reverse=True,
        )

    def _chunk_matches_any_device(
        self,
        chunk: DocumentChunk,
        device_models: list[str],
    ) -> bool:
        source = str(chunk.metadata.get("source", ""))
        haystack = self._normalize_device_text(f"{source}\n{chunk.content}")
        return any(self._normalize_device_text(device) in haystack for device in device_models)

    def _specificity_score(self, question: str, chunk: DocumentChunk) -> float:
        haystack = f"{chunk.metadata.get('source', '')}\n{chunk.content}"
        normalized_haystack = self._normalize_device_text(haystack)
        score = 0.0
        for model in self._extract_device_models(question):
            if self._normalize_device_text(model) in normalized_haystack:
                score += 3.0
        for code in self._extract_fault_codes(question):
            normalized_code = self._normalize_device_text(code)
            if normalized_code in normalized_haystack:
                score += 4.0
            if re.search(rf"故障代码\s*{re.escape(code)}", haystack, flags=re.IGNORECASE):
                score += 5.0
        if any(term in haystack for term in ["故障代码", "报警", "排查步骤"]):
            score += 1.0
        return score

    def _extract_fault_codes(self, text: str) -> list[str]:
        codes: list[str] = []
        for match in re.finditer(r"\b[A-Z][-_]?\d{2,4}\b", text, flags=re.IGNORECASE):
            code = match.group(0).upper()
            if code.startswith(("A", "CW", "PLC", "VFD", "UPS", "ZX")):
                continue
            if code not in codes:
                codes.append(code)
        return codes

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

    def _tokens(self, text: str) -> list[str]:
        ascii_tokens = re.findall(r"[A-Za-z]+[-_]?\d*|\d{2,4}", text.upper())
        chinese_terms = [
            term
            for term in [
                "空压机",
                "冷水机",
                "变频器",
                "电池",
                "冒烟",
                "异味",
                "过热",
                "过温",
                "跳停",
                "报警",
                "散热器",
                "重启",
                "停机",
                "人工",
            ]
            if term in text
        ]
        return ascii_tokens + chinese_terms
