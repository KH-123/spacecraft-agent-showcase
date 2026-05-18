"""
LLM-based mission parameter extraction.

The LLM is used only for natural-language understanding. It extracts raw
mission parameters as JSON; unit conversion, guardrail validation, and all
engineering calculations remain deterministic Python work elsewhere.
"""

import json
import os
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT_SECONDS = 30


EXTRACTION_SYSTEM_PROMPT = """You are a spacecraft conceptual design parameter extractor.

Your task is ONLY to extract mission parameters from the user's natural language input.

Rules:
- Do NOT perform engineering calculations.
- Do NOT fabricate values the user did not provide.
- Output ONLY valid JSON. No Markdown, no code fences, no explanation.
- Support Chinese, English, unit abbreviations, synonyms, and minor typos.
- Do NOT convert units at the LLM layer. Keep the original value and unit as written.
- If a field is not present, set found=false, value=null, unit=null, raw_text=null, confidence=0.0.

Chinese mapping hints:
- 有效质量 / 有效载荷质量 / 载荷质量 -> payload_mass
- 载荷功耗 / 载荷功率 / 功率需求 -> power_required
- 轨道高度 / 高度 -> orbit_altitude
- 轨道周期 / 周期 -> orbit_period
- 轨道倾角 / 倾角 -> orbit_inclination
- 任务寿命 / 寿命 -> mission_lifetime
- 地面分辨率 / 分辨率 -> ground_resolution
- 太阳同步轨道 -> orbit_type value: "SSO"
- SSO -> orbit_type value: "SSO"
- 极地轨道 -> orbit_type value: "polar orbit"
- 低轨 / 近地轨道 / LEO -> orbit_type value: "LEO"
- 圆轨道 / 近圆轨道 / 圆形轨道 / circular orbit / near-circular orbit -> orbit_type value: "circular orbit"
- 轨道类型位极地轨道 means 轨道类型为极地轨道 and should be orbit_type value: "polar orbit"

Unit examples:
- 有效质量1吨 -> value: 1, unit: "吨"
- 载荷功耗0.5千瓦 -> value: 0.5, unit: "千瓦"
- 轨道高度500公里 -> value: 500, unit: "公里"
- 寿命3年 -> value: 3, unit: "年"

Output exactly this JSON shape:
{
  "explicit_params": {
    "orbit_altitude": {"found": false, "value": null, "unit": null, "raw_text": null, "confidence": 0.0},
    "payload_mass": {"found": false, "value": null, "unit": null, "raw_text": null, "confidence": 0.0},
    "power_required": {"found": false, "value": null, "unit": null, "raw_text": null, "confidence": 0.0},
    "orbit_inclination": {"found": false, "value": null, "unit": null, "raw_text": null, "confidence": 0.0},
    "orbit_period": {"found": false, "value": null, "unit": null, "raw_text": null, "confidence": 0.0},
    "orbit_type": {"found": false, "value": null, "unit": null, "raw_text": null, "confidence": 0.0},
    "mission_lifetime": {"found": false, "value": null, "unit": null, "raw_text": null, "confidence": 0.0},
    "ground_resolution": {"found": false, "value": null, "unit": null, "raw_text": null, "confidence": 0.0}
  },
  "mission_intent": {
    "mission_objective": null,
    "target_region": null,
    "performance_requirements": [],
    "missing_params": [],
    "ambiguity_notes": []
  },
  "ambiguity_notes": [],
  "raw_interpretation_notes": []
}
"""


class LLMExtractionError(Exception):
    """Raised when LLM extraction fails."""

    reason_code = "failed_api_error"


class NoAPIKeyError(LLMExtractionError):
    """Raised when no API key is configured."""

    reason_code = "disabled_no_api_key"


class InvalidJSONError(LLMExtractionError):
    """Raised when LLM output cannot be parsed as JSON."""

    reason_code = "failed_invalid_json"


class SchemaMismatchError(LLMExtractionError):
    """Raised when parsed JSON does not match the required schema."""

    reason_code = "failed_schema_validation"


