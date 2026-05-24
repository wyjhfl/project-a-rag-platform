import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "xiaomi_mimo"
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    timeout: float = 45.0
    temperature: float = 0.0
    max_tokens: int = 700


@dataclass(frozen=True)
class LLMGenerationResult:
    answer: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    error: str = ""


class HttpJsonClient(Protocol):
    def post_json(self, url: str, headers: dict, payload: dict, timeout: float) -> dict:
        ...


class UrllibJsonClient:
    def post_json(self, url: str, headers: dict, payload: dict, timeout: float) -> dict:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM HTTP {exc.code}: {body}") from exc


class LLMGenerator:
    def __init__(
        self,
        config: LLMConfig,
        http_client: HttpJsonClient | None = None,
    ) -> None:
        self.config = config
        self.http_client = http_client or UrllibJsonClient()

    @property
    def is_enabled(self) -> bool:
        return bool(self.config.api_key and self.config.base_url and self.config.model)

    def generate(self, question: str, context: str, prompt: str = "") -> LLMGenerationResult:
        if not self.is_enabled:
            return LLMGenerationResult(answer="", error="LLM is not configured")

        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": _system_prompt(),
                },
                {
                    "role": "user",
                    "content": prompt.strip() or _build_user_prompt(question, context),
                },
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        url = self.config.base_url.rstrip("/") + "/chat/completions"

        try:
            response = self.http_client.post_json(
                url=url,
                headers=headers,
                payload=payload,
                timeout=self.config.timeout,
            )
            answer = _normalize_answer(_extract_answer(response))
            usage = response.get("usage", {})
            return LLMGenerationResult(
                answer=answer,
                prompt_tokens=int(usage.get("prompt_tokens", 0)),
                completion_tokens=int(usage.get("completion_tokens", 0)),
                total_tokens=int(usage.get("total_tokens", 0)),
            )
        except Exception as exc:
            return LLMGenerationResult(answer="", error=str(exc))


def _system_prompt() -> str:
    return (
        "你是企业设备售后诊断 RAG 助手。"
        "只能基于给定资料回答，不要补充资料中没有的结论。"
        "如果用户消息里已经给出了“资料”段落，你必须把它视为已提供资料。"
        "来源标签只是片段标识，不代表需要访问外部文件。"
        "禁止说“未提供资料”“无法访问文件”或“没有上下文”，除非资料段落本身为空。"
        "如果资料不足，明确说明“当前资料不足，无法确认”，不要猜测。"
        "如果问题涉及危险操作，必须先给出停机、隔离、禁止直接重启并升级人工确认的结论。"
        "请优先使用中文，并尽量按“结论：...\\n依据：...\\n建议动作：...”的结构回答。"
    )


def _build_user_prompt(question: str, context: str) -> str:
    return (
        "下面是已经完整贴给你的排障资料片段，请直接基于这些文字回答。\n"
        "其中“来源标签”只是引用标识，不需要访问任何外部文件。\n"
        "如果下面资料已经足够，就不要再说“未提供资料”或“无法访问文件”。\n\n"
        f"已提供资料开始\n{context}\n已提供资料结束\n\n"
        f"用户问题：{question}\n\n"
        "请输出：\n"
        "结论：一句话先回答用户问题。\n"
        "依据：引用资料中的关键信息。\n"
        "建议动作：给出排查或处理步骤。"
    )


def _extract_answer(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(part for part in parts if part).strip()
    return str(content).strip()


def _normalize_answer(answer: str) -> str:
    cleaned = answer.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    for prefix in ["回答：", "答复：", "输出："]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip()
    return cleaned
