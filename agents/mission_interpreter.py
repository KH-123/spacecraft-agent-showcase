"""Mission-level request interpretation for conceptual spacecraft design.

This module is separate from ``llm_extractor.py``. It handles beginner-facing
mission intent and missing design drivers, not parameter-level extraction.
"""

from __future__ import annotations

import re
from typing import Any


MISSION_DRIVER_LABELS = {
    "target_region": "目标区域",
    "revisit_requirement_hours": "重访/访问间隔",
    "spatial_resolution_m": "空间分辨率",
    "swath_width_km": "幅宽",
    "sensor_type": "传感器类型",
    "single_satellite_or_constellation": "单星/星座约束",
    "off_nadir_pointing_allowed": "是否允许侧摆成像",
    "mission_lifetime_years": "任务寿命",
    "preferred_orbit_type": "偏好的轨道类型",
}

MISSION_DRIVER_GUIDANCE = {
    "target_region": "请给出明确地理区域、国家、城市群、海岸线或经纬度范围。",
    "revisit_requirement_hours": "请给出期望多久至少观测一次，例如 6 小时、12 小时或每天 2 次。",
    "spatial_resolution_m": "请给出地面分辨率目标，例如 1 m、5 m、10 m 或 30 m。",
    "swath_width_km": "请给出单次成像幅宽或覆盖宽度，例如 20 km、100 km。",
    "sensor_type": "请确认载荷类型，例如光学、多光谱、高光谱、SAR 或热红外。",
    "single_satellite_or_constellation": "请确认是否必须单星，或允许多星星座满足重访。",
    "off_nadir_pointing_allowed": "请确认是否允许侧摆成像以及最大侧摆角。",
    "mission_lifetime_years": "请给出任务寿命目标，例如 1 年、3 年或 5 年。",
    "preferred_orbit_type": "请确认是否偏好 SSO、极轨、倾斜 LEO 或其他轨道。",
}

_PARAMETER_HINT_PATTERNS = [
    r"\bLEO\b|\bSSO\b|\bGEO\b|\bMEO\b",
    r"\d+(?:[.,]\d+)?\s*(?:km|公里|千米)",
    r"\d+(?:[.,]\d+)?\s*(?:kg|千克|公斤|g|克|t|吨)\b",
    r"\d+(?:[.,]\d+)?\s*(?:w|kw|瓦|千瓦)\b",
    r"(?:倾角|轨道倾角|inclination)\s*\d+(?:[.,]\d+)?",
]

_MISSION_HINT_PATTERNS = [
    r"遥感|观测|监测|覆盖|成像|重访|访问|查看|看",
    r"remote\s*sensing|monitor|observe|coverage|revisit",
    r"农业|农田|海岸线|灾害|洪水|火灾|森林|城市|海洋",
]

_VAGUE_TARGET_TERMS = {
    "某个",
    "某些",
    "某一",
    "一个",
    "目标区域",
    "指定区域",
    "农业区域",
    "区域",
    "地区",
}


def interpret_mission_request(user_text: str) -> dict[str, Any]:
    """Interpret a non-expert mission-level request."""

    text = (user_text or "").strip()
    sensor_type = _extract_sensor_type(text)
    interpretation = {
        "input_type": _detect_input_type(text),
        "mission_objective": _infer_mission_objective(text),
        "target_region": _extract_target_region(text),
        "revisit_requirement_hours": _extract_revisit_hours(text),
        "payload_type_hint": _infer_payload_type_hint(text, sensor_type),
        "sensor_type": sensor_type,
        "spatial_resolution_m": _extract_spatial_resolution_m(text),
        "swath_width_km": _extract_swath_width_km(text),
        "single_satellite_or_constellation": _extract_architecture_preference(text),
        "off_nadir_pointing_allowed": _extract_off_nadir_preference(text),
        "mission_lifetime_years": _extract_lifetime_years(text),
        "preferred_orbit_type": _extract_preferred_orbit_type(text),
        "performance_requirements": [],
        "missing_design_drivers": [],
        "ambiguity_notes": [],
    }
    interpretation["performance_requirements"] = _build_performance_requirements(interpretation)
    interpretation["missing_design_drivers"] = _identify_missing_design_drivers(interpretation)
    interpretation["ambiguity_notes"] = _build_ambiguity_notes(interpretation)
    return interpretation


