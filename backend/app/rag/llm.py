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

    def generate(self, question: str, context: str) -> LLMGenerationResult:
        if not self.is_enabled:
            return LLMGenerationResult(answer="", error="LLM is not configured")

        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是企业设备售后诊断 RAG 助手。只能基于给定资料回答；"
                        "资料不足时必须明确说当前资料不足，无法确认。"
                        "危险操作必须提示停机、隔离、禁止直接重启并升级人工确认。"
                    ),
                },
                {
                    "role": "user",
                    "content": f"问题：{question}\n\n资料：\n{context}",
                },
            ],
            "temperature": 0.2,
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
            answer = _extract_answer(response)
            usage = response.get("usage", {})
            return LLMGenerationResult(
                answer=answer,
                prompt_tokens=int(usage.get("prompt_tokens", 0)),
                completion_tokens=int(usage.get("completion_tokens", 0)),
                total_tokens=int(usage.get("total_tokens", 0)),
            )
        except Exception as exc:
            return LLMGenerationResult(answer="", error=str(exc))


def _extract_answer(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return str(message.get("content", "")).strip()
