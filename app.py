"""Spacecraft Conceptual Design Agent Demo - Main Application."""

from __future__ import annotations

import os
from copy import deepcopy
from datetime import datetime
from typing import Any

import streamlit as st

from agents.design_advisor import generate_design_advice
from agents.design_draft_generator import (
    build_external_simulation_placeholders,
    build_params_from_confirmed_draft,
    generate_candidate_design_drafts,
)
from agents.extractor import extract_mission_parameters
from agents.mission_context_extractor import extract_mission_context
from agents.mission_interpreter import build_constraint_rows, interpret_mission_request
from agents.normalizer import build_not_found_params, normalize_rules_output
from agents.orbit_consistency import (
    has_severe_orbit_conflicts,
    validate_orbit_consistency,
)
from agents.orbit_interpreter import build_orbital_elements_table, interpret_orbit_parameters
from agents.parameter_inference import infer_missing_parameters
from agents.parser import identify_missing_parameters
from agents.planner import execute_all_tasks
from agents.report_generator import (
    generate_parameter_confirmation_report,
    generate_report,
)
from agents.validator import has_severe_errors, validate_parameters
from ui_helpers import (
    USE_MODE_MISSION,
    append_execution_log,
    apply_console_style,
    get_execution_logs,
    render_advisor_panel,
    render_current_design_summary_card,
    render_debug_panel,
    render_execution_log,
    render_header,
    render_input_panel,
    render_mission_debug_panel,
    render_mission_guidance_panel,
    render_mission_input_panel,
    render_mode_selector,
    render_parameter_cards,
    render_parameter_understanding_panel,
    render_patch_view_panel,
    render_raw_input_history_panel,
    render_confirmation_panel,
    render_report_download,
    render_status_card,
    render_summary_panel,
    reset_execution_logs,
)


EXPLICIT_PARAM_SOURCES = {
    "user_provided",
    "llm_extracted",
    "llm_extracted_normalized",
    "rules_extracted",
    "rules_fallback",
    "user_confirmed_llm_inferred",
    "user_confirmed",
    "user_updated",
}

CONFIRMATION_FORM_SOURCE = "parameter_confirmation_form"
CONFIRMATION_SUPPORTED_ENGINEERING_FIELDS = {
    "orbit_type",
    "orbit_inclination_deg",
    "eccentricity",
    "raan_deg",
    "arg_perigee_deg",
    "true_anomaly_deg",
}

HISTORICAL_STATE_SOURCES = EXPLICIT_PARAM_SOURCES | {
    "inferred_from_altitude",
    "inferred_from_orbit_type",
    "rules_inferred",
    "llm_inferred",
    "default_assumption",
    "tool_computed",
}

DERIVED_PARAM_SOURCES = {
    "inferred_from_altitude",
    "inferred_from_orbit_type",
    "rules_inferred",
    "llm_inferred",
    "default_assumption",
    "tool_computed",
}

DERIVED_DEPENDENCIES = {
    "orbit_altitude_km": {"semi_major_axis_km", "orbit_period_min"},
    "semi_major_axis_km": {"orbit_period_min"},
    "orbit_type": {"eccentricity", "orbit_inclination_deg"},
}

PENDING_DESIGN_STATE_KEY = "pending_design_state"
PARAMETER_INPUT_CLEAR_QUEUE_KEY = "_parameter_input_clear_keys"
PARAMETER_NEW_INPUT_KEY = "mission_input"
PARAMETER_UPDATE_INPUT_KEY = "mission_update_input"


def _queue_parameter_input_clear(*, update_current: bool, state: Any | None = None) -> None:
    """Queue only the active parameter input widget to be cleared on next render."""

    session = state if state is not None else st.session_state
    key = PARAMETER_UPDATE_INPUT_KEY if update_current else PARAMETER_NEW_INPUT_KEY
    queued_keys = list(session.get(PARAMETER_INPUT_CLEAR_QUEUE_KEY, []) or [])
    if key not in queued_keys:
        queued_keys.append(key)
    session[PARAMETER_INPUT_CLEAR_QUEUE_KEY] = queued_keys


def _consume_parameter_input_clear_queue(state: Any | None = None) -> None:
    """Clear queued text-area buffers before Streamlit instantiates widgets."""

    session = state if state is not None else st.session_state
    queued_keys = list(session.pop(PARAMETER_INPUT_CLEAR_QUEUE_KEY, []) or [])
    for key in queued_keys:
        session[key] = ""


def _confirmation_audit_rounds(raw_input_history: list[str] | None) -> tuple[int, int]:
    """Return separate audit rounds for confirmation action and pipeline rerun."""

    confirmation_round = len(raw_input_history or []) + 1
    return confirmation_round, confirmation_round + 1


def _has_context_values(context: dict[str, Any] | None) -> bool:
    return any(value not in (None, "", []) for value in (context or {}).values())


