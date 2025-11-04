from __future__ import annotations

import os
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict

from app.core.logger import get_logger

logger = get_logger(__name__)


def _env_value(name: str) -> str | None:
    return os.getenv(name)


def _parse_float(name: str, default: float) -> float:
    raw = _env_value(name)
    if raw is None:
        return default
    try:
        return float(str(raw).replace(",", "."))
    except ValueError:
        logger.warning("Invalid float value for %s=%r. Falling back to %s", name, raw, default)
        return default


def _parse_int(name: str, default: int) -> int:
    raw = _env_value(name)
    if raw is None:
        return default
    try:
        return int(str(raw))
    except ValueError:
        logger.warning("Invalid int value for %s=%r. Falling back to %s", name, raw, default)
        return default


def _parse_bool(name: str, default: bool) -> bool:
    raw = _env_value(name)
    if raw is None:
        return default
    if isinstance(raw, str):
        return raw.strip().lower() in {"true", "1", "yes", "y", "on"}
    return bool(raw)


def _parse_languages(default: List[str]) -> List[str]:
    raw = _env_value("SUPPORTED_LANGUAGES")
    if raw is None:
        return default
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if not parts:
        logger.warning("SUPPORTED_LANGUAGES is empty; using default %s", default)
        return default
    return parts


def _load_config() -> Dict[str, Any]:
    return {
        "app_name": "contract-extractor-api",
        "version": "0.1.0",
        "env": _env_value("ENV") or "dev",
        "ollama_host": _env_value("OLLAMA_HOST") or "http://legal-ai-ollama:11434",
        "model_name": _env_value("MODEL") or "qwen3-vl:8b-instruct",
        "temperature": _parse_float("TEMPERATURE", 0.1),
        "max_tokens": _parse_int("MAX_TOKENS", 1024),
        "numeric_tolerance": _parse_float("NUMERIC_TOLERANCE", 0.01),
        "use_llm": _parse_bool("USE_LLM", True),
        "ollama_read_timeout": _parse_float("OLLAMA_READ_TIMEOUT", 300.0),
        "supported_languages": _parse_languages(["ru", "en"]),
    }


class AppConfig(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    app_name: str
    version: str
    env: str
    ollama_host: str
    model_name: str
    temperature: float
    max_tokens: int
    numeric_tolerance: float
    use_llm: bool
    ollama_read_timeout: float
    supported_languages: List[str]


def _build_config() -> AppConfig:
    data = _load_config()
    return AppConfig.model_validate(data)


CONFIG = _build_config()
