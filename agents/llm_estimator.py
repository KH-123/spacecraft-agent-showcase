"""
LLM concept-level estimation fallback for spacecraft conceptual design.

Provides structured concept-level estimates only when deterministic tools
do not support the requested analysis. Does not replace existing tools.

All outputs are marked with source="llm_estimated" and include assumptions,
uncertainty notes, confidence, and requires_confirmation.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (reuses the same env vars as llm_extractor.py)
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT_SECONDS = 30

# ---------------------------------------------------------------------------
# Estimation system prompt
# ---------------------------------------------------------------------------

ESTIMATION_SYSTEM_PROMPT = """You are a spacecraft conceptual design assistant.

Your task is to provide a concept-level estimate for an analysis request that
is NOT supported by the available deterministic engineering tools.

Rules:
- This is a CONCEPT-LEVEL estimate only. Do NOT claim high precision.
- Do NOT fabricate precise numerical values unless the user provided them.
- If information is insufficient, list what parameters are needed rather than guessing.
- Output ONLY valid JSON. No Markdown, no code fences, no explanation.
- Always include assumptions, uncertainty notes, confidence, and requires_confirmation.

Available deterministic tools:
- orbit_period(altitude_km): circular orbit period and velocity
- mass_budget(payload_mass_kg, orbit_type): mass budget estimation
- solar_array_area(power_required_w): solar panel sizing
- battery_capacity(power_required_w, eclipse_hours): battery sizing

Output exactly this JSON shape:
{
  "task_id": "string",
  "status": "completed",
  "source": "llm_estimated",
  "result": {
    "value": "string or number or null",
    "unit": "string or null",
    "confidence": 0.0,
    "assumptions": ["string"],
    "uncertainty_notes": ["string"],
    "requires_confirmation": true
  }
}
"""


# ---------------------------------------------------------------------------
# Estimation function
# ---------------------------------------------------------------------------


def estimate_conceptually(
    request: Dict[str, Any],
    params: dict,
    available_tools: List[str],
) -> Dict[str, Any]:
    """Provide a concept-level estimate for an unsupported analysis request.

    Parameters
    ----------
    request : dict
        The analysis request. Expected keys:
        - ``task_id``: unique identifier for the request.
        - ``name``: human-readable name.
        - ``description``: description of what is being requested.
    params : dict
        Current mission parameters (for context).
    available_tools : list of str
        List of available deterministic tool names.

    Returns
    -------
    dict
        Estimation result with keys:
        - ``task_id``: same as request.
        - ``name``: same as request.
        - ``status``: "completed" or "failed".
        - ``source``: "llm_estimated".
        - ``result``: dict with value, unit, confidence, assumptions,
          uncertainty_notes, requires_confirmation.
    """
    task_id = request.get("task_id", "unknown")
    task_name = request.get("name", "Unknown")
    task_description = request.get("description", "")

    # Build context for the LLM
    param_summary = _summarize_params(params)
    tools_str = ", ".join(available_tools) if available_tools else "none"

    user_prompt = (
        f"Analysis request: {task_name}\n"
        f"Description: {task_description}\n\n"
        f"Available tools: {tools_str}\n\n"
        f"Current mission parameters:\n{param_summary}\n\n"
        f"Please provide a concept-level estimate for this request. "
        f"If insufficient information is available, state what is needed."
    )

    try:
        client = _get_client()
        if client is None:
            return _fallback_estimate(task_id, task_name, "LLM API not configured")

        model = os.environ.get("LLM_MODEL", DEFAULT_MODEL)
        timeout = int(os.environ.get("LLM_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": ESTIMATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
            timeout=timeout,
        )

        raw_content = response.choices[0].message.content
        if raw_content is None:
            return _fallback_estimate(
                task_id, task_name, "LLM returned empty content"
            )

        parsed = _parse_estimation_json(raw_content)
        parsed["task_id"] = task_id
        parsed["name"] = task_name
        return parsed

    except Exception as exc:
        logger.warning("LLM estimation failed: %s", exc)
        return _fallback_estimate(task_id, task_name, str(exc))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_client() -> Optional[OpenAI]:
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        return None
    return OpenAI(
        api_key=api_key,
        base_url=os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL),
    )


def _summarize_params(params: dict) -> str:
    """Build a concise parameter summary for the LLM prompt."""
    lines = []
    for key, entry in params.items():
        if key.startswith("_"):
            continue
        if isinstance(entry, dict) and entry.get("found"):
            val = entry.get("value")
            unit = entry.get("unit") or ""
            source = entry.get("source", "unknown")
            lines.append(f"  - {key}: {val} {unit} (source: {source})")
    return "\n".join(lines) if lines else "  (no parameters provided)"


def _parse_estimation_json(raw_content: str) -> dict:
    """Parse LLM JSON output, tolerating code fences."""
    cleaned = raw_content.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1:].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object
        start = cleaned.find("{")
        if start != -1:
            end = cleaned.rfind("}")
            if end != -1 and end > start:
                try:
                    data = json.loads(cleaned[start:end + 1])
                except json.JSONDecodeError:
                    return _fallback_estimate("unknown", "Parse Error", "Invalid JSON")
            else:
                return _fallback_estimate("unknown", "Parse Error", "No JSON object")
        else:
            return _fallback_estimate("unknown", "Parse Error", "No JSON object")

    # Ensure required fields
    if "result" not in data:
        data["result"] = {
            "value": None,
            "unit": None,
            "confidence": 0.0,
            "assumptions": ["LLM output did not contain structured result"],
            "uncertainty_notes": [],
            "requires_confirmation": True,
        }

    result = data.get("result", {})
    result.setdefault("assumptions", [])
    result.setdefault("uncertainty_notes", [])
    result.setdefault("requires_confirmation", True)
    result.setdefault("confidence", 0.0)
    data["source"] = "llm_estimated"
    data["status"] = "completed"

    return data


def _fallback_estimate(
    task_id: str, task_name: str, reason: str
) -> Dict[str, Any]:
    """Return a safe fallback when LLM estimation is unavailable."""
    return {
        "task_id": task_id,
        "name": task_name,
        "status": "completed",
        "source": "llm_estimated",
        "result": {
            "value": None,
            "unit": None,
            "confidence": 0.0,
            "assumptions": [
                f"LLM estimation was not available: {reason}",
                "No deterministic tool supports this analysis.",
            ],
            "uncertainty_notes": [
                "This is a placeholder because LLM estimation could not be performed.",
                "Please implement a deterministic tool or provide an API key for LLM estimation.",
            ],
            "requires_confirmation": True,
        },
    }
