"""
Explicit mission context extraction for spacecraft conceptual design.

This module extracts only what the user explicitly stated — no engineering
inference, no auto-completion, no participation in core orbit gate.

The extracted context is used for:
- UI display of "what the system understood"
- missing-parameter hints
- RAG advisor input

It does NOT:
- overwrite normalized parameters
- participate in core orbit gate
- perform engineering inference
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


MISSION_CONTEXT_FIELDS = [
    "mission_type",
    "target_region",
    "revisit_time_h",
    "payload_type",
    "ground_resolution_m",
    "swath_width_km",
    "imaging_frequency",
    "daily_data_volume_GB",
    "downlink_rate_Mbps",
    "mission_lifetime_year",
    "pointing_accuracy_deg",
]


def _empty_context() -> Dict[str, Any]:
    return {field: None for field in MISSION_CONTEXT_FIELDS}


def _extract_from_llm_json(llm_parsed_json: Optional[dict]) -> Dict[str, Any]:
    """Extract mission context from LLM parsed JSON (mission_intent block)."""
    if not llm_parsed_json:
        return {}

    intent = llm_parsed_json.get("mission_intent") or {}
    result: Dict[str, Any] = {}

    # Map LLM mission_intent fields to our context fields
    field_map = {
        "mission_type": "mission_type",
        "target_region": "target_region",
        "revisit_time_h": "revisit_time_h",
        "payload_type": "payload_type",
        "ground_resolution_m": "ground_resolution_m",
        "swath_width_km": "swath_width_km",
        "imaging_frequency": "imaging_frequency",
        "daily_data_volume_GB": "daily_data_volume_GB",
        "downlink_rate_Mbps": "downlink_rate_Mbps",
        "mission_lifetime_year": "mission_lifetime_year",
        "pointing_accuracy_deg": "pointing_accuracy_deg",
    }

    for llm_key, ctx_key in field_map.items():
        value = intent.get(llm_key)
        if value is not None:
            result[ctx_key] = value

    return result


def _parse_number(value: str) -> float:
    return float(value.replace(",", "."))


def _extract_revisit_time_hours(text: str) -> float | None:
    """Extract explicit revisit/access-cycle requirements expressed in hours."""

    hour_unit = r"(?:小时|h|hr|hrs|hour|hours)"
    value = r"(?P<value>\d+(?:[.,]\d+)?)"
    assignment = r"(?:改为|调整为|设为|设置为|改成|为|是|=|:|：)?"
    patterns = [
        rf"(?:重访时间|重访周期|访问周期|访问间隔|重访间隔|"
        rf"revisit\s*(?:time|cycle|period|interval)?|"
        rf"access\s*(?:cycle|period|interval)|visit\s*(?:cycle|period|interval))"
        rf"\s*{assignment}\s*{value}\s*{hour_unit}",
        rf"每\s*{value}\s*{hour_unit}\s*(?:访问|重访|观测|覆盖)(?:一次)?",
        rf"{value}\s*{hour_unit}\s*(?:内)?\s*(?:重访|访问|观测|覆盖)(?:一次)?",
        rf"(?:revisits?|visits?|access(?:es)?|observes?)\s+every\s+{value}\s*{hour_unit}",
        rf"every\s+{value}\s*{hour_unit}\s*(?:revisits?|visits?|access(?:es)?|observations?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _parse_number(match.group("value"))
    return None


def _extract_from_user_text(text: str) -> Dict[str, Any]:
    """Extract mission context from raw user text using simple patterns.

    Only extracts what is explicitly stated. No inference.
    """
    result: Dict[str, Any] = {}
    text_lower = text.lower()

    # Common Chinese incremental-update forms. These are explicit context
    # fields only; they do not feed the core orbit gate or tool execution.
    if re.search(r"遥感|光学遥感|remote sensing|earth observation", text_lower):
        result["mission_type"] = "remote_sensing"
    if re.search(r"光学|optical", text_lower):
        result["payload_type"] = "optical"

    target_match = re.search(
        r"(?:目标区域|目标|target region)\s*(?:改为|调整为|设为|设置为|改成|为|是|=|:|：)?\s*([^，。；;,\n]+)",
        text,
        re.IGNORECASE,
    )
    if target_match:
        result["target_region"] = target_match.group(1).strip()

    revisit_time_h = _extract_revisit_time_hours(text)
    if revisit_time_h is not None:
        result["revisit_time_h"] = revisit_time_h

    resolution_match = re.search(
        r"(?:地面分辨率|分辨率|ground\s+resolution|resolution)\s*(?:改为|调整为|设为|设置为|改成|为|是|=|:|：)?\s*(\d+(?:[.,]\d+)?)\s*(m|meter|meters|metre|metres|米)",
        text,
        re.IGNORECASE,
    )
    if resolution_match:
        result["ground_resolution_m"] = float(resolution_match.group(1).replace(",", "."))

    # --- mission_type ---
    mission_patterns = [
        (r"遥感|remote sensing|earth observation|观测|监测", "remote_sensing"),
        (r"通信|communication|comms|链路", "communications"),
        (r"导航|navigation|定位|positioning", "navigation"),
        (r"科学|science|scientific|探测", "science"),
        (r"侦察|reconnaissance|spy|军事", "reconnaissance"),
    ]
    for pattern, mtype in mission_patterns:
        if "mission_type" not in result and re.search(pattern, text_lower):
            result["mission_type"] = mtype
            break

    # --- target_region ---
    region_patterns = [
        r"(?:目标区域|目标|target region)\s*(?:是|为|=|:|：)?\s*([^，,。；;]+)",
        r"(?:监测|观测|覆盖|查看|重访|访问)\s*(?:一次)?\s*([^，,。；;]+?)(?:地区|区域|海域|沿海|的遥感|的观测|的监测)",
        r"(?:target|monitor|observe)\s+([^,.；;]+)",
        r"设计(?:一颗|一个)?[^，,。；;]*?([^，,。；;]+?)(?:的)?(?:遥感|观测|监测)(?:卫星|任务)",
    ]
    if "target_region" not in result:
        for pattern in region_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["target_region"] = match.group(1).strip()
                break

    # --- revisit_time_h ---
    revisit_time_h = _extract_revisit_time_hours(text)
    if revisit_time_h is not None and "revisit_time_h" not in result:
        result["revisit_time_h"] = revisit_time_h

    # --- payload_type ---
    payload_patterns = [
        (r"光学|可见光|多光谱|高光谱|光学遥感|optical|multispectral|hyperspectral", "optical"),
        (r"合成孔径雷达|sar|雷达|radar", "SAR"),
        (r"红外|thermal infrared|热红外", "infrared"),
        (r"通信|通信载荷|comms|communication payload", "communication"),
        (r"导航|导航载荷|navigation payload", "navigation"),
    ]
    for pattern, ptype in payload_patterns:
        if "payload_type" not in result and re.search(pattern, text_lower):
            result["payload_type"] = ptype
            break

    # --- ground_resolution_m ---
    res_match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(m|meter|meters|metre|metres|米)\s*(?:分辨率|resolution)",
        text,
        re.IGNORECASE,
    )
    if res_match and "ground_resolution_m" not in result:
        result["ground_resolution_m"] = float(res_match.group(1).replace(",", "."))

    # --- swath_width_km ---
    swath_match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(km|kilometer|kilometers|公里|千米)\s*(?:幅宽|swath|幅宽)",
        text,
        re.IGNORECASE,
    )
    if swath_match:
        result["swath_width_km"] = float(swath_match.group(1).replace(",", "."))

    # --- daily_data_volume_GB ---
    data_match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(gb|gigabyte|gigabytes|tb|terabyte|terabytes)\s*(?:数据|data|日数据量)",
        text,
        re.IGNORECASE,
    )
    if data_match:
        val = float(data_match.group(1).replace(",", "."))
        unit = data_match.group(2).lower()
        if unit in ("tb", "terabyte", "terabytes"):
            val *= 1024.0
        result["daily_data_volume_GB"] = val

    # --- downlink_rate_Mbps ---
    downlink_match = re.search(
        r"(?:下行速率|数传速率|downlink rate|downlink)\s*(?:=|:|：|为|是)?\s*"
        r"(\d+(?:[.,]\d+)?)\s*(mbps|mps|兆比特每秒|兆每秒)",
        text,
        re.IGNORECASE,
    ) or re.search(
        r"(\d+(?:[.,]\d+)?)\s*(mbps|mps|兆比特每秒|兆每秒)\s*(?:下行|数传|downlink)",
        text,
        re.IGNORECASE,
    )
    if downlink_match:
        result["downlink_rate_Mbps"] = float(downlink_match.group(1).replace(",", "."))

    # --- pointing_accuracy_deg ---
    pointing_match = re.search(
        r"(?:指向精度|pointing accuracy)\s*(?:=|:|：|为|是)?\s*"
        r"(\d+(?:[.,]\d+)?)\s*(deg|degree|degrees|°|度)",
        text,
        re.IGNORECASE,
    )
    if pointing_match:
        result["pointing_accuracy_deg"] = float(pointing_match.group(1).replace(",", "."))

    # --- mission_lifetime_year ---
    life_match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(年|year|years|yr|yrs)\s*(?:寿命|lifetime|任务寿命)",
        text,
        re.IGNORECASE,
    )
    if life_match:
        result["mission_lifetime_year"] = float(life_match.group(1).replace(",", "."))

    return result


def extract_mission_context(
    user_text: str,
    llm_parsed_json: Optional[dict] = None,
) -> Dict[str, Any]:
    """Extract explicitly stated mission context from user input.

    Parameters
    ----------
    user_text : str
        Raw user input text.
    llm_parsed_json : dict or None
        Parsed LLM JSON output (from llm_extractor), which may contain
        a ``mission_intent`` block with explicit context fields.

    Returns
    -------
    dict
        Mission context with the following keys (all may be ``None``)::

            {
                "mission_type": None,
                "target_region": None,
                "revisit_time_h": None,
                "payload_type": None,
                "ground_resolution_m": None,
                "swath_width_km": None,
                "imaging_frequency": None,
                "daily_data_volume_GB": None,
                "downlink_rate_Mbps": None,
                "mission_lifetime_year": None,
                "pointing_accuracy_deg": None,
            }

    Notes
    -----
    - LLM-extracted context takes priority over rules-extracted context.
    - No engineering inference is performed.
    - No auto-completion of missing fields.
    - This context does NOT participate in core orbit gate.
    """
    ctx = _empty_context()

    # 1. Try LLM-extracted context first
    llm_ctx = _extract_from_llm_json(llm_parsed_json)
    ctx.update(llm_ctx)

    # 2. Fill gaps with rules-extracted context (only where LLM returned None)
    rules_ctx = _extract_from_user_text(user_text)
    for key, value in rules_ctx.items():
        if ctx.get(key) is None and value is not None:
            ctx[key] = value

    return ctx


def build_mission_context_display_rows(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build display rows for the mission context table in the UI.

    Returns a list of dicts suitable for ``st.dataframe()``::

        [
            {
                "字段": "mission_type",
                "中文名": "任务类型",
                "值": "remote_sensing",
                "状态": "已识别",
            },
            ...
        ]
    """
    FIELD_LABELS = {
        "mission_type": ("任务类型", "mission_type"),
        "target_region": ("目标区域", "target_region"),
        "revisit_time_h": ("重访时间", "revisit_time_h"),
        "payload_type": ("载荷类型", "payload_type"),
        "ground_resolution_m": ("地面分辨率", "ground_resolution_m"),
        "swath_width_km": ("幅宽", "swath_width_km"),
        "imaging_frequency": ("成像频率", "imaging_frequency"),
        "daily_data_volume_GB": ("日数据量", "daily_data_volume_GB"),
        "downlink_rate_Mbps": ("下行速率", "downlink_rate_Mbps"),
        "mission_lifetime_year": ("任务寿命", "mission_lifetime_year"),
        "pointing_accuracy_deg": ("指向精度", "pointing_accuracy_deg"),
    }

    rows = []
    for field in MISSION_CONTEXT_FIELDS:
        cn_label, en_label = FIELD_LABELS.get(field, (field, field))
        value = context.get(field)
        if value is not None:
            display_value = str(value)
            status = "已识别"
        else:
            display_value = "未提供"
            status = "待补充"
        rows.append({
            "字段": en_label,
            "中文名": cn_label,
            "值": display_value,
            "状态": status,
        })
    return rows
