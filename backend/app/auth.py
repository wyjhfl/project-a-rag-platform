import logging

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from app.config import Settings, get_settings

logger = logging.getLogger("project_a")

ROLE_HIERARCHY: dict[str, int] = {"viewer": 0, "operator": 1, "admin": 2}

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_settings_dep = Depends(get_settings)


def _configured_keys(settings: Settings) -> dict[str, str]:
    keys: dict[str, str] = {}
    if settings.viewer_api_key:
        keys[settings.viewer_api_key] = "viewer"
    if settings.operator_api_key:
        keys[settings.operator_api_key] = "operator"
    if settings.admin_api_key:
        keys[settings.admin_api_key] = "admin"
    return keys


def _key_to_role(api_key: str | None, settings: Settings) -> str | None:
    if not api_key:
        return None
    return _configured_keys(settings).get(api_key)


def require_role(min_role: str):
    def dependency(
        x_api_key: str | None = Depends(_api_key_header),
        settings: Settings = _settings_dep,
    ) -> str:
        if not settings.auth_enabled:
            return "viewer"

        if not _configured_keys(settings):
            raise HTTPException(
                status_code=503,
                detail="Auth is enabled but no API keys are configured",
            )

        if not x_api_key:
            raise HTTPException(status_code=401, detail="Missing API key")

        role = _key_to_role(x_api_key, settings)
        if role is None:
            logger.info("auth failed: invalid key")
            raise HTTPException(status_code=401, detail="Invalid API key")

        if ROLE_HIERARCHY.get(role, -1) < ROLE_HIERARCHY.get(min_role, 99):
            logger.info("auth failed: role=%s requires=%s", role, min_role)
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        logger.info("auth ok: role=%s", role)
        return role

    return dependency