REQUIRED_TOP_KEYS = set()
REQUIRED_FIELD_KEYS = {
    "orbit_altitude",
    "payload_mass",
    "power_required",
    "orbit_inclination",
    "orbit_type",
    "mission_lifetime",
    "ground_resolution",
}
REQUIRED_ENTRY_KEYS = {"found", "value", "unit", "raw_text", "confidence"}


def get_llm_config() -> Dict[str, Any]:
    """Return safe LLM configuration metadata without exposing the API key."""

    api_key = os.environ.get("LLM_API_KEY", "")
    return {
        "llm_enabled": bool(api_key),
        "llm_api_key_present": bool(api_key),
        "llm_base_url": os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL),
        "llm_model": os.environ.get("LLM_MODEL", DEFAULT_MODEL),
        "llm_timeout_seconds": int(
            os.environ.get("LLM_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
        ),
    }


def _get_client() -> Optional[OpenAI]:
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        return None
    return OpenAI(
        api_key=api_key,
        base_url=os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL),
    )


def _strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    if not cleaned.startswith("```"):
        return cleaned

    first_newline = cleaned.find("\n")
    if first_newline != -1:
        cleaned = cleaned[first_newline + 1 :].strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()
    return cleaned


def _extract_first_json_object(text: str) -> str:
    """Extract the first balanced JSON object from text."""

    cleaned = _strip_code_fence(text)
    if cleaned.startswith("{") and cleaned.endswith("}"):
        return cleaned

    start = cleaned.find("{")
    if start == -1:
        raise InvalidJSONError("No JSON object start found in LLM output")

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(cleaned)):
        char = cleaned[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return cleaned[start : index + 1]

    raise InvalidJSONError("No balanced JSON object found in LLM output")


def parse_llm_json(raw_content: str) -> dict:
    """Parse LLM JSON, tolerating code fences or small surrounding text."""

    json_text = _extract_first_json_object(raw_content)
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise InvalidJSONError(f"LLM output is not valid JSON: {exc}") from exc


def _validate_schema(data: dict) -> None:
    if not isinstance(data, dict):
        raise SchemaMismatchError("LLM output is not a dict")

    missing_top = REQUIRED_TOP_KEYS - set(data.keys())
    if missing_top:
        raise SchemaMismatchError(f"Missing top-level key(s): {missing_top}")

    mission_parameters = data.get("explicit_params") or data.get("mission_parameters")
    if not isinstance(mission_parameters, dict):
        raise SchemaMismatchError("explicit_params/mission_parameters is not a dict")

    missing_fields = REQUIRED_FIELD_KEYS - set(mission_parameters.keys())
    if missing_fields:
        raise SchemaMismatchError(
            f"Missing field(s) in mission_parameters: {missing_fields}"
        )

    for field_name, field_value in mission_parameters.items():
        if not isinstance(field_value, dict):
            raise SchemaMismatchError(f"Field '{field_name}' is not a dict")
        missing_entry = REQUIRED_ENTRY_KEYS - set(field_value.keys())
        if missing_entry:
            raise SchemaMismatchError(
                f"Field '{field_name}' missing key(s): {missing_entry}"
            )


def extract_via_llm_detailed(user_text: str) -> Tuple[dict, Dict[str, Any]]:
    """Extract parameters and return parsed JSON plus safe metadata."""

    metadata = get_llm_config()
    client = _get_client()
    if client is None:
        raise NoAPIKeyError("LLM_API_KEY is not set")

    try:
        response = client.chat.completions.create(
            model=metadata["llm_model"],
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            temperature=0.0,
            max_tokens=2000,
            timeout=metadata["llm_timeout_seconds"],
        )
    except Exception as exc:
        raise LLMExtractionError(f"LLM API call failed: {exc}") from exc

    raw_content = response.choices[0].message.content
    if raw_content is None:
        raise LLMExtractionError("LLM returned empty content")

    parsed = parse_llm_json(raw_content)
    _validate_schema(parsed)

    metadata.update(
        {
            "llm_status": "enabled",
            "llm_raw_response": raw_content,
            "llm_parsed_json": parsed,
        }
    )
    return parsed, metadata


def extract_via_llm(user_text: str) -> dict:
    """Backward-compatible extraction function returning only parsed JSON."""

    parsed, _metadata = extract_via_llm_detailed(user_text)
    return parsed
