from typing import Dict, Any, List, Optional
from .rules import RuleBasedExtractor
from .llm import LLMExtractor
from app.core.validator import SchemaValidator
from app.core.config import CONFIG
from app.core.logger import get_logger
from app.core.field_settings import FieldSettings
from ..warnings import WarningItem
from ..normalize import normalize_whitespace
from ..summary import (
    build_selection_rationale,
    build_short_summary,
    clamp_summary_text,
)

logger = get_logger(__name__)


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(" ", "")
    if not text:
        return None
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        logger.debug("Unable to convert %r to float", value)
        return None


class ExtractionPipeline:
    def __init__(
        self,
        schema: Dict[str, Any],
        system_prompt_path: str,
        user_tmpl_path: str,
        field_settings: FieldSettings,
        field_guidelines_path: Optional[str] = None,
        summary_system_prompt_path: Optional[str] = None,
        summary_user_tmpl_path: Optional[str] = None,
    ):
        self.field_settings = field_settings
        self.schema = self.field_settings.apply_to_schema(schema)
        self.validator = SchemaValidator(self.schema)
        self.rules = RuleBasedExtractor()
        self.llm = None
        self.summary_llm = None
        self._summary_schema = {
            "type": "object",
            "properties": {
                "КраткоеСодержание": {"type": "string"},
                "ОбоснованиеВыбора": {"type": "string"},
                "ОЭЗ_ОКПД2": {"type": "string"},
                "СрокДоговора": {"type": "string"},
                "Ответственный": {"type": "string"},
                "seza_ТипДоговора": {"type": "string"},
                "СпособОплаты": {"type": "string"},
            },
        }
        if CONFIG.use_llm:
            self.llm = LLMExtractor(
                self.schema,
                system_prompt_path,
                user_tmpl_path,
                field_guidelines_path,
            )
            if summary_system_prompt_path and summary_user_tmpl_path:
                self.summary_llm = LLMExtractor(
                    self._summary_schema,
                    summary_system_prompt_path,
                    summary_user_tmpl_path,
                )

    def _default_value_for_field(self, field: str) -> Any:
        properties = self.schema.get("properties", {})
        meta = properties.get(field, {}) if isinstance(properties, dict) else {}
        field_type = meta.get("type")
        if isinstance(field_type, list):
            field_type = next((item for item in field_type if isinstance(item, str)), None)

        if field_type == "integer":
            return 0
        if field_type == "number":
            return 0.0
        if field_type == "boolean":
            return False
        if field_type == "array":
            return []
        if field_type == "object":
            return {}
        return ""

    @staticmethod
    def _is_empty_value(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) == 0
        return False

    async def run(self, text: str) -> (
        Dict[str, Any],
        List[WarningItem],
        List[Dict[str, Any]],
        Dict[str, Any],
        str,
    ):
        warnings = []

        cleaned_text = normalize_whitespace(text)

        summary_text = ""
        rationale_text = ""
        okpd2_code = ""
        contract_term = ""
        responsible_person = ""
        contract_type = ""
        payment_method = ""
        prompts: List[str] = []
        raw_outputs: List[str] = []

        if self.summary_llm is not None:
            summary_payload: Dict[str, Any] = {}
            try:
                result = await self.summary_llm.extract(cleaned_text, {})
                if isinstance(result, dict):
                    summary_payload = result
            except Exception:  # noqa: BLE001
                logger.exception("Summary extractor failed")
                warnings.append(
                    WarningItem(
                        code="summary_llm_error",
                        message="Не удалось получить краткое содержание из модели; возвращены правила",
                    )
                )
            else:
                if not isinstance(result, dict):
                    logger.warning(
                        "Summary extractor returned non-dict payload: %s", type(result)
                    )
            finally:
                summary_prompt = getattr(self.summary_llm, "last_prompt", "")
                if summary_prompt:
                    prompts.append(summary_prompt)
                summary_raw = getattr(self.summary_llm, "last_raw", "")
                if summary_raw:
                    raw_outputs.append(summary_raw)

            candidate_summary = summary_payload.get("КраткоеСодержание", "")
            candidate_rationale = summary_payload.get("ОбоснованиеВыбора", "")
            candidate_okpd2 = summary_payload.get("ОЭЗ_ОКПД2", "")
            candidate_contract_term = summary_payload.get("СрокДоговора", "")
            candidate_responsible = summary_payload.get("Ответственный", "")
            candidate_contract_type = summary_payload.get("seza_ТипДоговора", "")
            candidate_payment_method = summary_payload.get("СпособОплаты", "")

            if isinstance(candidate_summary, str):
                summary_text = clamp_summary_text(candidate_summary)
            if isinstance(candidate_rationale, str):
                rationale_text = clamp_summary_text(candidate_rationale)
            if isinstance(candidate_okpd2, str):
                okpd2_code = candidate_okpd2.strip()
            if isinstance(candidate_contract_term, str):
                contract_term = candidate_contract_term.strip()
            if isinstance(candidate_responsible, str):
                responsible_person = candidate_responsible.strip()
            if isinstance(candidate_contract_type, str):
                contract_type = candidate_contract_type.strip()
            if isinstance(candidate_payment_method, str):
                payment_method = candidate_payment_method.strip()

        # 1) Правила (используем только если LLM отключен)
        if self.llm is None:
            partial: Dict[str, Any] = await self.rules.extract(cleaned_text, {})
        else:
            partial = {}

        llm_fields = tuple(self.field_settings.llm_fields())

        llm_fields = tuple(self.field_settings.llm_fields())

        # 2) LLM (если включен)
        if self.llm is not None:
            aggregated: Dict[str, Any] = dict(partial)
            for field in llm_fields:
                aggregated.pop(field, None)
            warned_missing_fields: set[str] = set()
            try:
                self.field_settings.refresh_prompts()
                for group in self.field_settings.build_llm_groups():
                    schema_subset = self.field_settings.build_schema_subset(
                        self.schema, group.fields
                    )
                    guidelines = self.field_settings.build_guidelines_bundle(group.fields)
                    segment = group.document_slice.extract(cleaned_text)
                    group_partial: Dict[str, Any] = {}
                    try:
                        llm_result = await self.llm.extract(
                            segment,
                            group_partial,
                            schema_override=schema_subset,
                            field_guidelines=guidelines,
                        )
                    except Exception:  # noqa: BLE001
                        logger.exception(
                            "LLM extractor failed for fields %s", ", ".join(group.fields)
                        )
                        warnings.append(
                            WarningItem(
                                code="llm_error",
                                message=(
                                    "Не удалось получить данные из модели для некоторых полей; "
                                    "использованы значения по умолчанию"
                                ),
                            )
                        )
                        for field in group.fields:
                            if field in warned_missing_fields:
                                continue
                            aggregated.setdefault(
                                field, self._default_value_for_field(field)
                            )
                            warned_missing_fields.add(field)
                        continue

                    for field in group.fields:
                        value = llm_result.get(field, None)
                        if self._is_empty_value(value):
                            if field not in warned_missing_fields:
                                warnings.append(
                                    WarningItem(
                                        code="llm_missing_field",
                                        message=(
                                            f"Модель не вернула значение для поля '{field}'"
                                        ),
                                    )
                                )
                                warned_missing_fields.add(field)
                            aggregated[field] = self._default_value_for_field(field)
                        else:
                            aggregated[field] = value
                    llm_prompt = getattr(self.llm, "last_prompt", "")
                    if llm_prompt:
                        prompts.append(llm_prompt)
                    llm_raw = getattr(self.llm, "last_raw", "")
                    if llm_raw:
                        raw_outputs.append(llm_raw)
            except Exception:  # noqa: BLE001
                logger.exception("LLM extractor failed with unexpected error")
                warnings.append(
                    WarningItem(
                        code="llm_error",
                        message=(
                            "Не удалось получить данные из модели для некоторых полей; "
                            "использованы значения по умолчанию"
                        ),
                    )
                )
                aggregated = dict(partial)
                for field in llm_fields:
                    aggregated.pop(field, None)
                    if field not in warned_missing_fields:
                        warnings.append(
                            WarningItem(
                                code="llm_missing_field",
                                message=(
                                    f"Модель не вернула значение для поля '{field}'"
                                ),
                            )
                        )
                        warned_missing_fields.add(field)
                    aggregated.setdefault(field, self._default_value_for_field(field))
                data = aggregated
            else:
                for field in llm_fields:
                    if field in aggregated:
                        continue
                    aggregated[field] = self._default_value_for_field(field)
                    if field in warned_missing_fields:
                        continue
                    warnings.append(
                        WarningItem(
                            code="llm_missing_field",
                            message=(
                                f"Модель не вернула значение для поля '{field}'"
                            ),
                        )
                    )
                    warned_missing_fields.add(field)
                data = aggregated
        else:
            data = partial

        prompt = "\n\n-----\n\n".join(prompts)

        if okpd2_code:
            data["ОЭЗ_ОКПД2"] = okpd2_code
        
        if contract_term:
            data["СрокДоговора"] = contract_term
        
        if responsible_person:
            existing_responsible = data.get("Ответственный")
            if not isinstance(existing_responsible, str) or not existing_responsible.strip():
                data["Ответственный"] = responsible_person
        
        if contract_type:
            existing_contract_type = data.get("seza_ТипДоговора")
            if not isinstance(existing_contract_type, str) or not existing_contract_type.strip():
                data["seza_ТипДоговора"] = contract_type
        
        if payment_method:
            existing_payment_method = data.get("СпособОплаты")
            if not isinstance(existing_payment_method, str) or not existing_payment_method.strip():
                data["СпособОплаты"] = payment_method
                
        # 3) Валидация
        filtered_data = self.field_settings.filter_payload(data)
        errors = self.validator.validate(filtered_data)

        if not summary_text:
            summary_text = build_short_summary(filtered_data, cleaned_text)
        if summary_text:
            filtered_data["КраткоеСодержание"] = summary_text

        if not rationale_text:
            rationale_text = build_selection_rationale(filtered_data, cleaned_text)
        if rationale_text:
            filtered_data["ОбоснованиеВыбора"] = rationale_text

        # 4) Дополнительные предупреждения (пример: расхождение НДС)
        vat = _coerce_float(data.get("СуммаНДС"))
        total = _coerce_float(data.get("Сумма"))
        rate = _coerce_float(data.get("СтавкаНДС"))
        if vat is not None and total is not None and rate is not None and rate > 0:
            expected_vat = round(total * rate / (100 + rate), 2)
            if abs(expected_vat - vat) > CONFIG.numeric_tolerance:
                warnings.append(
                    WarningItem(
                        code="vat_mismatch",
                        message=(
                            f"НДС в документе {vat}, расчётное значение {expected_vat} при ставке {rate}%"
                        ),
                    )
                )
        elif any(value is None for value in (vat, total, rate)):
            logger.debug(
                "VAT consistency check skipped due to missing or invalid numbers: vat=%r total=%r rate=%r",
                data.get("СуммаНДС"),
                data.get("Сумма"),
                data.get("СтавкаНДС"),
            )

        debug = {
            "disabled_fields": ", ".join(sorted(self.field_settings.disabled_fields())),
            "llm_raw_outputs": raw_outputs,
        }

        prompt = normalize_whitespace(prompt) if prompt else ""

        return filtered_data, warnings, errors, debug, prompt
