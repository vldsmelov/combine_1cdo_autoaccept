"""Маршруты статуса и конфигурации приложения."""

from fastapi import APIRouter, Depends, HTTPException

from ...dependencies import container_dependency
from ...application import AppContainer

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz(container: AppContainer = Depends(container_dependency)) -> dict:
    """Базовая проверка доступности сервиса."""

    return {"status": "ok", "version": container.config.version}


@router.get("/health")
async def health(container: AppContainer = Depends(container_dependency)) -> dict:
    """Alias для обратной совместимости с внешними оркестраторами."""

    return await healthz(container)  # type: ignore[arg-type]


@router.get("/status")
async def status(container: AppContainer = Depends(container_dependency)) -> dict:
    """Возвращает информацию о конфигурации LLM-клиента."""

    config = container.config
    return {
        "status": "ok",
        "use_llm": config.use_llm,
        "model": config.model_name,
        "ollama_host": config.ollama_host,
        "supported_languages": config.supported_languages,
    }


@router.get("/config")
async def get_config(container: AppContainer = Depends(container_dependency)) -> dict:
    """Возвращает полную конфигурацию приложения."""

    return container.config.model_dump()


@router.get("/schema")
async def get_schema(container: AppContainer = Depends(container_dependency)) -> dict:
    """Возвращает схему данных, используемую валидатором."""

    return container.schema


@router.get("/models")
async def get_models(container: AppContainer = Depends(container_dependency)):
    """Запрашивает список моделей у Ollama."""

    try:
        return await container.client.list_models()
    except Exception as exc:  # pragma: no cover - зависимость от внешней системы
        raise HTTPException(status_code=502, detail=f"Ollama error: {exc}") from exc


@router.get("/version")
async def version(container: AppContainer = Depends(container_dependency)) -> dict:
    """Возвращает версию сервиса и имя приложения."""

    return {"version": container.config.version, "app": container.config.app_name}


@router.get("/llmcherck")
async def llmcherck(container: AppContainer = Depends(container_dependency)) -> dict:
    """Простой запрос к LLM для проверки доступности модели."""

    if not container.config.use_llm:
        raise HTTPException(status_code=503, detail="LLM usage is disabled in configuration")

    question = "ты кто?"

    try:
        answer = await container.client.chat(
            system_prompt="You are a helpful assistant.",
            user_prompt=question,
        )
    except Exception as exc:  # pragma: no cover - зависимость от внешней системы
        raise HTTPException(status_code=502, detail=f"Ollama error: {exc}") from exc

    return {"question": question, "answer": answer}