def build_constraint_rows(interpretation: dict[str, Any]) -> list[dict[str, Any]]:
    """Build UI-friendly rows for known and missing mission drivers."""

    rows: list[dict[str, Any]] = []
    for key, label in MISSION_DRIVER_LABELS.items():
        value = interpretation.get(key)
        known = value not in (None, "", [])
        rows.append(
            {
                "约束项": label,
                "字段": key,
                "当前识别": _format_value(value) if known else "未提供",
                "状态": "已识别" if known else "待补充",
                "补充建议": MISSION_DRIVER_GUIDANCE[key],
            }
        )
    return rows


def _detect_input_type(text: str) -> str:
    has_parameter_hint = any(
        re.search(pattern, text, re.IGNORECASE) for pattern in _PARAMETER_HINT_PATTERNS
    )
    has_mission_hint = any(
        re.search(pattern, text, re.IGNORECASE) for pattern in _MISSION_HINT_PATTERNS
    )
    if has_parameter_hint and has_mission_hint:
        return "mixed_request"
    if has_parameter_hint:
        return "parameter_level_request"
    return "mission_level_request"


def _infer_mission_objective(text: str) -> str | None:
    lower = text.lower()
    if re.search(r"农业|农田|作物|农作物|agriculture|crop", lower):
        return "agriculture_monitoring"
    if re.search(r"海岸线|沿海|近海|coast|coastline", lower):
        return "coastline_monitoring"
    if re.search(r"灾害|洪水|火灾|地震|滑坡|disaster|flood|fire", lower):
        return "disaster_monitoring"
    if re.search(r"遥感|成像|remote\s*sensing|imaging", lower):
        return "regional_remote_sensing"
    if re.search(r"监测|观测|覆盖|查看|看|monitor|observe|coverage", lower):
        return "regional_monitoring"
    if re.search(r"通信|communication|comms|link", lower):
        return "communications"
    return None


