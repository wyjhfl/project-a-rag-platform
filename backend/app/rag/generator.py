from app.rag.chunker import DocumentChunk


class ExtractiveGenerator:
    """A local generator fallback that keeps v0.1 runnable without an API key."""

    def generate(self, question: str, chunks: list[DocumentChunk]) -> str:
        if not chunks:
            return "当前知识库没有检索到足够资料，无法确认该故障的处理方式。"

        sentences: list[str] = []
        for chunk in chunks:
            for sentence in self._split_sentences(chunk.content):
                if sentence not in sentences:
                    sentences.append(sentence)
                if len(sentences) >= 4:
                    break
            if len(sentences) >= 4:
                break

        body = "；".join(sentences)
        return f"根据已检索资料，建议按以下方向排查：{body}"

    def stream(self, question: str, chunks: list[DocumentChunk]):
        answer = self.generate(question, chunks)
        for index in range(0, len(answer), 12):
            yield answer[index : index + 12]

    def _split_sentences(self, text: str) -> list[str]:
        normalized = text.replace("\n", "。")
        parts = []
        for raw in normalized.replace("；", "。").replace("，", "。").split("。"):
            sentence = raw.strip()
            if sentence:
                parts.append(sentence)
        return parts
