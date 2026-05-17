import re
from dataclasses import asdict, dataclass

from app.cache.redis_cache import RedisCache


@dataclass
class ConversationState:
    last_device_model: str = ""
    last_fault_code: str = ""
    last_question: str = ""


class ConversationMemory:
    """Minimal session memory for v0.5 pronoun resolution and topic continuation."""

    def __init__(self, cache: RedisCache | None = None) -> None:
        self._sessions: dict[str, ConversationState] = {}
        self.cache = cache

    def resolve_question(self, session_id: str, question: str) -> str:
        state = self._load_state(session_id)
        resolved = question
        has_pronoun = any(term in question for term in ["它", "这个", "刚才那个", "该设备"])
        if has_pronoun and (state.last_device_model or state.last_fault_code):
            prefix = " ".join(
                part for part in [state.last_device_model, state.last_fault_code] if part
            )
            resolved = f"{prefix} {question}".strip()

        self._update_state(state, resolved)
        self._save_state(session_id, state)
        return resolved

    def _load_state(self, session_id: str) -> ConversationState:
        if self.cache:
            data = self.cache.get_json(self._cache_key(session_id))
            if data:
                return ConversationState(**data)
        return self._sessions.setdefault(session_id, ConversationState())

    def _save_state(self, session_id: str, state: ConversationState) -> None:
        if self.cache:
            self.cache.set_json(self._cache_key(session_id), asdict(state))
            return
        self._sessions[session_id] = state

    def _cache_key(self, session_id: str) -> str:
        return f"project_a:conversation:{session_id}"

    def _update_state(self, state: ConversationState, question: str) -> None:
        device = self._extract_device_model(question)
        fault = self._extract_fault_code(question)
        if device:
            state.last_device_model = device
        if fault:
            state.last_fault_code = fault
        state.last_question = question

    def _extract_device_model(self, text: str) -> str:
        patterns = [
            r"\bUPS[-_]?\d+[A-Z]?\b",
            r"\bA\d{2,4}\b",
            r"\bCW\d{2,4}\b",
            r"\bPLC[-_]?[A-Z]?\d{2,4}\b",
            r"\bVFD[-_]?\d{2,4}\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(0).upper()
        return ""

    def _extract_fault_code(self, text: str) -> str:
        for match in re.finditer(r"\b[A-Z][-_]?\d{2,4}\b", text, flags=re.IGNORECASE):
            code = match.group(0).upper()
            if not code.startswith(("A", "CW", "PLC", "VFD", "UPS")):
                return code
        return ""
