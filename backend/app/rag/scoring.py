import re
from collections import Counter

from app.rag.chunker import DocumentChunk


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    code_tokens = [token.replace("-", "") for token in re.findall(r"[a-z]+-?\d+|\d+", lowered)]
    words = re.findall(r"[a-z0-9]+", lowered)
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", lowered)
    chinese_bigrams = [
        "".join(chinese_chars[index : index + 2])
        for index in range(max(len(chinese_chars) - 1, 0))
    ]
    return code_tokens + words + chinese_chars + chinese_bigrams


def extract_fault_codes(text: str) -> list[str]:
    raw_codes = re.findall(r"\b[A-Z]{1,6}[-_]?\d{1,4}\b", text.upper())
    filtered: list[str] = []
    for code in raw_codes:
        if code.startswith(("UPS", "VFD", "PLC", "CW", "ZX", "PFX")):
            continue
        if re.fullmatch(r"A\d{2,4}", code):
            continue
        if code not in filtered:
            filtered.append(code)
    return filtered


def extract_device_models(text: str) -> list[str]:
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


def normalize_device_text(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def score_chunk_relevance(query: str, chunk: DocumentChunk) -> float:
    query_counts = Counter(tokenize(query))
    if not query_counts:
        return 0.0

    haystack = f"{chunk.metadata.get('source', '')}\n{chunk.content}"
    haystack_counts = Counter(tokenize(haystack))
    overlap = sum(
        min(count, haystack_counts.get(token, 0))
        for token, count in query_counts.items()
    )

    query_models = extract_device_models(query)
    query_fault_codes = extract_fault_codes(query)
    chunk_fault_codes = extract_fault_codes(haystack)

    device_bonus = sum(
        3.0
        for model in query_models
        if normalize_device_text(model) in normalize_device_text(haystack)
    )
    fault_bonus = sum(
        5.0
        for code in query_fault_codes
        if normalize_device_text(code) in normalize_device_text(haystack)
    )
    mismatched_fault_penalty = 0.0
    if query_fault_codes and chunk_fault_codes and not fault_bonus:
        mismatched_fault_penalty = 4.0

    intent_bonus = _intent_bonus(query, haystack)
    return overlap + device_bonus + fault_bonus + intent_bonus - mismatched_fault_penalty


def _intent_bonus(query: str, haystack: str) -> float:
    bonus = 0.0
    intent_groups = [
        (["复测", "确认", "稳定"], ["复测", "空载", "带载", "观察", "曲线", "记录"]),
        (["是否", "建议", "可以", "能不能"], ["禁止", "不建议", "可以", "必须", "先"]),
        (["备件", "部件"], ["备件", "过滤器", "传感器", "密封件", "风扇", "接触器"]),
    ]
    for query_terms, chunk_terms in intent_groups:
        if any(term in query for term in query_terms):
            bonus += sum(0.8 for term in chunk_terms if term in haystack)
    return bonus
