import json
import sys
import types
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch


BASE_APP_PATH = Path(__file__).resolve().parents[1]
if str(BASE_APP_PATH) not in sys.path:
    sys.path.insert(0, str(BASE_APP_PATH))


# Provide lightweight stubs for third-party packages so that application modules can be imported
fastapi_stub = types.ModuleType("fastapi")


class _FastAPI:
    def __init__(self, *args, **kwargs):
        self.routes = []

    def include_router(self, router):  # pragma: no cover - minimal stub
        self.routes.append(router)


class _APIRouter:
    def __init__(self, *args, **kwargs):
        self.routes = []

    def _register(self, *args, **kwargs):
        def decorator(func):
            self.routes.append((args, kwargs, func))
            return func

        return decorator

    get = post = put = delete = _register


class _HTTPException(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _identity(value=None, *args, **kwargs):
    return value


class _UploadFile:
    def __init__(self, *args, **kwargs):
        self.filename = kwargs.get("filename")

    async def read(self):  # pragma: no cover - helper stub
        return b""


fastapi_stub.FastAPI = _FastAPI
fastapi_stub.APIRouter = _APIRouter
fastapi_stub.HTTPException = _HTTPException
fastapi_stub.Depends = _identity
fastapi_stub.Body = _identity
fastapi_stub.File = _identity
fastapi_stub.UploadFile = _UploadFile

sys.modules.setdefault("fastapi", fastapi_stub)

responses_stub = types.ModuleType("fastapi.responses")


class _JSONResponse(dict):
    def __init__(self, *, content=None, status_code=200):
        super().__init__(content or {})
        self.status_code = status_code


class _PlainTextResponse(str):
    def __new__(cls, content="", status_code=200):
        obj = str.__new__(cls, content)
        obj.status_code = status_code
        return obj


responses_stub.JSONResponse = _JSONResponse
responses_stub.PlainTextResponse = _PlainTextResponse
sys.modules.setdefault("fastapi.responses", responses_stub)

pydantic_stub = types.ModuleType("pydantic")


class _BaseModel:
    def __init__(self, **data):
        for key, value in data.items():
            setattr(self, key, value)

    @classmethod
    def model_validate(cls, data):
        return cls(**data)

    def model_dump(self):
        return dict(self.__dict__)


def _config_dict(**kwargs):  # pragma: no cover - helper stub
    return dict(**kwargs)


pydantic_stub.BaseModel = _BaseModel
pydantic_stub.ConfigDict = _config_dict
sys.modules.setdefault("pydantic", pydantic_stub)

jsonschema_stub = types.ModuleType("jsonschema")


class _ValidationError(Exception):
    def __init__(self, message="", path=None, validator=None, validator_value=None, schema_path=None):
        super().__init__(message)
        self.message = message
        self.path = path or []
        self.validator = validator
        self.validator_value = validator_value
        self.schema_path = schema_path or []


class _DraftValidator:
    def __init__(self, schema):
        self.schema = schema

    def iter_errors(self, data):  # pragma: no cover - helper stub
        return []


jsonschema_stub.ValidationError = _ValidationError
jsonschema_stub.Draft202012Validator = _DraftValidator
sys.modules.setdefault("jsonschema", jsonschema_stub)

httpx_stub = types.ModuleType("httpx")


class _Timeout:
    def __init__(self, *args, **kwargs):
        pass


class _Response:
    def __init__(self, json_data=None, status_code=200):
        self._json = json_data or {}
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):  # pragma: no cover - helper stub
        return None


class _AsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None):  # pragma: no cover - helper stub
        return _Response()

    async def get(self, url):  # pragma: no cover - helper stub
        return _Response()


class _HTTPStatusError(Exception):
    def __init__(self, message="", request=None, response=None):
        super().__init__(message)
        self.response = response or _Response()


class _ReadTimeout(Exception):
    pass


httpx_stub.AsyncClient = _AsyncClient
httpx_stub.Timeout = _Timeout
httpx_stub.HTTPStatusError = _HTTPStatusError
httpx_stub.ReadTimeout = _ReadTimeout
httpx_stub.Response = _Response
sys.modules.setdefault("httpx", httpx_stub)

from app.core.config import CONFIG
from app.core.field_settings import FieldSettings
from app.services.extractor.pipeline import ExtractionPipeline
from app.services.ollama_client import OllamaClient


class ExtractionPipelineLLMTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        base_dir = Path(__file__).resolve().parents[1]
        schema_path = base_dir / "app" / "assets" / "schema.json"
        self.schema = json.loads(schema_path.read_text(encoding="utf-8"))

        self.field_settings = FieldSettings(
            extractors_path=str(base_dir / "app" / "assets" / "field_extractors.json"),
            guidelines_path=str(base_dir / "app" / "prompts" / "field_guidelines.md"),
            prompts_dir=str(base_dir / "app" / "prompts" / "fields"),
            contexts_path=str(base_dir / "app" / "assets" / "field_contexts.json"),
        )

        self.pipeline = ExtractionPipeline(
            self.schema,
            system_prompt_path=str(base_dir / "app" / "prompts" / "system.txt"),
            user_tmpl_path=str(base_dir / "app" / "prompts" / "user_template.txt"),
            field_settings=self.field_settings,
            field_guidelines_path=str(base_dir / "app" / "prompts" / "field_guidelines.md"),
        )

    async def test_pipeline_uses_configured_model_and_returns_llm_data(self) -> None:
        captured_models: list[str] = []

        async def fake_chat(self, system_prompt, user_prompt, temperature=None, max_tokens=None):
            captured_models.append(self.model)
            return json.dumps({"ОЭЗ_Резидент": "LLM Value"})

        text = "Простой текст договора без специализированных реквизитов."

        with patch.object(OllamaClient, "chat", new=fake_chat):
            data, warnings, errors, debug, prompt = await self.pipeline.run(text)

        self.assertIn("ОЭЗ_Резидент", data)
        self.assertEqual(data["ОЭЗ_Резидент"], "LLM Value")
        self.assertTrue(captured_models, "LLM client was not invoked")
        self.assertEqual(captured_models[0], CONFIG.model_name)
        self.assertIsInstance(warnings, list)
        self.assertIsInstance(errors, list)
        self.assertIn("llm_raw_outputs", debug)
        self.assertIsInstance(prompt, str)
