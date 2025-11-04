from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml

from .logger import get_logger


logger = get_logger(__name__)


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"


def _load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                raise ValueError("settings.yaml должен содержать объект верхнего уровня")
            return data
    return {}


def _to_bool(value: Any, *, name: str | None = None, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    if name:
        logger.warning("Invalid boolean value for %s=%r; using %s", name, value, default)
    return default


def _safe_int(value: Any, default: int, name: str, *, minimum: int | None = None) -> int:
    if value is None:
        return default
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        logger.warning("Invalid integer for %s=%r; using %s", name, value, default)
        return default
    if minimum is not None and parsed < minimum:
        logger.warning(
            "Value for %s=%r is below minimum %s; using %s",
            name,
            parsed,
            minimum,
            default,
        )
        return default
    return parsed


def _safe_float(value: Any, default: float, name: str, *, minimum: float | None = None) -> float:
    if value is None:
        return default
    try:
        parsed = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        logger.warning("Invalid float for %s=%r; using %s", name, value, default)
        return default
    if minimum is not None and parsed < minimum:
        logger.warning(
            "Value for %s=%r is below minimum %s; using %s",
            name,
            parsed,
            minimum,
            default,
        )
        return default
    return parsed


class Settings:
    def __init__(self) -> None:
        cfg = _load_config()

        ollama_cfg = cfg.get("ollama", {}) if isinstance(cfg.get("ollama"), dict) else {}
        rag_cfg = cfg.get("rag", {}) if isinstance(cfg.get("rag"), dict) else {}
        rerank_cfg = cfg.get("reranker", {}) if isinstance(cfg.get("reranker"), dict) else {}
        startup_cfg = cfg.get("startup", {}) if isinstance(cfg.get("startup"), dict) else {}
        scoring_cfg = cfg.get("scoring", {}) if isinstance(cfg.get("scoring"), dict) else {}
        prompts_cfg = cfg.get("prompts", {}) if isinstance(cfg.get("prompts"), dict) else {}

        # Ollama
        self.OLLAMA_URL = os.getenv("OLLAMA_BASE_URL") or ollama_cfg.get("url", "http://ollama:11434")
        self.OLLAMA_MODEL = os.getenv("OLLAMA_MODEL") or ollama_cfg.get("model", "qwen2.5:7b-instruct")

        # RAG
        self.QDRANT_URL = os.getenv("QDRANT_URL") or rag_cfg.get("qdrant_url", "http://qdrant:6333")
        self.QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION") or rag_cfg.get("collection", "ru_law_m3")
        self.EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL") or rag_cfg.get("embedding_model", "BAAI/bge-m3")
        self.EMBED_DEVICE = os.getenv("EMBED_DEVICE") or rag_cfg.get("embed_device", "cuda")
        rag_top_k_raw = os.getenv("RAG_TOP_K", rag_cfg.get("top_k", 8))
        self.RAG_TOP_K = _safe_int(rag_top_k_raw, 8, "RAG_TOP_K", minimum=1)

        # Reranker
        rerank_enable_env = os.getenv("RERANK_ENABLE")
        rerank_debug_env = os.getenv("RERANK_DEBUG")
        self.RERANK_ENABLE = _to_bool(
            rerank_enable_env if rerank_enable_env is not None else rerank_cfg.get("enable", True),
            name="RERANK_ENABLE",
            default=True,
        )
        self.RERANKER_MODEL = os.getenv("RERANKER_MODEL") or rerank_cfg.get("model", "BAAI/bge-reranker-v2-m3")
        self.RERANK_DEVICE = os.getenv("RERANK_DEVICE") or rerank_cfg.get("device", "cuda")
        rerank_keep_raw = os.getenv("RERANK_KEEP", rerank_cfg.get("keep", 5))
        self.RERANK_KEEP = _safe_int(rerank_keep_raw, 5, "RERANK_KEEP", minimum=1)
        rerank_batch_raw = os.getenv("RERANK_BATCH", rerank_cfg.get("batch", 16))
        self.RERANK_BATCH = _safe_int(rerank_batch_raw, 16, "RERANK_BATCH", minimum=1)
        self.RERANK_DEBUG = _to_bool(
            rerank_debug_env if rerank_debug_env is not None else rerank_cfg.get("debug", False),
            name="RERANK_DEBUG",
            default=False,
        )

        # Startup flags
        startup_checks_env = os.getenv("STARTUP_CHECKS")
        self.STARTUP_CHECKS = _to_bool(
            startup_checks_env if startup_checks_env is not None else startup_cfg.get("checks", True),
            name="STARTUP_CHECKS",
            default=True,
        )
        self_check_timeout_raw = os.getenv("SELF_CHECK_TIMEOUT", startup_cfg.get("self_check_timeout", 5))
        self.SELF_CHECK_TIMEOUT = _safe_int(self_check_timeout_raw, 5, "SELF_CHECK_TIMEOUT", minimum=1)
        self_check_gen_env = os.getenv("SELF_CHECK_GEN")
        self.SELF_CHECK_GEN = _to_bool(
            self_check_gen_env if self_check_gen_env is not None else startup_cfg.get("self_check_gen", False),
            name="SELF_CHECK_GEN",
            default=False,
        )
        startup_cuda_env = os.getenv("STARTUP_CUDA_NAME")
        self.STARTUP_CUDA_NAME = _to_bool(
            startup_cuda_env if startup_cuda_env is not None else startup_cfg.get("cuda_name", True),
            name="STARTUP_CUDA_NAME",
            default=True,
        )

        # Scoring / UI
        self.SCORING_MODE = os.getenv("SCORING_MODE") or scoring_cfg.get("mode", "strict")
        score_green_raw = os.getenv("SCORE_GREEN", scoring_cfg.get("score_green", 75))
        self.SCORE_GREEN = _safe_int(score_green_raw, 75, "SCORE_GREEN", minimum=1)
        score_yellow_raw = os.getenv("SCORE_YELLOW", scoring_cfg.get("score_yellow", 51))
        self.SCORE_YELLOW = _safe_int(score_yellow_raw, 51, "SCORE_YELLOW", minimum=1)
        business_max_tokens_raw = os.getenv("BUSINESS_MAX_TOKENS", scoring_cfg.get("business_max_tokens", 1400))
        self.BUSINESS_MAX_TOKENS = _safe_int(
            business_max_tokens_raw,
            1400,
            "BUSINESS_MAX_TOKENS",
            minimum=128,
        )
        business_retry_raw = os.getenv("BUSINESS_RETRY_STEP", scoring_cfg.get("business_retry_step", 400))
        self.BUSINESS_RETRY_STEP = _safe_int(
            business_retry_raw,
            400,
            "BUSINESS_RETRY_STEP",
            minimum=32,
        )

        # Prompts configuration
        prompt_dir_env = os.getenv("PROMPTS_DIR")
        if prompt_dir_env:
            prompt_dir = Path(prompt_dir_env)
        else:
            dir_from_cfg = prompts_cfg.get("dir")
            prompt_dir = Path(dir_from_cfg) if dir_from_cfg else BASE_DIR / "prompts"
        if not prompt_dir.is_absolute():
            prompt_dir = (BASE_DIR / prompt_dir).resolve()
        self.PROMPTS_DIR = prompt_dir
        self.PROMPTS: Dict[str, str] = {
            "analyze_system": prompts_cfg.get("analyze_system", "analyze_system.txt"),
            "analyze_user": prompts_cfg.get("analyze_user", "analyze_user.txt"),
            "analyze_system_lenient_rule": prompts_cfg.get(
                "analyze_system_lenient_rule", "analyze_system_lenient_rule.txt"
            ),
            "business_system": prompts_cfg.get("business_system", "business_system.txt"),
            "business_user": prompts_cfg.get("business_user", "business_user.txt"),
            "overview_system": prompts_cfg.get("overview_system", "overview_system.txt"),
            "overview_user": prompts_cfg.get("overview_user", "overview_user.txt"),
        }


settings = Settings()
