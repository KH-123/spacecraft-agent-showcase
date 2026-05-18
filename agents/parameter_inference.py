"""Mission intent parsing and cautious missing-parameter inference.

This module is intentionally lightweight. It never replaces user-provided
values or deterministic tool results. LLM-inferred values are marked
``source="llm_inferred"`` and require confirmation; rules fallback values are
marked ``source="rules_inferred"``.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Tuple

from dotenv import load_dotenv
from openai import OpenAI

from agents.llm_extractor import DEFAULT_BASE_URL, DEFAULT_MODEL, DEFAULT_TIMEOUT_SECONDS

load_dotenv()


INFERABLE_PARAM_UNITS = {
    "orbit_type": None,
    "orbit_altitude_km": "km",
    "orbit_inclination_deg": "deg",
    "orbit_period_min": "min",
    "eccentricity": None,
}


INFERENCE_SYSTEM_PROMPT = """You are a spacecraft conceptual design assistant.

Infer only cautious candidate mission parameters that are missing from the
explicit user input. Do not replace user-provided values. Do not perform
engineering calculations or claim high precision.

Rules:
- Output ONLY valid JSON.
- Use internal parameter names and normalized units.
- Mark every inferred value as requiring confirmation.
- If information is insufficient, leave the value null and explain what is
  missing in ambiguity_notes.
- Prefer "requires_confirmation": true unless the value is directly implied.