def _is_explicit_param_entry(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    source = entry.get("source")
    status = entry.get("status")
    return source in EXPLICIT_PARAM_SOURCES and (
        bool(entry.get("found"))
        or entry.get("value") is not None
        or status in {"invalid_unit", "missing_unit"}
    )


def _is_available_param_entry(entry: Any) -> bool:
    return (
        isinstance(entry, dict)
        and bool(entry.get("found"))
        and entry.get("value") is not None
    )


def _is_preservable_history_entry(entry: Any) -> bool:
    return _is_available_param_entry(entry) and entry.get("source") in HISTORICAL_STATE_SOURCES


def _extract_explicit_parameters(params: dict[str, Any]) -> dict[str, Any]:
    explicit = build_not_found_params()
    for key, entry in params.items():
        if key.startswith("_"):
            continue
        if _is_explicit_param_entry(entry):
            explicit[key] = deepcopy(entry)
    return explicit


def _merge_explicit_parameters(
    previous_explicit: dict[str, Any] | None,
    latest_params: dict[str, Any],
) -> dict[str, Any]:
    merged = build_not_found_params()
    for key, entry in (previous_explicit or {}).items():
        if key.startswith("_"):
            continue
        if _is_explicit_param_entry(entry):
            merged[key] = deepcopy(entry)

    for key, entry in (latest_params or {}).items():
        if key.startswith("_") or not _is_explicit_param_entry(entry):
            continue
        new_entry = deepcopy(entry)
        previous_entry = merged.get(key)
        latest_source = new_entry.get("source")
        is_confirmation_source = latest_source in {"user_confirmed", "user_confirmed_llm_inferred"}
        if (
            _is_explicit_param_entry(previous_entry)
            and _entry_signature(new_entry) != _entry_signature(previous_entry)
            and not is_confirmation_source
        ):
            new_entry["previous_value"] = previous_entry.get("value")
            new_entry["previous_unit"] = previous_entry.get("unit")
            new_entry["previous_source"] = previous_entry.get("source")
            new_entry["source_before_update"] = latest_source
            new_entry["source"] = "user_updated"
            new_entry["status"] = "user_updated"
            if new_entry.get("found") and new_entry.get("value") is not None:
                new_entry["requires_confirmation"] = False
        merged[key] = new_entry
    merged["_extraction_metadata"] = {
        "extraction_mode": "multi_turn_merged_explicit_params",
        "llm_status": "not_used_for_merge",
        "fallback_reason": None,
        "normalization_source": "session_design_state",
        "explicit_params": _param_snapshot(merged),
        "normalized_params": _public_params_snapshot(merged),
        "llm_raw_response": None,
        "llm_parsed_json": None,
        "llm_api_key_present": False,
        "llm_base_url": None,
        "llm_model": None,
        "llm_timeout_seconds": None,
    }
    return merged


def _make_stale_entry(previous_entry: dict[str, Any], dependency_field: str) -> dict[str, Any]:
    return {
        "value": None,
        "unit": previous_entry.get("unit"),
        "found": False,
        "source": "not_found",
        "status": "stale",
        "requires_confirmation": True,
        "previous_value": previous_entry.get("value"),
        "previous_unit": previous_entry.get("unit"),
        "previous_source": previous_entry.get("source"),
        "stale_due_to": dependency_field,
    }


def _clear_stale_derived_parameters(
    params: dict[str, Any],
    changed_fields: set[str],
) -> list[dict[str, Any]]:
    stale_items: list[dict[str, Any]] = []
    for dependency_field in changed_fields:
        for derived_field in DERIVED_DEPENDENCIES.get(dependency_field, set()):
            if derived_field in changed_fields:
                continue
            entry = params.get(derived_field)
            if not _is_available_param_entry(entry):
                continue
            if entry.get("source") not in DERIVED_PARAM_SOURCES:
                continue
            params[derived_field] = _make_stale_entry(entry, dependency_field)
            stale_items.append(
                {
                    "field": derived_field,
                    "previous_value": entry.get("value"),
                    "previous_unit": entry.get("unit"),
                    "previous_source": entry.get("source"),
                    "stale_due_to": dependency_field,
                }
            )

    if "orbit_type" in changed_fields:
        params.pop("_orbit_semantics", None)

    return stale_items


def apply_user_patch_to_design_state(
    previous_state: dict[str, Any],
    latest_explicit_patch: dict[str, Any],
    latest_context_patch: dict[str, Any] | None = None,
    *,
    round_label: str | None = None,
    confirmed_at_round: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Merge a latest explicit patch onto the previous design state.

    Missing fields in the latest extraction are ignored. Existing explicit,
    inferred, default, and tool-computed values are preserved unless the user
    explicitly updates a dependency that makes a derived value stale.
    """
    previous_normalized = previous_state.get("normalized_parameters") or {}
    previous_context = previous_state.get("mission_context") or {}
    merged = build_not_found_params()

    for key, entry in previous_normalized.items():
        if key.startswith("_"):
            if isinstance(entry, dict):
                merged[key] = deepcopy(entry)
            continue
        if _is_preservable_history_entry(entry):
            merged[key] = deepcopy(entry)

    changed_fields: set[str] = set()
    latest_keys: set[str] = set()
    for key, entry in (latest_explicit_patch or {}).items():
        if key.startswith("_") or not _is_explicit_param_entry(entry):
            continue
        latest_keys.add(key)
        new_entry = deepcopy(entry)
        previous_entry = merged.get(key)
        latest_source = new_entry.get("source")
        is_confirmation_source = latest_source in {"user_confirmed", "user_confirmed_llm_inferred"}
        if _is_available_param_entry(previous_entry) and _entry_signature(new_entry) != _entry_signature(previous_entry):
            changed_fields.add(key)
            new_entry["previous_value"] = previous_entry.get("value")
            new_entry["previous_unit"] = previous_entry.get("unit")
            new_entry["previous_source"] = previous_entry.get("source")
            if not is_confirmation_source:
                new_entry["source_before_update"] = latest_source
                new_entry["source"] = "user_updated"
                new_entry["status"] = "user_updated"
                if new_entry.get("found") and new_entry.get("value") is not None:
                    new_entry["requires_confirmation"] = False
        elif not _is_available_param_entry(previous_entry):
            changed_fields.add(key)
        merged[key] = new_entry

    stale_items = _clear_stale_derived_parameters(merged, changed_fields)
    mission_context = _merge_mission_context(previous_context, latest_context_patch)
    patch_view = _build_patch_view(
        previous_state,
        latest_explicit_patch,
        latest_context_patch or {},
        round_label=round_label,
        confirmed_at_round=confirmed_at_round,
    )
    if stale_items:
        patch_view["stale"] = stale_items

    merged["_extraction_metadata"] = {
        "extraction_mode": "multi_turn_patch_merged_design_state",
        "llm_status": "not_used_for_merge",
        "fallback_reason": None,
        "normalization_source": "previous_design_state_plus_latest_explicit_patch",
        "patch_fields": sorted(latest_keys),
        "changed_fields": sorted(changed_fields),
        "stale_derived_parameters": stale_items,
        "explicit_params": _param_snapshot(_extract_explicit_parameters(merged)),
        "normalized_params": _public_params_snapshot(merged),
        "llm_raw_response": None,
        "llm_parsed_json": None,
        "llm_api_key_present": False,
        "llm_base_url": None,
        "llm_model": None,
        "llm_timeout_seconds": None,
    }
    return merged, mission_context, patch_view


def _merge_mission_context(
    previous_context: dict[str, Any] | None,
    latest_context: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(previous_context or latest_context or {})
    for key, value in (latest_context or {}).items():
        if key not in merged:
            merged[key] = value
        elif value not in (None, "", []):
            merged[key] = value
    return merged


def _build_params_from_confirmation_patch(patch: dict[str, Any]) -> dict[str, Any]:
    """Convert a structured confirmation patch into normalized user-confirmed params."""
    engineering = patch.get("engineering_parameters") or {}
    rules_like: dict[str, dict[str, Any]] = {}
    for field, entry in engineering.items():
        if field not in CONFIRMATION_SUPPORTED_ENGINEERING_FIELDS or not isinstance(entry, dict):
            continue
        value = entry.get("value")
        if value in (None, ""):
            continue
        rules_like[field] = {
            "found": True,
            "value": value,
            "unit": entry.get("unit"),
            "raw_text": f"confirmation_form:{field}",
        }

    normalized = normalize_rules_output(rules_like)
    for field in rules_like:
        if field not in normalized:
            continue
        normalized[field]["source"] = "user_confirmed"
        if normalized[field].get("found") and normalized[field].get("value") is not None:
            normalized[field]["status"] = "user_confirmed"
            normalized[field]["requires_confirmation"] = False
        normalized[field]["confirmation_source"] = CONFIRMATION_FORM_SOURCE
        normalized[field]["raw_text"] = f"confirmation_form:{field}"

    normalized["_extraction_metadata"] = {
        "extraction_mode": "confirmation_patch",
        "llm_status": "not_used_for_confirmation_patch",
        "fallback_reason": None,
        "normalization_source": "confirmation_patch_via_normalizer",
        "explicit_params": _param_snapshot(normalized),
        "normalized_params": _public_params_snapshot(normalized),
        "confirmation_patch": deepcopy(patch),
        "llm_raw_response": None,
        "llm_parsed_json": None,
        "llm_api_key_present": False,
        "llm_base_url": None,
        "llm_model": None,
        "llm_timeout_seconds": None,
    }
    return normalized


def _confirmation_patch_note(patch: dict[str, Any]) -> str:
    parts = []
    for field, entry in (patch.get("engineering_parameters") or {}).items():
        if not isinstance(entry, dict):
            continue
        value = entry.get("value")
        if value in (None, ""):
            continue
        unit = entry.get("unit") or ""
        suffix = f" {unit}" if unit else ""
        parts.append(f"{field}={value}{suffix}")
    joined = "; ".join(parts) if parts else "no valid selected fields"
    return f"确认表单：{joined}"


def _entry_signature(entry: Any) -> tuple[Any, Any]:
    if not isinstance(entry, dict):
        return (None, None)
    return (entry.get("value"), entry.get("unit"))


def _patch_param_item(
    field: str,
    entry: dict[str, Any],
    previous_entry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item = {
        "field": field,
        "value": entry.get("value"),
        "unit": entry.get("unit"),
        "source": entry.get("source"),
        "new_source": entry.get("source"),
        "status": entry.get("status"),
        "requires_confirmation": bool(entry.get("requires_confirmation")),
        "category": "engineering_parameter",
        "kind": "engineering_parameter",
    }
    if previous_entry:
        item["previous_value"] = previous_entry.get("value")
        item["previous_unit"] = previous_entry.get("unit")
        item["previous_source"] = previous_entry.get("source")
    return item


def _patch_context_item(
    field: str,
    value: Any,
    previous_value: Any = None,
) -> dict[str, Any]:
    item = {
        "field": field,
        "value": value,
        "unit": "",
        "source": "mission_context",
        "new_source": "mission_context",
        "status": "user_explicit_context",
        "requires_confirmation": False,
        "category": "mission_context",
        "kind": "mission_context",
    }
    if previous_value not in (None, "", []):
        item["previous_value"] = previous_value
        item["previous_source"] = "mission_context"
    return item


def _build_patch_view(
    previous_state: dict[str, Any],
    latest_params: dict[str, Any],
    latest_context: dict[str, Any],
    *,
    round_label: str | None = None,
    confirmed_at_round: int | None = None,
) -> dict[str, Any]:
    previous_explicit = previous_state.get("explicit_parameters") or {}
    previous_normalized = previous_state.get("normalized_parameters") or {}
    previous_context = previous_state.get("mission_context") or {}
    latest_explicit = _extract_explicit_parameters(latest_params)

    added: list[dict[str, Any]] = []
    modified: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []
    latest_keys: set[str] = set()

    for key, entry in latest_explicit.items():
        if key.startswith("_") or not _is_explicit_param_entry(entry):
            continue
        latest_keys.add(key)
        previous_entry = previous_explicit.get(key)
        if not _is_explicit_param_entry(previous_entry):
            previous_entry = previous_normalized.get(key)
        if not _is_available_param_entry(previous_entry):
            item = _patch_param_item(key, entry)
            item.update({
                "action": "added",
                "patch_source": "natural_language_update",
                "update_origin": "natural_language_update",
                "round_label": round_label,
                "confirmed_at_round": confirmed_at_round,
            })
            added.append(item)
        elif _entry_signature(entry) != _entry_signature(previous_entry):
            item = _patch_param_item(key, entry, previous_entry)
            item.update({
                "action": "modified",
                "source": "user_updated",
                "new_source": "user_updated",
                "extracted_source": entry.get("source"),
                "patch_source": "natural_language_update",
                "update_origin": "natural_language_update",
                "round_label": round_label,
                "confirmed_at_round": confirmed_at_round,
            })
            modified.append(item)

    for key, entry in previous_explicit.items():
        if key.startswith("_") or key in latest_keys or not _is_explicit_param_entry(entry):
            continue
        item = _patch_param_item(key, entry)
        item.update({
            "action": "retained",
            "patch_source": "natural_language_update",
            "update_origin": "natural_language_update",
            "round_label": round_label,
            "confirmed_at_round": confirmed_at_round,
        })
        retained.append(item)

    latest_context_keys: set[str] = set()
    for key, value in (latest_context or {}).items():
        if value in (None, "", []):
            continue
        latest_context_keys.add(key)
        previous_value = previous_context.get(key)
        if previous_value in (None, "", []):
            item = _patch_context_item(key, value)
            item.update({
                "action": "added",
                "patch_source": "natural_language_update",
                "update_origin": "natural_language_update",
                "round_label": round_label,
                "confirmed_at_round": confirmed_at_round,
            })
            added.append(item)
        elif previous_value != value:
            item = _patch_context_item(key, value, previous_value)
            item.update({
                "action": "modified",
                "patch_source": "natural_language_update",
                "update_origin": "natural_language_update",
                "round_label": round_label,
                "confirmed_at_round": confirmed_at_round,
            })
            modified.append(item)

    for key, value in previous_context.items():
        if key in latest_context_keys or value in (None, "", []):
            continue
        item = _patch_context_item(key, value)
        item.update({
            "action": "retained",
            "patch_source": "natural_language_update",
            "update_origin": "natural_language_update",
            "round_label": round_label,
            "confirmed_at_round": confirmed_at_round,
        })
        retained.append(item)

    not_merged: list[dict[str, Any]] = []
    previous_normalized = previous_state.get("normalized_parameters") or {}
    non_explicit_sources = {
        "llm_inferred",
        "rules_inferred",
        "inferred_from_altitude",
        "inferred_from_orbit_type",
        "default_assumption",
        "tool_computed",
        "llm_estimated",
    }
    for key, entry in previous_normalized.items():
        if key.startswith("_") or not isinstance(entry, dict):
            continue
        if entry.get("found") and entry.get("value") is not None and entry.get("source") in non_explicit_sources:
            not_merged.append(_patch_param_item(key, entry))

    for item in previous_state.get("default_assumptions") or []:
        field = item.get("field") if isinstance(item, dict) else str(item)
        if field and not any(existing.get("field") == field for existing in not_merged):
            not_merged.append(
                {
                    "field": field,
                    "value": item.get("value") if isinstance(item, dict) else None,
                    "unit": item.get("unit") if isinstance(item, dict) else "",
                    "source": "default_assumption",
                    "status": "not_merged",
                    "requires_confirmation": True,
                    "category": "engineering_parameter",
                    "kind": "default_assumption",
                }
            )

    return {
        "mode": "supplement_or_modify",
        "source": "natural_language_update",
        "patch_source": "natural_language_update",
        "update_origin": "natural_language_update",
        "round_label": round_label,
        "confirmed_at_round": confirmed_at_round,
        "added": added,
        "modified": modified,
        "retained": retained,
        "not_merged": not_merged[:12],
        "current_missing": [],
    }


def _build_confirmation_patch_view(
    previous_state: dict[str, Any],
    patch_params: dict[str, Any],
    patch: dict[str, Any],
    round_label: str,
    confirmed_at_round: int,
) -> dict[str, Any]:
    previous_explicit = previous_state.get("explicit_parameters") or {}
    previous_normalized = previous_state.get("normalized_parameters") or {}
    engineering = patch.get("engineering_parameters") or {}

    added: list[dict[str, Any]] = []
    modified: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []
    latest_keys: set[str] = set()

    for field in engineering:
        if field not in CONFIRMATION_SUPPORTED_ENGINEERING_FIELDS:
            continue
        entry = patch_params.get(field)
        if not _is_explicit_param_entry(entry):
            continue
        latest_keys.add(field)
        previous_entry = previous_explicit.get(field)
        if not _is_explicit_param_entry(previous_entry):
            previous_entry = previous_normalized.get(field)
        previous_for_diff = previous_entry if isinstance(previous_entry, dict) else None
        item = _patch_param_item(field, entry, previous_for_diff)
        old_source = (previous_for_diff or {}).get("source") or "not_found"
        item.update(
            {
                "source": CONFIRMATION_FORM_SOURCE,
                "new_source": entry.get("source") or "user_confirmed",
                "previous_source": old_source,
                "category": "engineering_parameter",
                "merge_source": CONFIRMATION_FORM_SOURCE,
                "patch_source": CONFIRMATION_FORM_SOURCE,
                "update_origin": CONFIRMATION_FORM_SOURCE,
                "round_label": round_label,
                "confirmed_at_round": confirmed_at_round,
            }
        )

        if not previous_for_diff or not previous_for_diff.get("found"):
            item["action"] = "added"
            added.append(item)
        elif old_source == "default_assumption" and _entry_signature(entry) == _entry_signature(previous_for_diff):
            item["action"] = "confirmed"
            modified.append(item)
        elif _entry_signature(entry) != _entry_signature(previous_for_diff) or old_source != entry.get("source"):
            item["action"] = "modified"
            modified.append(item)
        else:
            item["action"] = "confirmed"
            modified.append(item)

    for field, entry in previous_explicit.items():
        if field.startswith("_") or field in latest_keys or not _is_explicit_param_entry(entry):
            continue
        retained_item = _patch_param_item(field, entry)
        retained_item["action"] = "retained"
        retained_item["round_label"] = round_label
        retained_item["confirmed_at_round"] = confirmed_at_round
        retained_item["patch_source"] = CONFIRMATION_FORM_SOURCE
        retained_item["update_origin"] = CONFIRMATION_FORM_SOURCE
        retained.append(retained_item)

    not_merged: list[dict[str, Any]] = []
    for item in previous_state.get("default_assumptions") or []:
        field = item.get("field") if isinstance(item, dict) else str(item)
        if not field or field in latest_keys:
            continue
        not_merged.append(
            {
                "field": field,
                "value": item.get("value") if isinstance(item, dict) else None,
                "unit": item.get("unit") if isinstance(item, dict) else "",
                "source": "default_assumption",
                "status": "not_selected_in_confirmation_form",
                "requires_confirmation": True,
                "category": "engineering_parameter",
                "kind": "default_assumption",
                "action": "not_selected",
                "round_label": round_label,
                "confirmed_at_round": confirmed_at_round,
                "patch_source": CONFIRMATION_FORM_SOURCE,
                "update_origin": CONFIRMATION_FORM_SOURCE,
            }
        )

    return {
        "mode": "confirmation_form",
        "source": CONFIRMATION_FORM_SOURCE,
        "patch_source": CONFIRMATION_FORM_SOURCE,
        "update_origin": CONFIRMATION_FORM_SOURCE,
        "round_label": round_label,
        "confirmed_at_round": confirmed_at_round,
        "raw_action_note": patch.get("raw_action_note"),
        "added": added,
        "modified": modified,
        "retained": retained,
        "not_merged": not_merged[:12],
        "current_missing": [],
    }


def _format_patch_value(value: Any, unit: Any = None) -> str:
    if value in (None, ""):
        return "-"
    suffix = f" {unit}" if unit not in (None, "") else ""
    return f"{value}{suffix}"


def _log_patch_modifications(patch_view: dict[str, Any] | None, round_number: int) -> None:
    for item in (patch_view or {}).get("modified") or []:
        if item.get("category") != "engineering_parameter":
            continue
        field = item.get("field") or "-"
        old_value = _format_patch_value(item.get("previous_value"), item.get("previous_unit"))
        new_value = _format_patch_value(item.get("value"), item.get("unit"))
        append_execution_log(
            "parameter_overwritten",
            f"{field}: {old_value} -> {new_value}",
            details={
                "field": field,
                "old_value": old_value,
                "new_value": new_value,
                "old_source": item.get("previous_source"),
                "new_source": item.get("new_source") or item.get("source"),
                "patch_source": item.get("patch_source"),
            },
            round_number=round_number,
        )


def _patch_missing_names(
    missing: list[dict[str, Any]],
    orbit_metadata: dict[str, Any] | None,
    mission_context: dict[str, Any] | None = None,
) -> list[str]:
    names: list[str] = []
    names.extend(str(item) for item in (orbit_metadata or {}).get("missing_core_elements", []) if item)
    for item in missing or []:
        name = item.get("parameter") or item.get("description")
        if name:
            names.append(str(name))
    ctx = mission_context or {}
    context_text = " ".join(
        str(value).lower()
        for value in (ctx.get("mission_type"), ctx.get("payload_type"))
        if value not in (None, "", [])
    )
    if any(term in context_text for term in ("remote_sensing", "optical", "multispectral", "sar", "遥感", "光学")):
        for field in (
            "ground_resolution_m",
            "swath_width_km",
            "daily_data_volume_GB",
            "downlink_rate_Mbps",
        ):
            if ctx.get(field) in (None, "", []):
                names.append(field)
    return list(dict.fromkeys(names))


def _param_snapshot(params: dict[str, Any]) -> dict[str, Any]:
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


def _public_params_snapshot(params: dict[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(entry)
        for key, entry in params.items()
        if (not key.startswith("_") or key == "_orbit_semantics") and isinstance(entry, dict)
    }


def _items_to_dicts(items: list[Any] | None) -> list[dict[str, Any]]:
    result = []
    for item in items or []:
        if hasattr(item, "to_dict"):
            result.append(item.to_dict())
        elif isinstance(item, dict):
            result.append(deepcopy(item))
        else:
            result.append({"value": str(item)})
    return result


def _default_assumptions_from_orbit(
    params: dict[str, Any],
    orbit_metadata: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    defaults = []
    for field in (orbit_metadata or {}).get("defaulted_parameters", []):
        entry = params.get(field, {})
        defaults.append({
            "field": field,
            "value": entry.get("value"),
            "unit": entry.get("unit"),
            "source": entry.get("source", "default_assumption"),
            "requires_confirmation": True,
        })
    return defaults


def _build_advisor_report(
    *,
    params: dict[str, Any],
    mission_context: dict[str, Any],
    missing: list[dict[str, Any]],
    orbit_conflicts: list[Any],
    validation_results: list[Any],
    task_results: list[dict[str, Any]],
    orbit_metadata: dict[str, Any],
    raw_user_input: str,
    raw_input_history: list[str] | None = None,
    current_round_input: str | None = None,
    report_status: str | None = None,
    core_gate_passed: bool | None = None,
) -> dict[str, Any]:
    default_assumptions = _default_assumptions_from_orbit(params, orbit_metadata)
    advisor_input = {
        "report_status": report_status,
        "raw_input_history": list(raw_input_history or [raw_user_input]),
        "current_round_input": current_round_input or raw_user_input,
        "explicit_parameters": _extract_explicit_parameters(params),
        "normalized_parameters": params,
        "normalized_params": params,
        "mission_context": mission_context,
        "inferred_parameters": list((orbit_metadata or {}).get("inferred_parameters", [])),
        "default_assumptions": default_assumptions,
        "missing_parameters": missing,
        "missing_params": missing,
        "consistency_issues": orbit_conflicts,
        "validation_results": validation_results,
        "tool_results": task_results,
        "task_results": task_results,
        "orbit_metadata": orbit_metadata,
        "raw_user_input": raw_user_input,
        "core_gate_passed": core_gate_passed,
    }
    return generate_design_advice(advisor_input)


def _store_current_design_state(
    *,
    raw_input_history: list[str],
    recent_user_input: str,
    params: dict[str, Any],
    mission_context: dict[str, Any],
    missing: list[dict[str, Any]],
    orbit_metadata: dict[str, Any],
    orbit_conflicts: list[Any],
    validation_results: list[Any],
    task_results: list[dict[str, Any]],
    report: str,
    advisor_report: dict[str, Any],
    report_status: str,
    skip_reason: str | None,
    patch_view: dict[str, Any] | None = None,
    execute_all_tasks_called: bool = False,
    report_filename: str | None = None,
    report_path: str | None = None,
    download_label: str | None = None,
    state_key: str = "current_design_state",
    audit_round: int | None = None,
) -> None:
    st.session_state[state_key] = {
        "raw_input_history": list(raw_input_history),
        "design_round": len(raw_input_history),
        "audit_round": audit_round if audit_round is not None else len(raw_input_history),
        "recent_input": recent_user_input,
        "explicit_parameters": _extract_explicit_parameters(params),
        "mission_context": deepcopy(mission_context),
        "normalized_parameters": _public_params_snapshot(params),
        "orbit_metadata": deepcopy(orbit_metadata),
        "inferred_parameters": list((orbit_metadata or {}).get("inferred_parameters", [])),
        "default_assumptions": _default_assumptions_from_orbit(params, orbit_metadata),
        "missing_parameters": deepcopy(missing),
        "missing_core_elements": list((orbit_metadata or {}).get("missing_core_elements", [])),
        "consistency_issues": _items_to_dicts(orbit_conflicts),
        "validation_results": _items_to_dicts(validation_results),
        "tool_results": deepcopy(task_results),
        "report_markdown": report,
        "advisor_report": deepcopy(advisor_report),
        "report_status": report_status,
        "skip_reason": skip_reason,
        "patch_view": deepcopy(patch_view or {}),
        "execute_all_tasks_called": execute_all_tasks_called,
        "report_filename": report_filename,
        "report_path": report_path,
        "download_label": download_label,
        "state_key": state_key,
        "is_pending_candidate": state_key == PENDING_DESIGN_STATE_KEY,
    }


def _detect_unsupported_requests(user_text: str) -> list[dict[str, str]]:
    """Detect analysis requests that do not have deterministic tools."""

    if not user_text:
        return []

    text_lower = user_text.lower()
    request_specs = [
        (
            "communication_link_estimate",
            "通信链路概念估算",
            ["通信链路", "链路预算", "communication link", "link budget"],
        ),
        (
            "thermal_control_estimate",
            "热控概念估算",
            ["热控", "热分析", "thermal control", "thermal analysis"],
        ),
        (
            "attitude_control_estimate",
            "姿态控制概念估算",
            ["姿控", "姿态控制", "adcs", "attitude control", "pointing"],
        ),
        (
            "propulsion_estimate",
            "推进概念估算",
            ["推进", "推进剂", "propulsion", "delta-v", "dv", "Δv"],
        ),
        (
            "risk_estimate",
            "风险概念估算",
            ["风险", "risk"],
        ),
        (
            "coverage_revisit_estimate",
            "覆盖/重访外部仿真需求",
            ["重访", "覆盖", "revisit", "coverage"],
        ),
    ]

    extra_requests = []
    for task_id, name, keywords in request_specs:
        if any(keyword.lower() in text_lower for keyword in keywords):
            extra_requests.append(
                {
                    "task_id": task_id,
                    "name": name,
                    "description": f"User requested unsupported analysis related to: {name}",
                }
            )
    return extra_requests


def _save_report(report: str, prefix: str) -> tuple[str, str]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outputs_dir = os.path.join("outputs", "reports")
    os.makedirs(outputs_dir, exist_ok=True)
    filename = f"{prefix}_{timestamp}.md"
    report_path = os.path.join(outputs_dir, filename)
    with open(report_path, "w", encoding="utf-8") as file:
        file.write(report)
    return filename, report_path


def build_mission_guidance(user_input: str) -> dict[str, Any]:
    """Build Phase 2 mission-level understanding and candidate drafts."""

    context = interpret_mission_request(user_input)
    constraints = build_constraint_rows(context)
    drafts = generate_candidate_design_drafts(context)
    report = _generate_mission_guidance_report(user_input, context, constraints, drafts)
    log_entries = [
        "当前选择的模式：任务级需求模式。",
        "已完成任务级需求理解。",
        "已识别缺失设计驱动，并生成候选参数草案。",
        "本阶段未调用 deterministic tools，也未生成正式工程验证报告。",
    ]
    if context.get("input_type"):
        log_entries.append(f"识别输入类型：{context['input_type']}。")
    if context.get("mission_objective"):
        log_entries.append(f"识别任务目标：{context['mission_objective']}。")
    if context.get("target_region"):
        log_entries.append(f"识别目标区域：{context['target_region']}。")
    if context.get("revisit_requirement_hours") is not None:
        log_entries.append(f"识别重访/访问需求：{context['revisit_requirement_hours']} hours。")
    for requirement in context.get("performance_requirements", []):
        unit = requirement.get("unit") or ""
        log_entries.append(
            f"识别性能需求：{requirement.get('name')} = {requirement.get('value')} {unit}。"
        )
    missing_names = [
        row["约束项"] for row in constraints
        if row.get("状态") == "待补充"
    ]
    if missing_names:
        log_entries.append(f"待补充约束：{', '.join(missing_names)}。")
    log_entries.append(f"已生成 {len(drafts)} 个候选草案，均为 conceptual / not_verified。")
    return {
        "mode": "mission_level_phase2",
        "user_input": user_input,
        "mission_context": context,
        "constraints": constraints,
        "candidate_drafts": drafts,
        "report": report,
        "log_entries": log_entries,
        "tools_called": False,
        "engineering_verified": False,
    }


def _generate_mission_guidance_report(
    user_input: str,
    context: dict[str, Any],
    constraints: list[dict[str, Any]],
    drafts: list[dict[str, Any]],
) -> str:
    lines = [
        "# 任务需求理解与约束补充建议",
        "",
        "本说明用于任务级需求梳理，尚未完成工程参数反推、确定性工具计算或总体设计验证。",
        "",
        "## 用户输入",
        "",
        user_input,
        "",
        "## 初步任务理解",
        "",
        f"- 任务目标：{context.get('mission_objective') or '未明确'}",
        f"- 目标区域：{context.get('target_region') or '未明确'}",
        f"- 输入类型：{context.get('input_type') or '未明确'}",
        f"- 重访/访问需求：{context.get('revisit_requirement_hours') or '未明确'} hours",
        f"- 载荷类型提示：{context.get('payload_type_hint') or '未明确'}",
        "- 性能需求：",
    ]
    requirements = context.get("performance_requirements", [])
    if requirements:
        for requirement in requirements:
            unit = requirement.get("unit") or ""
            lines.append(f"  - {requirement.get('name')}: {requirement.get('value')} {unit}".rstrip())
    else:
        lines.append("  - 未明确")

    lines.extend(["", "## 需要补充的约束", ""])
    for row in constraints:
        if row.get("状态") == "待补充":
            lines.append(f"- {row.get('约束项')}：{row.get('补充建议')}")

    lines.extend(["", "## 候选参数草案", ""])
    for draft in drafts:
        lines.append(f"### {draft.get('draft_name')}")
        lines.append(f"- 轨道候选：{draft.get('orbit_type_candidate')}")
        lines.append(f"- 高度：{draft.get('altitude_range_or_value')}")
        lines.append(f"- 倾角提示：{draft.get('inclination_hint_or_range')}")
        lines.append(f"- 载荷提示：{draft.get('payload_type_hint')}")
        lines.append(f"- 置信度：{draft.get('confidence')}")
        lines.append(f"- 验证状态：{draft.get('verification_status')}")
        lines.append("- 假设：")
        for assumption in draft.get("key_assumptions", []):
            lines.append(f"  - {assumption}")
        lines.append("")

    lines.extend(
        [
            "## 后续步骤",
            "",
            "1. 用户检查候选草案的假设、置信度和未验证项。",
            "2. 选择一个草案后，草案参数会标记为 `user_confirmed_llm_inferred`。",
            "3. 被采用的草案进入参数级流程，继续进行校验、轨道一致性检查和 deterministic tools 计算。",
            "",
            "> 注意：草案阶段不是正式总体设计报告，也不是工程验证结果。",
        ]
    )
    return "\n".join(lines)


def _param_value(params: dict[str, Any], key: str) -> Any:
    entry = params.get(key, {})
    if entry.get("found") and entry.get("value") is not None:
        return entry.get("value")
    return None


def _append_extraction_log(log_entries: list[str], params: dict[str, Any]) -> None:
    metadata = params.get("_extraction_metadata", {})
    mode = metadata.get("extraction_mode") or "unknown"
    model = metadata.get("llm_model") or "未配置"
    status = metadata.get("llm_status") or "unknown"
    fallback_reason = metadata.get("fallback_reason")

    log_entries.append(f"步骤 1/6：参数提取完成，模式：{mode}。")
    if mode == "llm":
        log_entries.append(f"LLM 提取成功，模型：{model}。")
    elif mode == "mission_draft_confirmed":
        log_entries.append("用户已采用任务级候选草案，草案参数来源标记为 user_confirmed_llm_inferred。")
    elif "fallback" in mode:
        reason = fallback_reason or status
        log_entries.append(f"已使用规则 fallback，原因：{reason}。")
    else:
        log_entries.append(f"LLM 状态：{status}，模型：{model}。")


def _append_parameter_log(log_entries: list[str], params: dict[str, Any]) -> None:
    key_labels = {
        "orbit_type": "orbit_type",
        "orbit_altitude_km": "orbit_altitude_km",
        "payload_mass_kg": "payload_mass_kg",
        "power_required_w": "power_required_w",
        "orbit_inclination_deg": "inclination_deg",
        "orbit_period_min": "orbit_period_min",
    }
    for key, label in key_labels.items():
        value = _param_value(params, key)
        if value is not None:
            unit = params.get(key, {}).get("unit")
            suffix = f" {unit}" if unit else ""
            log_entries.append(f"识别 {label} = {value}{suffix}。")


def _append_intent_log(log_entries: list[str], params: dict[str, Any]) -> None:
    context = params.get("_mission_context") or params.get("_extraction_metadata", {}).get("mission_context") or {}
    if not context:
        return
    objective = context.get("mission_objective")
    target = context.get("target_region")
    if objective:
        log_entries.append(f"识别任务意图：{objective}。")
    if target:
        log_entries.append(f"识别目标区域：{target}。")
    for requirement in context.get("performance_requirements", []):
        name = requirement.get("name", "performance_requirement")
        value = requirement.get("value")
        unit = requirement.get("unit") or ""
        log_entries.append(f"识别性能需求：{name} = {value} {unit}。")


def _append_mission_context_log(
    log_entries: list[str],
    mission_context: dict[str, Any],
) -> None:
    labels = {
        "mission_type": "任务类型",
        "target_region": "目标区域",
        "revisit_time_h": "重访需求",
        "payload_type": "载荷类型",
        "ground_resolution_m": "地面分辨率",
        "swath_width_km": "幅宽",
        "daily_data_volume_GB": "日数据量",
        "downlink_rate_Mbps": "下行速率",
        "mission_lifetime_year": "任务寿命",
        "pointing_accuracy_deg": "指向精度",
    }
    for key, label in labels.items():
        value = mission_context.get(key)
        if value not in (None, "", []):
            log_entries.append(f"识别 mission_context：{label} = {value}。")


def _append_inference_log(log_entries: list[str], inference_metadata: dict[str, Any]) -> None:
    mode = inference_metadata.get("mode", "none")
    log_entries.append(f"缺失参数推断完成，模式：{mode}。")
    for field in inference_metadata.get("inferred_parameters", []):
        log_entries.append(f"LLM 推断候选参数：{field}，需用户确认。")
    for field in inference_metadata.get("rules_inferred_parameters", []):
        log_entries.append(f"规则 fallback 推断候选参数：{field}，需用户确认。")
    for note in inference_metadata.get("ambiguity_notes", []):
        log_entries.append(f"歧义提示：{note}")


def _append_orbit_log(
    log_entries: list[str],
    orbit_metadata: dict[str, Any],
    params: dict[str, Any],
) -> None:
    log_entries.append("步骤 2/6：轨道参数推断完成。")
    for field in orbit_metadata.get("inferred_parameters", []):
        entry = params.get(field, {})
        value = entry.get("value")
        unit = entry.get("unit")
        if value is None:
            continue
        source = entry.get("source", "inferred")
        suffix = f" {unit}" if unit else ""
        log_entries.append(f"推断 {field} = {value}{suffix}，来源：{source}。")

    for field in orbit_metadata.get("defaulted_parameters", []):
        log_entries.append(f"{field} 未提供，默认采用 0 deg，需用户确认。")

    for warning in orbit_metadata.get("warnings", []):
        log_entries.append(f"轨道风险提示：{warning}")

    missing_core = orbit_metadata.get("missing_core_elements", [])
    if missing_core:
        log_entries.append(f"核心轨道参数不完整：{', '.join(missing_core)}。")
        for field in missing_core:
            reason = orbit_metadata.get("missing_reasons", {}).get(field)
            if reason:
                log_entries.append(f"{field} 缺失原因：{reason}")


def _append_validation_log(
    log_entries: list[str],
    validation_results: list[Any],
    orbit_conflicts: list[Any],
) -> None:
    log_entries.append("步骤 3/6：一致性检查完成。")
    severe_count = sum(1 for item in validation_results if getattr(item, "level", "") == "severe")
    warning_count = sum(1 for item in validation_results if getattr(item, "level", "") == "warning")
    orbit_severe_count = sum(1 for item in orbit_conflicts if getattr(item, "level", "") == "severe")
    orbit_warning_count = sum(1 for item in orbit_conflicts if getattr(item, "level", "") == "warning")
    log_entries.append(
        f"参数校验：severe={severe_count}，warning={warning_count}；"
        f"轨道一致性：severe={orbit_severe_count}，warning={orbit_warning_count}。"
    )


def _render_initial_state() -> None:
    render_status_card(
        can_continue=False,
        skip_reason=None,
        orbit_metadata=None,
        validation_results=None,
        orbit_conflicts=None,
        missing=None,
    )
    render_parameter_cards(None, None, inactive=True)
    render_parameter_understanding_panel(
        params=None,
        orbit_metadata=None,
        mission_context=None,
        missing_params=None,
        validation_results=None,
        orbit_conflicts=None,
        inactive=True,
    )
    render_summary_panel(
        inactive=True,
        can_continue=False,
        skip_reason=None,
        missing=None,
        validation_results=None,
        orbit_metadata=None,
        orbit_conflicts=None,
        report=None,
    )
    render_advisor_panel(None)
    render_execution_log(get_execution_logs())


def _is_blocked_status(report_status: str | None, skip_reason: str | None) -> bool:
    if skip_reason in {
        "severe_user_provided_parameter",
        "severe_explicit_orbit_conflict",
        "missing_core_orbital_elements",
        "severe_validation_or_orbit_conflict",
    }:
        return True
    return report_status in {"存在严重冲突", "需要补充参数"}


def _render_saved_design_state(design_state: dict[str, Any]) -> None:
    """Render the saved current design state without rerunning the pipeline."""
    append_execution_log(
        "saved_state_rendered",
        "页面重新渲染已有 current_design_state，未覆盖 raw input history。",
        details={
            "report_status": design_state.get("report_status"),
            "raw_input_rounds": len(design_state.get("raw_input_history") or []),
        },
        round_number=(
            design_state.get("audit_round")
            or design_state.get("design_round")
            or len(design_state.get("raw_input_history") or [])
        ),
    )
    params = design_state.get("normalized_parameters") or {}
    orbit_metadata = design_state.get("orbit_metadata") or {
        "missing_core_elements": design_state.get("missing_core_elements", []),
        "inferred_parameters": design_state.get("inferred_parameters", []),
        "defaulted_parameters": [
            item.get("field")
            for item in design_state.get("default_assumptions", [])
            if isinstance(item, dict) and item.get("field")
        ],
        "element_table": [],
    }
    mission_context = design_state.get("mission_context") or {}
    missing = design_state.get("missing_parameters") or []
    validation_results = design_state.get("validation_results") or []
    orbit_conflicts = design_state.get("consistency_issues") or []
    task_results = design_state.get("tool_results") or []
    report = design_state.get("report_markdown") or ""
    advisor_report = design_state.get("advisor_report") or {}
    patch_view = design_state.get("patch_view") or {}
    skip_reason = design_state.get("skip_reason")
    can_continue = not _is_blocked_status(design_state.get("report_status"), skip_reason)

    render_current_design_summary_card(design_state)
    render_status_card(
        can_continue=can_continue,
        skip_reason=skip_reason,
        orbit_metadata=orbit_metadata,
        validation_results=validation_results,
        orbit_conflicts=orbit_conflicts,
        missing=missing,
    )
    render_parameter_cards(params, orbit_metadata, inactive=False)
    render_parameter_understanding_panel(
        params=params,
        orbit_metadata=orbit_metadata,
        mission_context=mission_context,
        missing_params=missing,
        validation_results=validation_results,
        orbit_conflicts=orbit_conflicts,
        inactive=False,
    )
    render_patch_view_panel(patch_view)
    render_summary_panel(
        inactive=False,
        can_continue=can_continue,
        skip_reason=skip_reason,
        missing=missing,
        validation_results=validation_results,
        orbit_metadata=orbit_metadata,
        orbit_conflicts=orbit_conflicts,
        report=report,
    )
    render_advisor_panel(advisor_report)
    render_confirmation_panel(design_state)
    render_execution_log(get_execution_logs())
    render_raw_input_history_panel(design_state)
    render_debug_panel(
        params=params,
        validation_results=validation_results,
        orbit_metadata=orbit_metadata,
        orbit_conflicts=orbit_conflicts,
        task_results=task_results,
        execute_all_tasks_called=bool(design_state.get("execute_all_tasks_called")),
        skip_reason=skip_reason,
    )
    if report and design_state.get("report_filename") and design_state.get("report_path"):
        render_report_download(
            report,
            design_state.get("report_filename"),
            design_state.get("download_label") or "下载 Markdown 报告",
            design_state.get("report_path"),
        )


def _render_mission_initial_state() -> None:
    render_mission_guidance_panel(None, inactive=True)
    render_execution_log(["尚未开始任务级引导。"])
    render_mission_debug_panel(None)


def _run_mission_guidance(user_input: str) -> None:
    guidance = build_mission_guidance(user_input)
    st.session_state["mission_guidance"] = guidance
    st.session_state["run_status"] = "需要补充参数"
    _render_mission_guidance(guidance)


def _render_mission_guidance(guidance: dict[str, Any]) -> None:
    selected_draft_id = render_mission_guidance_panel(guidance, inactive=False)
    if selected_draft_id:
        draft = _find_draft(guidance, selected_draft_id)
        if draft is None:
            st.warning("未找到所选草案，请重新生成候选草案。")
            return
        params = build_params_from_confirmed_draft(
            draft,
            guidance.get("mission_context", {}),
        )
        external_results = build_external_simulation_placeholders(
            guidance.get("mission_context", {}),
            draft,
        )
        log_entries = [
            "当前选择的模式：任务级需求模式。",
            f"用户采用候选草案：{draft.get('draft_name')}。",
            "草案参数已标记为 user_confirmed_llm_inferred，并进入参数级设计流程。",
        ]
        _append_extraction_log(log_entries, params)
        _append_intent_log(log_entries, params)
        _append_parameter_log(log_entries, params)
        _run_pipeline_with_params(
            guidance.get("user_input", ""),
            params,
            log_entries,
            pre_task_results=external_results,
            mission_context=guidance.get("mission_context", {}),
            raw_input_history=[guidance.get("user_input", "")],
            recent_user_input=guidance.get("user_input", ""),
        )
        return

    render_execution_log(guidance["log_entries"])
    render_mission_debug_panel(guidance)
    render_debug_panel(
        params=None,
        validation_results=None,
        orbit_metadata=None,
        orbit_conflicts=None,
        task_results=None,
        execute_all_tasks_called=False,
        skip_reason=None,
    )


def _run_pipeline(user_input: str) -> None:
    append_execution_log(
        "new_design_started",
        "用户点击“开始新方案”，系统开始从当前输入创建新的参数级 design_state。",
        details={"input_length": len(user_input)},
        round_number=1,
    )
    append_execution_log(
        "pipeline_rerun_started",
        "参数级 pipeline 开始运行：validation / orbit_consistency / tools / advisor 将按门控结果执行。",
        details={"source": "new_design_started"},
        round_number=1,
    )
    log_entries = [
        "当前选择的模式：参数级设计模式。",
        "已进入参数级分析流程。",
        "接收用户任务需求。",
    ]
    params = extract_mission_parameters(user_input)
    _append_extraction_log(log_entries, params)
    _append_parameter_log(log_entries, params)

    # Extract mission context (explicit only, no inference, no gate participation)
    llm_parsed = params.get("_extraction_metadata", {}).get("llm_parsed_json")
    mission_context = extract_mission_context(user_input, llm_parsed_json=llm_parsed)
    st.session_state["mission_context"] = mission_context
    if _has_context_values(mission_context):
        log_entries.append("已提取任务上下文（显式信息，未参与核心门控）。")
        _append_mission_context_log(log_entries, mission_context)

    _run_pipeline_with_params(
        user_input,
        params,
        log_entries,
        mission_context=mission_context,
        raw_input_history=[user_input],
        recent_user_input=user_input,
    )


def _run_pipeline_update(user_input: str) -> None:
    previous_state = st.session_state.get("current_design_state") or {}
    history = list(previous_state.get("raw_input_history") or [])
    history.append(user_input)
    current_round = len(history)
    append_execution_log(
        "design_updated_from_natural_language",
        "用户点击“补充 / 修改当前方案”，自然语言补充将与当前显式参数合并。",
        details={"raw_input_rounds": current_round, "input_length": len(user_input)},
        round_number=current_round,
    )
    append_execution_log(
        "pipeline_rerun_started",
        "补充 / 修改当前方案后，参数级 pipeline 将重新运行。",
        details={"source": "natural_language_update"},
        round_number=current_round,
    )

    log_entries = [
        "当前选择的模式：参数级设计模式。",
        "已进入补充 / 修改当前方案流程。",
        f"当前方案累计输入轮次：{len(history)}。",
    ]

    latest_params = extract_mission_parameters(user_input)
    _append_extraction_log(log_entries, latest_params)

    llm_parsed = latest_params.get("_extraction_metadata", {}).get("llm_parsed_json")
    latest_context = extract_mission_context(user_input, llm_parsed_json=llm_parsed)
    merged_params, mission_context, patch_view = apply_user_patch_to_design_state(
        previous_state,
        latest_params,
        latest_context,
        round_label=f"round {current_round} / natural_language_update",
        confirmed_at_round=current_round,
    )
    st.session_state["mission_context"] = mission_context

    _log_patch_modifications(patch_view, current_round)
    stale_fields = [item.get("field") for item in patch_view.get("stale", []) if item.get("field")]
    log_entries.append("已将本轮显式 patch 应用到上一轮 current_design_state；本轮未提到的字段已保留。")
    if stale_fields:
        log_entries.append(f"受影响的派生参数已标记为 stale 并将在本轮重算：{', '.join(stale_fields)}。")
    log_entries.append("mission_context 仅作为只读旁路合并，用于展示和设计建议。")
    if _has_context_values(mission_context):
        _append_mission_context_log(log_entries, mission_context)
    _append_parameter_log(log_entries, merged_params)

    _run_pipeline_with_params(
        "\n".join(history),
        merged_params,
        log_entries,
        mission_context=mission_context,
        raw_input_history=history,
        recent_user_input=user_input,
        patch_view=patch_view,
        preserve_current_on_block=True,
    )


def _run_pipeline_update_from_patch(patch: dict[str, Any]) -> None:
    previous_state = (
        st.session_state.get(PENDING_DESIGN_STATE_KEY)
        or st.session_state.get("current_design_state")
        or {}
    )
    history = list(previous_state.get("raw_input_history") or [])
    note = patch.get("raw_action_note") or _confirmation_patch_note(patch)
    confirmation_round, rerun_round = _confirmation_audit_rounds(history)
    round_label = f"round {confirmation_round} / confirmation_form"
    append_execution_log(
        "confirmation_patch_created",
        "系统接收到参数确认表单生成的 confirmation_patch。",
        details={
            "patch_source": CONFIRMATION_FORM_SOURCE,
            "fields": list((patch.get("engineering_parameters") or {}).keys()),
        },
        round_number=confirmation_round,
    )

    log_entries = [
        "当前选择的模式：参数级设计模式。",
        "已进入结构化参数确认表单应用流程。",
        f"当前方案累计输入轮次：{len(history)}。",
        f"确认表单作为审计轮次 R{confirmation_round} 追加记录，后续重新运行使用 R{rerun_round}。",
        "confirmation_patch 只包含用户勾选并确认的字段，不直接修改 normalized_parameters。",
    ]

    mission_context = previous_state.get("mission_context") or {}
    patch_params = _build_params_from_confirmation_patch(patch)
    merged_params, mission_context, merge_patch_view = apply_user_patch_to_design_state(
        previous_state,
        patch_params,
        mission_context,
        round_label=round_label,
        confirmed_at_round=confirmation_round,
    )
    st.session_state["mission_context"] = mission_context
    patch_view = _build_confirmation_patch_view(previous_state, patch_params, patch, round_label, confirmation_round)
    if merge_patch_view.get("stale"):
        patch_view["stale"] = merge_patch_view["stale"]

    append_execution_log(
        "confirmation_patch_applied",
        "用户确认的 patch 已合并为 user_confirmed 显式参数，并将重新运行完整参数级流程。",
        details={
            "patch_source": CONFIRMATION_FORM_SOURCE,
            "fields": list((patch.get("engineering_parameters") or {}).keys()),
        },
        round_number=confirmation_round,
    )
    append_execution_log(
        "pipeline_rerun_started",
        "应用 confirmation_patch 后，参数级 pipeline 将重新运行。",
        details={"source": CONFIRMATION_FORM_SOURCE},
        round_number=rerun_round,
    )
    _log_patch_modifications(patch_view, confirmation_round)

    log_entries.append("confirmation_patch 已通过 normalizer 转为 user_confirmed 显式参数。")
    log_entries.append("应用 patch 后将重新运行 validation、orbit_consistency、orbit_interpreter、core gate、tools、report 和 advisor。")
    _append_parameter_log(log_entries, merged_params)

    _run_pipeline_with_params(
        "\n".join(history),
        merged_params,
        log_entries,
        mission_context=mission_context,
        raw_input_history=history,
        recent_user_input=note,
        patch_view=patch_view,
        preserve_current_on_block=True,
        round_number_override=rerun_round,
    )


def _build_pre_inference_orbit_metadata(
    params: dict[str, Any],
    pre_orbit_conflicts: list[Any],
) -> dict[str, Any]:
    severe = any(getattr(item, "level", "") == "severe" for item in pre_orbit_conflicts)
    return {
        "status": "pre_inference_conflict" if severe else "pre_inference_checked",
        "inferred_parameters": [],
        "defaulted_parameters": [],
        "missing_core_elements": [],
        "missing_recommended_elements": [],
        "missing_reasons": {},
        "next_step_suggestions": [
            "Please resolve explicit orbit conflicts before automatic orbit completion."
        ] if severe else [],
        "assumptions": [],
        "warnings": [],
        "confidence": 1.0,
        "inference_details": {},
        "element_table": build_orbital_elements_table(params),
    }


def _run_pipeline_with_params(
    user_input: str,
    params: dict[str, Any],
    log_entries: list[str],
    pre_task_results: list[dict[str, Any]] | None = None,
    mission_context: dict[str, Any] | None = None,
    raw_input_history: list[str] | None = None,
    recent_user_input: str | None = None,
    patch_view: dict[str, Any] | None = None,
    preserve_current_on_block: bool = False,
    round_number_override: int | None = None,
) -> None:
    execute_all_tasks_called = False
    skip_reason = None
    task_results: list[dict[str, Any]] = list(pre_task_results or [])

    # Mission context is a read-only side channel for UI/advisor only.
    if mission_context is None:
        mission_context = st.session_state.get("mission_context", {})
    else:
        st.session_state["mission_context"] = mission_context

    missing = identify_missing_parameters(params)
    explicit_validation = validate_parameters(
        params,
        source_filter=EXPLICIT_PARAM_SOURCES,
        include_missing=False,
    )
    explicit_severe = has_severe_errors(explicit_validation)
    pre_orbit_conflicts = validate_orbit_consistency(
        params,
        stage="pre_inference",
        source_filter=EXPLICIT_PARAM_SOURCES,
        user_text=user_input,
    )
    explicit_orbit_severe = has_severe_orbit_conflicts(pre_orbit_conflicts)

    if explicit_severe or explicit_orbit_severe:
        log_entries.append("显式输入参数存在严重异常，跳过缺失参数推断和轨道补全。")
        orbit_metadata = _build_pre_inference_orbit_metadata(params, pre_orbit_conflicts)
        orbit_conflicts = pre_orbit_conflicts
        validation_results = explicit_validation
    else:
        params, inference_metadata = infer_missing_parameters(
            params,
            mission_context={},
            user_text=user_input,
        )
        _append_inference_log(log_entries, inference_metadata)
        missing = identify_missing_parameters(params)

        params, orbit_metadata = interpret_orbit_parameters(params, user_text=user_input)
        _append_orbit_log(log_entries, orbit_metadata, params)
        missing = identify_missing_parameters(params)

        validation_results = validate_parameters(params)
        orbit_conflicts = validate_orbit_consistency(
            params,
            stage="post_inference",
            user_text=user_input,
        )

    _append_validation_log(log_entries, validation_results, orbit_conflicts)

    severe_orbit = has_severe_orbit_conflicts(orbit_conflicts)
    orbit_gate_block = bool(orbit_metadata.get("missing_core_elements"))
    severe = has_severe_errors(validation_results) or severe_orbit
    should_block_normal_flow = severe or orbit_gate_block
    round_number = round_number_override or len(raw_input_history or [user_input])
    validation_severe_count = sum(1 for item in validation_results if getattr(item, "level", "") == "severe")
    validation_warning_count = sum(1 for item in validation_results if getattr(item, "level", "") == "warning")
    orbit_severe_count = sum(1 for item in orbit_conflicts if getattr(item, "level", "") == "severe")
    orbit_warning_count = sum(1 for item in orbit_conflicts if getattr(item, "level", "") == "warning")
    append_execution_log(
        "validation_completed",
        "validation / orbit_consistency 已完成。",
        details={
            "validation_severe": validation_severe_count,
            "validation_warning": validation_warning_count,
            "orbit_severe": orbit_severe_count,
            "orbit_warning": orbit_warning_count,
        },
        round_number=round_number,
    )
    append_execution_log(
        "core_gate_failed" if orbit_gate_block else "core_gate_passed",
        "core orbit gate 未通过。" if orbit_gate_block else "core orbit gate 已通过。",
        details={"missing_core_elements": list(orbit_metadata.get("missing_core_elements") or [])},
        round_number=round_number,
    )

    if explicit_severe:
        skip_reason = "severe_user_provided_parameter"
    elif explicit_orbit_severe:
        skip_reason = "severe_explicit_orbit_conflict"
    elif orbit_gate_block:
        skip_reason = "missing_core_orbital_elements"
    elif severe:
        skip_reason = "severe_validation_or_orbit_conflict"

    if severe:
        append_execution_log(
            "severe_blocked",
            "存在 severe issue，正式计算已阻断。",
            details={"skip_reason": skip_reason},
            round_number=round_number,
        )

    if should_block_normal_flow:
        advisor_report = _build_advisor_report(
            params=params,
            mission_context=mission_context,
            missing=missing,
            orbit_conflicts=orbit_conflicts,
            validation_results=validation_results,
            task_results=task_results,
            orbit_metadata=orbit_metadata,
            raw_user_input=user_input,
            raw_input_history=raw_input_history,
            current_round_input=recent_user_input,
            report_status="存在严重冲突" if severe else "需要补充参数",
            core_gate_passed=not orbit_gate_block,
        )
        log_entries.append("步骤 4/6：工具计算已跳过。")
        log_entries.append(f"未调用 execute_all_tasks，原因：{skip_reason}。")
        append_execution_log(
            "advisor_generated",
            "RAG-enhanced design advisor / next_actions 已生成，用于解释阻断原因和下一步建议。",
            details={"core_gate_passed": not orbit_gate_block, "blocked": True},
            round_number=round_number,
        )
        report = generate_parameter_confirmation_report(
            params,
            missing,
            validation_results,
            orbit_metadata=orbit_metadata,
            orbit_conflicts=orbit_conflicts,
            mission_context=mission_context,
            advisor_report=None,
        )
        log_entries.append("步骤 5/6：已生成参数确认/缺失说明。")
        log_entries.append("步骤 6/6：已生成设计建议与风险提示。")
        st.session_state["run_status"] = "存在严重冲突" if severe else "需要补充参数"
        report_prefix = "parameter_confirmation"
        download_label = "下载参数确认报告"
    else:
        log_entries.append("步骤 4/6：工具计算 / LLM 概念估算。")
        has_altitude = params.get("orbit_altitude_km", {}).get("found", False)
        has_mass = params.get("payload_mass_kg", {}).get("found", False)
        if not has_altitude and not has_mass:
            skip_reason = "missing_basic_task_parameters"
            log_entries.append("未调用 execute_all_tasks，原因：缺少轨道高度和载荷质量。")
        else:
            extra_requests = _detect_unsupported_requests(user_input)
            execute_all_tasks_called = True
            deterministic_results = execute_all_tasks(params, extra_requests=extra_requests)
            task_results = deterministic_results + task_results
            completed = sum(1 for item in task_results if item.get("status") == "completed")
            skipped = sum(1 for item in task_results if item.get("status") == "skipped")
            failed = sum(1 for item in task_results if item.get("status") == "failed")
            append_execution_log(
                "tools_executed",
                "deterministic tools 已运行。",
                details={"completed": completed, "skipped": skipped, "failed": failed},
                round_number=round_number,
            )
            log_entries.append(
                f"已调用 execute_all_tasks，完成 {completed}，跳过 {skipped}，失败 {failed}。"
            )

        advisor_report = _build_advisor_report(
            params=params,
            mission_context=mission_context,
            missing=missing,
            orbit_conflicts=orbit_conflicts,
            validation_results=validation_results,
            task_results=task_results,
            orbit_metadata=orbit_metadata,
            raw_user_input=user_input,
            raw_input_history=raw_input_history,
            current_round_input=recent_user_input,
            report_status="已完成",
            core_gate_passed=not orbit_gate_block,
        )
        append_execution_log(
            "advisor_generated",
            "RAG-enhanced design advisor / next_actions 已生成。",
            details={"core_gate_passed": not orbit_gate_block, "blocked": False},
            round_number=round_number,
        )
        report = generate_report(
            params,
            missing,
            task_results,
            orbit_metadata=orbit_metadata,
            orbit_conflicts=orbit_conflicts,
            mission_context=mission_context,
            advisor_report=None,
        )
        log_entries.append("步骤 5/6：已生成初步设计报告。")
        log_entries.append("步骤 6/6：已生成设计建议与风险提示。")
        st.session_state["run_status"] = "已完成"
        report_prefix = "design_report"
        download_label = "下载 Markdown 报告"

    if patch_view is not None:
        patch_view["current_missing"] = _patch_missing_names(missing, orbit_metadata, mission_context)

    filename, report_path = _save_report(report, report_prefix)
    state_key = (
        PENDING_DESIGN_STATE_KEY
        if preserve_current_on_block and severe
        else "current_design_state"
    )
    _store_current_design_state(
        raw_input_history=raw_input_history or [user_input],
        recent_user_input=recent_user_input or user_input,
        params=params,
        mission_context=mission_context,
        missing=missing,
        orbit_metadata=orbit_metadata,
        orbit_conflicts=orbit_conflicts,
        validation_results=validation_results,
        task_results=task_results,
        report=report,
        advisor_report=advisor_report,
        report_status=st.session_state.get("run_status", "未运行"),
        skip_reason=skip_reason,
        patch_view=patch_view,
        execute_all_tasks_called=execute_all_tasks_called,
        report_filename=filename,
        report_path=report_path,
        download_label=download_label,
        state_key=state_key,
        audit_round=round_number,
    )
    if state_key == "current_design_state":
        st.session_state.pop(PENDING_DESIGN_STATE_KEY, None)

    # --- New UI: status card + parameter understanding panel ---
    rendered_state = st.session_state.get(state_key)
    render_current_design_summary_card(rendered_state)
    render_status_card(
        can_continue=not should_block_normal_flow,
        skip_reason=skip_reason,
        orbit_metadata=orbit_metadata,
        validation_results=validation_results,
        orbit_conflicts=orbit_conflicts,
        missing=missing,
    )

    render_parameter_cards(params, orbit_metadata, inactive=False)

    render_parameter_understanding_panel(
        params=params,
        orbit_metadata=orbit_metadata,
        mission_context=mission_context,
        missing_params=missing,
        validation_results=validation_results,
        orbit_conflicts=orbit_conflicts,
        inactive=False,
    )

    render_patch_view_panel(patch_view)

    render_summary_panel(
        inactive=False,
        can_continue=not should_block_normal_flow,
        skip_reason=skip_reason,
        missing=missing,
        validation_results=validation_results,
        orbit_metadata=orbit_metadata,
        orbit_conflicts=orbit_conflicts,
        report=report,
    )

    # --- New UI: RAG-enhanced design advisor panel ---
    render_advisor_panel(advisor_report)
    render_confirmation_panel(rendered_state)

    render_execution_log(get_execution_logs())
    render_raw_input_history_panel(rendered_state)
    render_debug_panel(
        params=params,
        validation_results=validation_results,
        orbit_metadata=orbit_metadata,
        orbit_conflicts=orbit_conflicts,
        task_results=task_results,
        execute_all_tasks_called=execute_all_tasks_called,
        skip_reason=skip_reason,
    )
    render_report_download(report, filename, download_label, report_path)


def _find_draft(guidance: dict[str, Any], draft_id: str) -> dict[str, Any] | None:
    for draft in guidance.get("candidate_drafts", []):
        if draft.get("draft_id") == draft_id:
            return draft
    return None


def main() -> None:
    st.set_page_config(
        page_title="航天器总体设计 AI Agent Demo",
        page_icon="",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    apply_console_style()

    st.session_state.setdefault("run_status", "未运行")
    header_slot = st.empty()
    render_header(st.session_state["run_status"], target=header_slot)
    mode = render_mode_selector()

    with st.sidebar:
        st.header("使用说明")
        st.markdown(
            """
            本系统用于低轨遥感小卫星概念设计阶段的参数解析、轨道推断、
            deterministic tools 计算和初步报告生成。

            示例：
            - `LEO300km，圆轨道，载荷30kg，功率200W，倾角51.6度`
            - `极地轨道，高度500km，载荷20kg`
            - `太阳同步轨道，高度500km，载荷20kg`
            """
        )
        st.caption("所有输出仅用于概念设计辅助，不构成飞行合格结论。")

    if mode == USE_MODE_MISSION:
        user_input, analyze_button, clear_button = render_mission_input_panel()

        if clear_button:
            st.session_state.pop("mission_guidance", None)
            _render_mission_initial_state()
            return

        if analyze_button and not user_input.strip():
            st.session_state["run_status"] = "未运行"
            st.warning("请输入任务目标后再开始任务理解。")
            _render_mission_initial_state()
            return

        if analyze_button:
            st.session_state["run_status"] = "解析中"
            render_header(st.session_state["run_status"], target=header_slot)
            with st.spinner("正在理解任务需求并生成候选参数草案..."):
                _run_mission_guidance(user_input.strip())
            render_header(st.session_state["run_status"], target=header_slot)
        else:
            guidance = st.session_state.get("mission_guidance")
            if guidance:
                _render_mission_guidance(guidance)
            else:
                _render_mission_initial_state()

        _render_footer()
        return

    _consume_parameter_input_clear_queue()
    user_input, start_new_button, update_button, clear_button = render_input_panel()

    pending_patch = st.session_state.pop("pending_confirmation_patch", None)
    if pending_patch:
        st.session_state.pop("confirmation_table_editor", None)
        if not (st.session_state.get(PENDING_DESIGN_STATE_KEY) or st.session_state.get("current_design_state")):
            st.warning("当前还没有可应用确认表单的方案。请先开始新方案。")
            _render_initial_state()
            _render_footer()
            return
        st.session_state["run_status"] = "解析中"
        render_header(st.session_state["run_status"], target=header_slot)
        with st.spinner("正在应用结构化 confirmation_patch 并重新运行方案..."):
            _run_pipeline_update_from_patch(pending_patch)
        render_header(st.session_state["run_status"], target=header_slot)
        st.rerun()

    pending_confirmation = st.session_state.pop("pending_confirmation_input", None)
    if pending_confirmation:
        st.session_state.pop("confirmation_reply_input", None)
        if not st.session_state.get("current_design_state"):
            st.warning("当前还没有可应用确认的方案。请先开始新方案。")
            _render_initial_state()
            _render_footer()
            return
        st.session_state["run_status"] = "解析中"
        render_header(st.session_state["run_status"], target=header_slot)
        with st.spinner("正在应用用户确认并重新运行方案..."):
            _run_pipeline_update(str(pending_confirmation).strip())
        render_header(st.session_state["run_status"], target=header_slot)
        st.rerun()

    if clear_button:
        st.session_state.pop("current_design_state", None)
        st.session_state.pop(PENDING_DESIGN_STATE_KEY, None)
        st.session_state.pop("mission_context", None)
        _render_initial_state()
        return

    if (start_new_button or update_button) and not user_input.strip():
        st.session_state["run_status"] = "未运行"
        st.warning("请输入任务需求后再开始解析。")
        _render_initial_state()
        return

    if update_button and not st.session_state.get("current_design_state"):
        st.warning("当前还没有可补充的方案。请先点击“开始新方案”。")
        _render_initial_state()
        return

    if start_new_button:
        reset_execution_logs()
        st.session_state["run_status"] = "解析中"
        st.session_state.pop("current_design_state", None)
        st.session_state.pop(PENDING_DESIGN_STATE_KEY, None)
        render_header(st.session_state["run_status"], target=header_slot)
        with st.spinner("正在解析任务需求并生成方案..."):
            _run_pipeline(user_input.strip())
        _queue_parameter_input_clear(update_current=False)
        _queue_parameter_input_clear(update_current=True)
        render_header(st.session_state["run_status"], target=header_slot)
        st.rerun()
    elif update_button:
        st.session_state["run_status"] = "解析中"
        render_header(st.session_state["run_status"], target=header_slot)
        with st.spinner("正在合并补充信息并重新运行方案..."):
            _run_pipeline_update(user_input.strip())
        _queue_parameter_input_clear(update_current=True)
        render_header(st.session_state["run_status"], target=header_slot)
        st.rerun()
    else:
        saved_state = st.session_state.get(PENDING_DESIGN_STATE_KEY) or st.session_state.get("current_design_state")
        if saved_state:
            _render_saved_design_state(saved_state)
        else:
            _render_initial_state()

    _render_footer()


def _render_footer() -> None:
    st.markdown(
        """
        <div style='text-align: center; color: #7b8794; font-size: 0.82rem; margin-top: 2rem;'>
        航天器总体设计 AI Agent Demo · 概念设计阶段辅助工具
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