def _extract_target_region(text: str) -> str | None:
    cleaned = _remove_revisit_phrases(text)
    patterns = [
        r"(?:监测|观测|覆盖|查看|看)\s*([^，。；;,.]+)",
        r"(?:访问|重访)\s*(?:一次|一遍|两次|二次|多次)?\s*([^，。；;,.]+?)(?:的)?(?:遥感|观测|监测)?(?:卫星|任务|$)",
        r"(?:设计|规划|做|需要).*?(?:一颗|一个)?\s*([^，。；;,.]+?)(?:的)?(?:遥感|观测|监测)(?:卫星|任务)",
        r"(?:over|in|for|observe|monitor)\s+([A-Za-z][A-Za-z\s\-']+?)(?:\s+with|\s+every|[,.]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if not match:
            continue
        candidate = _clean_target_candidate(match.group(1))
        if candidate and not _is_vague_target(candidate):
            return candidate
    return None


def _extract_revisit_hours(text: str) -> float | None:
    patterns = [
        r"(?:每|每隔)?\s*(\d+(?:[.,]\d+)?)\s*(?:小时|h|hr|hour|hours)\s*(?:内|一次|一遍)?\s*(?:重访|访问|观测|覆盖|看)?",
        r"(?:重访|访问|观测|覆盖|看)\s*(?:周期|间隔)?\s*(?:为|=|:|：)?\s*(\d+(?:[.,]\d+)?)\s*(?:小时|h|hr|hour|hours)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return round(float(match.group(1).replace(",", ".")), 2)

    daily = re.search(
        r"(?:每天|每日|一天|24\s*小时)\s*(?:内)?\s*(?:看|访问|重访|观测|覆盖)?\s*([一二两三四五六七八九十\d]+)\s*次",
        text,
        re.IGNORECASE,
    )
    if daily:
        count = _number_from_text(daily.group(1))
        if count and count > 0:
            return round(24.0 / count, 2)

    per_day = re.search(
        r"([一二两三四五六七八九十\d]+)\s*次\s*/?\s*(?:天|日|day)",
        text,
        re.IGNORECASE,
    )
    if per_day:
        count = _number_from_text(per_day.group(1))
        if count and count > 0:
            return round(24.0 / count, 2)
    return None


def _extract_sensor_type(text: str) -> str | None:
    sensor_patterns = [
        (r"\bSAR\b|合成孔径雷达|雷达", "SAR"),
        (r"高光谱|hyperspectral", "hyperspectral"),
        (r"多光谱|multispectral", "multispectral"),
        (r"热红外|红外|thermal|infrared", "thermal_infrared"),
        (r"光学|可见光|optical", "optical"),
    ]
    for pattern, value in sensor_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return value
    return None


def _infer_payload_type_hint(text: str, sensor_type: str | None) -> str | None:
    if sensor_type:
        return sensor_type
    objective = _infer_mission_objective(text)
    if objective == "agriculture_monitoring":
        return "multispectral_or_optical_remote_sensing"
    if objective == "coastline_monitoring":
        return "optical_or_sar_remote_sensing"
    if objective == "disaster_monitoring":
        return "optical_sar_or_thermal_remote_sensing"
    if objective in {"regional_remote_sensing", "regional_monitoring"}:
        return "remote_sensing_payload_to_be_confirmed"
    return None


def _extract_spatial_resolution_m(text: str) -> float | None:
    patterns = [
        r"(?:分辨率|空间分辨率|resolution)\s*(?:为|=|:|：)?\s*(\d+(?:[.,]\d+)?)\s*(?:m|米|meter|meters)",
        r"(\d+(?:[.,]\d+)?)\s*(?:m|米|meter|meters)\s*(?:级)?\s*(?:分辨率|空间分辨率|resolution)",
    ]
    return _extract_first_float(text, patterns)


def _extract_swath_width_km(text: str) -> float | None:
    patterns = [
        r"(?:幅宽|成像宽度|覆盖宽度|swath)\s*(?:为|=|:|：)?\s*(\d+(?:[.,]\d+)?)\s*(?:km|公里|千米)",
        r"(\d+(?:[.,]\d+)?)\s*(?:km|公里|千米)\s*(?:幅宽|成像宽度|覆盖宽度|swath)",
    ]
    return _extract_first_float(text, patterns)


def _extract_lifetime_years(text: str) -> float | None:
    patterns = [
        r"(?:寿命|任务寿命|lifetime)\s*(?:为|=|:|：)?\s*(\d+(?:[.,]\d+)?)\s*(?:年|years|year|yr|yrs)",
        r"(\d+(?:[.,]\d+)?)\s*(?:年|years|year|yr|yrs)\s*(?:寿命|任务寿命|lifetime)",
    ]
    return _extract_first_float(text, patterns)


def _extract_preferred_orbit_type(text: str) -> str | None:
    if re.search(r"太阳同步|SSO|sun[-\s]?synchronous", text, re.IGNORECASE):
        return "SSO"
    if re.search(r"极轨|极地|polar", text, re.IGNORECASE):
        return "polar orbit"
    if re.search(r"低轨|近地|LEO|low earth orbit", text, re.IGNORECASE):
        return "LEO"
    if re.search(r"地球同步|地球静止|GEO|geostationary|geosynchronous", text, re.IGNORECASE):
        return "GEO"
    return None


def _extract_architecture_preference(text: str) -> str | None:
    if re.search(r"星座|多星|多颗|constellation|multiple satellites", text, re.IGNORECASE):
        return "constellation_allowed_or_requested"
    if re.search(r"单星|一颗|1颗|single satellite", text, re.IGNORECASE):
        return "single_satellite_preferred"
    return None


def _extract_off_nadir_preference(text: str) -> str | None:
    if re.search(r"不允许侧摆|不侧摆|no off[-\s]?nadir", text, re.IGNORECASE):
        return "not_allowed"
    if re.search(r"侧摆|斜视|off[-\s]?nadir|pointing", text, re.IGNORECASE):
        return "allowed_or_to_be_sized"
    return None


def _build_performance_requirements(interpretation: dict[str, Any]) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    if interpretation.get("revisit_requirement_hours") is not None:
        requirements.append(
            {
                "name": "revisit_time",
                "value": interpretation["revisit_requirement_hours"],
                "unit": "hours",
                "source": "mission_level_interpreted",
                "verification_status": "not_verified",
            }
        )
    if interpretation.get("spatial_resolution_m") is not None:
        requirements.append(
            {
                "name": "spatial_resolution",
                "value": interpretation["spatial_resolution_m"],
                "unit": "m",
                "source": "mission_level_interpreted",
                "verification_status": "not_verified",
            }
        )
    if interpretation.get("swath_width_km") is not None:
        requirements.append(
            {
                "name": "swath_width",
                "value": interpretation["swath_width_km"],
                "unit": "km",
                "source": "mission_level_interpreted",
                "verification_status": "requires_external_simulation",
            }
        )
    return requirements


def _identify_missing_design_drivers(interpretation: dict[str, Any]) -> list[str]:
    return [
        key for key in MISSION_DRIVER_LABELS
        if interpretation.get(key) in (None, "", [])
    ]


def _build_ambiguity_notes(interpretation: dict[str, Any]) -> list[str]:
    notes = [
        "Mission-level interpretation is conceptual and must be confirmed before engineering analysis."
    ]
    if interpretation.get("revisit_requirement_hours") is not None:
        notes.append(
            "Revisit or coverage capability is not verified by the current deterministic tools and requires external coverage simulation."
        )
    if interpretation.get("target_region") is None:
        notes.append("Target region is not specific enough for orbit/coverage trade studies.")
    if interpretation.get("sensor_type") is None:
        notes.append("Payload type is only a hint until the user confirms sensor type and resolution.")
    return notes


def _extract_first_float(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return round(float(match.group(1).replace(",", ".")), 3)
    return None


def _remove_revisit_phrases(text: str) -> str:
    text = re.sub(
        r"(?:每|每隔)?\s*\d+(?:[.,]\d+)?\s*(?:小时|h|hr|hour|hours)\s*(?:内|访问|重访|看|一次|一遍)*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(
        r"(?:每天|每日|一天|24\s*小时)\s*(?:内)?\s*(?:看|访问|重访|观测|覆盖)?\s*[一二两三四五六七八九十\d]+\s*次",
        "",
        text,
        flags=re.IGNORECASE,
    )


def _clean_target_candidate(candidate: str) -> str:
    cleaned = candidate.strip()
    cleaned = re.sub(r"^(一次|一遍|两次|二次|多次|的|区域|地区)\s*", "", cleaned)
    cleaned = re.sub(
        r"(的)?(遥感卫星|观测卫星|监测卫星|遥感任务|观测任务|监测任务|卫星|任务)$",
        "",
        cleaned,
    )
    cleaned = re.sub(r"^(帮我|我想|我只想|请|设计|规划|做|一颗|一个|某个|某些|某一)\s*", "", cleaned)
    return cleaned.strip(" 的，。；;,.")


def _is_vague_target(candidate: str) -> bool:
    normalized = candidate.strip()
    if not normalized:
        return True
    if normalized in _VAGUE_TARGET_TERMS:
        return True
    return any(term in normalized for term in ("某个", "某些", "某一", "目标区域"))


def _number_from_text(token: str) -> int | None:
    token = token.strip()
    if token.isdigit():
        return int(token)
    digits = {
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
    }
    if token in digits:
        return digits[token]
    if "十" in token:
        left, _, right = token.partition("十")
        tens = digits.get(left, 1) if left else 1
        ones = digits.get(right, 0) if right else 0
        return tens * 10 + ones
    return None


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)
