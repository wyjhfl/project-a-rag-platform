import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentChunk:
    content: str
    metadata: dict[str, str | int]


def chunk_text(
    text: str,
    source: str,
    document_id: str,
    chunk_size: int = 600,
    overlap: int = 120,
) -> list[DocumentChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap 必须大于等于 0 且小于 chunk_size")

    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    chunks: list[DocumentChunk] = []
    start = 0

    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        content = normalized[start:end]
        chunks.append(
            DocumentChunk(
                content=content,
                metadata={
                    "source": source,
                    "document_id": document_id,
                    "chunk_index": len(chunks),
                },
            )
        )
        if end == len(normalized):
            break
        start = end - overlap

    return chunks


def semantic_chunk_text(
    text: str,
    source: str,
    document_id: str,
    default_section: str = "未分节",
) -> list[DocumentChunk]:
    normalized_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not normalized_lines:
        return []

    chunks: list[DocumentChunk] = []
    section = default_section
    buffer: list[str] = []

    def flush_buffer() -> None:
        if not buffer:
            return
        chunks.append(
            DocumentChunk(
                content="\n".join(buffer),
                metadata={
                    "source": source,
                    "document_id": document_id,
                    "chunk_index": len(chunks),
                    "section": section,
                    "chunk_strategy": "semantic",
                },
            )
        )
        buffer.clear()

    for line in normalized_lines:
        heading = _extract_heading(line)
        if heading:
            flush_buffer()
            section = heading
            continue

        if _is_markdown_table_row(line):
            flush_buffer()
            if set(line.replace("|", "").strip()) <= {"-", ":"}:
                continue
            if not _looks_like_fault_code_entry(line):
                continue
            chunks.append(
                DocumentChunk(
                    content=line,
                    metadata={
                        "source": source,
                        "document_id": document_id,
                        "chunk_index": len(chunks),
                        "section": section,
                        "chunk_strategy": "semantic_table_row",
                    },
                )
            )
            continue

        if _looks_like_fault_code_entry(line):
            flush_buffer()
            chunks.append(
                DocumentChunk(
                    content=line,
                    metadata={
                        "source": source,
                        "document_id": document_id,
                        "chunk_index": len(chunks),
                        "section": section,
                        "chunk_strategy": "semantic_fault_code",
                    },
                )
            )
            continue

        buffer.append(line)

    flush_buffer()
    return chunks


def _extract_heading(line: str) -> str | None:
    markdown_heading = re.match(r"^#{1,6}\s+(.+)$", line)
    if markdown_heading:
        return markdown_heading.group(1).strip()
    if re.match(r"^(第[一二三四五六七八九十0-9]+[章节]|[0-9]+(?:\.[0-9]+)*)\s+", line):
        return line.strip()
    return None


def _is_markdown_table_row(line: str) -> bool:
    return line.startswith("|") and line.endswith("|") and line.count("|") >= 2


def _looks_like_fault_code_entry(line: str) -> bool:
    return bool(re.search(r"\b[A-Z]{0,4}[-_]?\d{2,4}\b", line))