Output shape:
{
  "candidate_params": {
    "orbit_type": {
      "found": false,
      "value": null,
      "unit": null,
      "confidence": 0.0,
      "assumptions": [],
      "requires_confirmation": true
    }
  },
  "ambiguity_notes": [],
  "missing_params": []
}
"""


def extract_mission_context(user_text: str, llm_parsed_json: dict | None = None) -> dict:
    """Extract high-level mission intent without treating it as tool output."""

    llm_intent = (llm_parsed_json or {}).get("mission_intent") or {}
    objective = llm_intent.get("mission_objective") or _infer_objective_rules(user_text)
    target_region = llm_intent.get("target_region") or _infer_target_region_rules(user_text)
    performance = list(llm_intent.get("performance_requirements") or [])
    performance.extend(_infer_performance_requirements_rules(user_text))

    ambiguity_notes = list(llm_intent.get("ambiguity_notes") or [])
    if objective and not any("objective" in str(item).lower() for item in ambiguity_notes):
        ambiguity_notes.append(
            "Mission objective is interpreted at concept level and should be confirmed."
        )

    return {
        "mission_objective": objective,
        "target_region": target_region,
        "performance_requirements": _dedupe_dicts(performance),
        "missing_params": list(llm_intent.get("missing_params") or []),
        "ambiguity_notes": ambiguity_notes,
    }


def infer_missing_parameters(
    params: dict,
    mission_context: dict | None = None,
    user_text: str = "",
) -> Tuple[dict, Dict[str, Any]]:
    """Infer cautious candidates for missing parameters.

    Existing found values are never overwritten.
    """

    mission_context = mission_context or extract_mission_context(user_text)
    metadata: Dict[str, Any] = {
        "mode": "none",
        "llm_status": "disabled_no_api_key",
        "inferred_parameters": [],
        "rules_inferred_parameters": [],
        "assumptions": [],
        "ambiguity_notes": list(mission_context.get("ambiguity_notes", [])),
        "raw_llm_response": None,
        "parsed_llm_json": None,
    }

    candidates = {}
    if os.environ.get("LLM_API_KEY"):
        llm_candidates, llm_metadata = _infer_with_llm(params, mission_context, user_text)
        metadata.update(llm_metadata)
        candidates.update(llm_candidates)

    rules_candidates = _infer_with_rules(params, mission_context, user_text)
    for key, candidate in rules_candidates.items():
        candidates.setdefault(key, candidate)

    for key, candidate in candidates.items():
        if key not in INFERABLE_PARAM_UNITS:
            continue
        existing = params.get(key, {})
        if existing.get("found") and existing.get("value") is not None:
            continue
        if not candidate.get("found") or candidate.get("value") is None:
            continue

        params[key] = {
            "value": candidate.get("value"),
            "unit": candidate.get("unit", INFERABLE_PARAM_UNITS[key]),
            "found": True,
            "source": candidate.get("source", "llm_inferred"),
            "status": "inferred",
            "confidence": float(candidate.get("confidence", 0.5)),
            "assumptions": list(candidate.get("assumptions", [])),
            "requires_confirmation": bool(candidate.get("requires_confirmation", True)),
        }
        if params[key]["source"] == "llm_inferred":
            metadata["inferred_parameters"].append(key)
        else:
            metadata["rules_inferred_parameters"].append(key)
        metadata["assumptions"].extend(params[key]["assumptions"])

    if metadata["inferred_parameters"]:
        metadata["mode"] = "llm_inference"
    elif metadata["rules_inferred_parameters"]:
        metadata["mode"] = "rules_inference"

    params["_mission_context"] = mission_context
    params["_inference_metadata"] = metadata
    return params, metadata


def _infer_with_llm(params: dict, mission_context: dict, user_text: str) -> tuple[dict, dict]:
    metadata = {
        "llm_status": "enabled",
        "raw_llm_response": None,
        "parsed_llm_json": None,
    }
    client = OpenAI(
        api_key=os.environ["LLM_API_KEY"],
        base_url=os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL),
    )
    prompt = {
        "user_text": user_text,
        "mission_context": mission_context,
        "current_params": _safe_param_summary(params),
        "missing_keys": [
            key for key in INFERABLE_PARAM_UNITS
            if not params.get(key, {}).get("found")
        ],
    }
    try:
        response = client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", DEFAULT_MODEL),
            messages=[
                {"role": "system", "content": INFERENCE_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            temperature=0.2,
            max_tokens=1200,
            timeout=int(os.environ.get("LLM_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))),
        )
        raw = response.choices[0].message.content or ""
        parsed = _parse_json_object(raw)
        metadata["raw_llm_response"] = raw
        metadata["parsed_llm_json"] = parsed
    except Exception as exc:
        metadata["llm_status"] = f"failed: {exc}"
        return {}, metadata

    candidates = {}
    for key, candidate in (metadata["parsed_llm_json"].get("candidate_params") or {}).items():
        if not isinstance(candidate, dict):
            continue
        candidates[key] = {
            "found": bool(candidate.get("found") and candidate.get("value") is not None),
            "value": candidate.get("value"),
            "unit": candidate.get("unit", INFERABLE_PARAM_UNITS.get(key)),
            "confidence": candidate.get("confidence", 0.5),
            "assumptions": candidate.get("assumptions", []),
            "requires_confirmation": candidate.get("requires_confirmation", True),
            "source": "llm_inferred",
        }
    return candidates, metadata


def _infer_with_rules(params: dict, mission_context: dict, user_text: str) -> dict:
    candidates = {}
    objective = str(mission_context.get("mission_objective") or "").lower()
    text_lower = user_text.lower()
    is_earth_observation = (
        "remote_sensing" in objective
        or "monitoring" in objective
        or any(term in text_lower for term in ["遥感", "监测", "观测", "成像", "remote sensing", "monitor"])
    )
    if is_earth_observation and not params.get("orbit_type", {}).get("found"):
        candidates["orbit_type"] = {
            "found": True,
            "value": "SSO",
            "unit": None,
            "confidence": 0.45,
            "assumptions": [
                "Earth-observation monitoring missions commonly start from an SSO/LEO trade study.",
                "This is a rules fallback candidate and must be confirmed by the user.",
            ],
            "requires_confirmation": True,
            "source": "rules_inferred",
        }
    return candidates


def _infer_objective_rules(text: str) -> str | None:
    text_lower = text.lower()
    if any(term in text_lower for term in ["遥感", "监测", "观测", "成像", "remote sensing", "monitor"]):
        return "remote_sensing_monitoring"
    if any(term in text_lower for term in ["通信", "链路", "communication", "comms"]):
        return "communications"
    return None


def _infer_target_region_rules(text: str) -> str | None:
    patterns = [
        r"(?:监测|观测|覆盖|查看)\s*([^，,。；;]+?)(?:地区|区域|海域|沿海地区)",
        r"(?:重访|访问)(?:一次)?\s*([^，,。；;]+?)(?:的)?(?:遥感|观测|监测)",
        r"设计(?:一颗|一个)?[^，,。；;]*?([^，,。；;]+?)(?:的)?(?:遥感|观测|监测)(?:卫星|任务)",
        r"(?:target|monitor|observe)\s+([^,.；;]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _infer_performance_requirements_rules(text: str) -> list[dict[str, Any]]:
    requirements = []
    revisit = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(小时|h|hr|hour|hours)\s*(?:内)?\s*(?:重访|访问)(?:一次)?",
        text,
        re.IGNORECASE,
    )
    if revisit:
        value = float(revisit.group(1).replace(",", "."))
        requirements.append({
            "name": "revisit_time",
            "value": value,
            "unit": "hours",
            "source": "user_provided",
            "raw_text": revisit.group(0),
        })
    return requirements


def _safe_param_summary(params: dict) -> dict:
    return {
        key: {
            "value": entry.get("value"),
            "unit": entry.get("unit"),
            "source": entry.get("source"),
            "found": entry.get("found"),
        }
        for key, entry in params.items()
        if not key.startswith("_") and isinstance(entry, dict)
    }


def _parse_json_object(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1:].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


def _dedupe_dicts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for item in items:
        marker = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if marker not in seen:
            seen.add(marker)
            result.append(item)
    return result
