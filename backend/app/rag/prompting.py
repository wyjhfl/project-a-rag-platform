from pathlib import Path

try:
    from langchain_core.prompts import PromptTemplate
except Exception:  # pragma: no cover - defensive fallback for broken envs
    PromptTemplate = None


DEFAULT_TEMPLATE = """你是企业设备售后诊断助手。
只能根据给定资料回答。资料不足时说明无法确认，不要编造。

资料：
{context}

用户问题：
{question}

请输出排查建议，并保留可追溯引用。"""


def load_prompt_template(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return DEFAULT_TEMPLATE


def build_rag_prompt(question: str, context: str, template: str = DEFAULT_TEMPLATE) -> str:
    if PromptTemplate is None:
        return template.format(question=question, context=context)
    prompt = PromptTemplate.from_template(template)
    return prompt.format(question=question, context=context)
