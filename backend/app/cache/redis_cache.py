import json
from dataclasses import dataclass
from typing import Any, Protocol


class RedisClient(Protocol):
    def ping(self):
        ...

    def get(self, key: str):
        ...

    def setex(self, key: str, seconds: int, value: str):
        ...

    def incr(self, key: str):
        ...


@dataclass(frozen=True)
class RedisCacheConfig:
    enabled: bool = False
    url: str = ""
    ttl_seconds: int = 1800
    docs_version_key: str = "project_a:docs_version"


class RedisCache:
    def __init__(
        self,
        config: RedisCacheConfig,
        client: RedisClient | None = None,
    ) -> None:
        self.config = config
        self.client = client or self._create_client(config)
        self.client.ping()

    def get_json(self, key: str) -> Any | None:
        raw = self.client.get(key)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(str(raw))

    def set_json(self, key: str, value: Any) -> None:
        self.client.setex(
            key,
            self.config.ttl_seconds,
            json.dumps(value, ensure_ascii=False),
        )

    def current_docs_version(self) -> int:
        raw = self.client.get(self.config.docs_version_key)
        if raw is None:
            return 0
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return int(raw)

    def bump_docs_version(self) -> int:
        return int(self.client.incr(self.config.docs_version_key))

    def _create_client(self, config: RedisCacheConfig) -> RedisClient:
        if config.enabled and not config.url:
            raise ValueError("CACHE_ENABLED=true requires REDIS_URL.")
        if not config.enabled:
            raise ValueError("RedisCache requires CACHE_ENABLED=true.")
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError(
                "Redis package is not installed. Install dependency 'redis'."
            ) from exc
        return redis.Redis.from_url(config.url, decode_responses=True)
