from app.rag.chunker import DocumentChunk
from app.rag.scoring import score_chunk_relevance


class ExtractiveGenerator:
    """A local generator fallback that keeps the public chain runnable without an API key."""

    def generate(self, question: str, chunks: list[DocumentChunk]) -> str:
        if not chunks:
            return "当前知识库没有检索到足够资料，无法确认该故障的处理方式。"

        conclusion = self._build_conclusion(question, chunks)
        sentences = self._select_sentences(question, chunks)
        body = "；".join(sentences)
        return f"{conclusion}{body}"

    def stream(self, question: str, chunks: list[DocumentChunk]):
        answer = self.generate(question, chunks)
        for index in range(0, len(answer), 12):
            yield answer[index : index + 12]

    def _select_sentences(self, question: str, chunks: list[DocumentChunk]) -> list[str]:
        ranked_chunks = sorted(
            chunks,
            key=lambda chunk: score_chunk_relevance(question, chunk),
            reverse=True,
        )
        scored_sentences: list[tuple[float, str]] = []
        seen: set[str] = set()
        for chunk in ranked_chunks:
            for sentence in self._split_sentences(chunk.content):
                sentence = sentence.strip(" -")
                if not sentence or sentence in seen:
                    continue
                seen.add(sentence)
                score = score_chunk_relevance(
                    question,
                    DocumentChunk(content=sentence, metadata=chunk.metadata),
                )
                if len(sentence) <= 6:
                    score -= 1.5
                if any(marker in sentence for marker in ["处理步骤", "排查步骤", "建议", "检查"]):
                    score += 0.6
                scored_sentences.append((score, sentence))

        scored_sentences.sort(key=lambda item: item[0], reverse=True)
        selected = [sentence for _, sentence in scored_sentences[:4]]
        if selected:
            return selected
        return [self._split_sentences(ranked_chunks[0].content)[0]]

    def _build_conclusion(self, question: str, chunks: list[DocumentChunk]) -> str:
        best_chunk = max(chunks, key=lambda chunk: score_chunk_relevance(question, chunk))
        best_text = best_chunk.content
        if any(term in question for term in ["是否", "建议", "可以", "能不能"]):
            if any(term in best_text for term in ["禁止", "不建议", "不得", "严禁"]):
                return "根据已检索资料，结论是不建议直接执行该操作；建议先按以下依据处理："
            if any(term in best_text for term in ["可以", "建议", "应先", "先"]):
                return "根据已检索资料，结论是可以在满足前置条件后处理；建议先按以下依据确认："
        if any(term in question for term in ["复测", "确认", "稳定"]):
            return "根据已检索资料，建议按以下复测与确认步骤执行："
        if any(term in question for term in ["备件", "部件"]):
            return "根据已检索资料，优先关注以下备件与检查点："
        return "根据已检索资料，建议按以下方向排查："

    def _split_sentences(self, text: str) -> list[str]:
        normalized = (
            text.replace("\n", "。")
            .replace("；", "。")
            .replace(";", "。")
            .replace("？", "。")
            .replace("!", "。")
        )
        parts = []
        for raw in normalized.split("。"):
            sentence = raw.strip()
            if sentence:
                parts.append(sentence)
        return parts
