"""
Parameter extraction orchestrator.

Runs LLM-first extraction and falls back to the rules parser while preserving
transparent metadata for UI/debug reporting.
"""

import logging
from typing import Any, Dict, Tuple

from agents import normalizer
from agents.llm_extractor import (
    InvalidJSONError,
    LLMExtractionError,
    NoAPIKeyError,
    SchemaMismatchError,
    extract_via_llm_detailed,
    get_llm_config,
)
from agents.parser import parse_mission_requirements
from agents.parameter_inference import extract_mission_context

logger = logging.getLogger(__name__)

MIN_FOUND_FIELDS = 1
METADATA_KEY = "_extraction_metadata"


def _llm_output_acceptable(normalized: dict) -> bool:
    """Return True when normalized LLM output contains enough fields."""

    found_count = 0
    for key, entry in normalized.items():
        if key.startswith("_"):
            continue
        if entry.get("found") and entry.get("value") is not None:
            found_count += 1
    return found_count >= MIN_FOUND_FIELDS


def _found_count(params: dict) -> int:
    return sum(
        1
        for key, entry in params.items()
        if not key.startswith("_") and entry.get("found") and entry.get("value") is not None
    )


def _base_metadata() -> Dict[str, Any]:
    config = get_llm_config()
    return {
        "extraction_mode": "rules_fallback",
        "llm_status": "disabled_no_api_key"
        if not config["llm_enabled"]
        else "enabled",
        "fallback_reason": None,
        "normalization_source": None,
        "llm_raw_response": None,
        "llm_parsed_json": None,
        "explicit_params": None,
        "normalized_params": None,
        **config,
    }


def _fallback_to_rules(user_text: str, metadata: Dict[str, Any], reason: str) -> Tuple[dict, Dict[str, Any]]:
    logger.info("Falling back to rules parser: %s", reason)
    metadata["fallback_reason"] = reason
    metadata["extraction_mode"] = (
        "llm_disabled_rules_fallback"
        if metadata.get("llm_status") == "disabled_no_api_key"
        else "llm_failed_rules_fallback"
    )

    try:
        rules_params = parse_mission_requirements(user_text)
        normalized = normalizer.normalize_rules_output(rules_params)
        metadata["mission_context"] = extract_mission_context(user_text)
        metadata["explicit_params"] = _explicit_params_snapshot(normalized)
        metadata["normalization_source"] = "rules_fallback"
        metadata["normalized_params"] = normalized
        return normalized, metadata
    except Exception as exc:
        logger.exception("Rules fallback also failed")
        params = normalizer.build_not_found_params()
        metadata["fallback_reason"] = f"{reason}; rules_parser_failed: {exc}"
        metadata["extraction_mode"] = "rules_fallback"
        metadata["normalization_source"] = "not_found"
        metadata["normalized_params"] = params
        return params, metadata


def extract_mission_parameters_with_metadata(user_text: str) -> Tuple[dict, Dict[str, Any]]:
    """Extract mission parameters and return params plus transparency metadata."""

    metadata = _base_metadata()

    if not metadata["llm_enabled"]:
        return _fallback_to_rules(user_text, metadata, "disabled_no_api_key")

    try:
        llm_raw, llm_metadata = extract_via_llm_detailed(user_text)
        metadata.update(llm_metadata)
        metadata["llm_status"] = "enabled"
        normalized = normalizer.normalize_llm_output(llm_raw)
        metadata["mission_context"] = extract_mission_context(user_text, llm_raw)
        metadata["explicit_params"] = _explicit_params_snapshot(normalized)
        metadata["normalized_params"] = normalized
        metadata["normalization_source"] = "llm_extracted_normalized"

        if not _llm_output_acceptable(normalized):
            metadata["llm_status"] = "failed_normalization"
            return _fallback_to_rules(
                user_text,
                metadata,
                f"failed_normalization: only {_found_count(normalized)} field(s) found",
            )

        metadata["extraction_mode"] = "llm"
        metadata["fallback_reason"] = None
        return normalized, metadata

    except NoAPIKeyError as exc:
        metadata["llm_status"] = "disabled_no_api_key"
        return _fallback_to_rules(user_text, metadata, str(exc))
    except InvalidJSONError as exc:
        metadata["llm_status"] = "failed_invalid_json"
        return _fallback_to_rules(user_text, metadata, f"invalid_json: {exc}")
    except SchemaMismatchError as exc:
        metadata["llm_status"] = "failed_schema_validation"
        return _fallback_to_rules(user_text, metadata, f"schema_validation: {exc}")
    except LLMExtractionError as exc:
        metadata["llm_status"] = "failed_api_error"
        return _fallback_to_rules(user_text, metadata, f"api_error: {exc}")
    except Exception as exc:
        metadata["llm_status"] = "failed_api_error"
        return _fallback_to_rules(user_text, metadata, f"unexpected_error: {exc}")


def extract_mission_parameters(user_text: str) -> dict:
    """Extract mission parameters.

    The return value is the existing params dict plus a reserved
    ``_extraction_metadata`` entry for UI/debug transparency.
    """

    params, metadata = extract_mission_parameters_with_metadata(user_text)
    params[METADATA_KEY] = metadata
    return params


def _explicit_params_snapshot(params: dict) -> Dict[str, Any]:
    return {
        key: {
            "value": entry.get("value"),
            "unit": entry.get("unit"),
            "source": entry.get("source"),
            "confidence": entry.get("confidence"),
        }
        for key, entry in params.items()
        if not key.startswith("_")
        and isinstance(entry, dict)
        and entry.get("found")
        and entry.get("value") is not None
    }
