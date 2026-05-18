"""
Parameter normalization for spacecraft conceptual design.

This module converts explicit LLM or rules-parser output into the internal
parameter schema. It is deterministic: no LLM calls and no engineering
inference are performed here.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


INTERNAL_PARAM_KEYS = [
    "orbit_altitude_km",
    "semi_major_axis_km",
    "eccentricity",
    "payload_mass_kg",
    "power_required_w",
    "orbit_inclination_deg",
    "orbit_period_min",
    "raan_deg",
    "arg_perigee_deg",
    "true_anomaly_deg",
    "orbit_type",
    "mission_lifetime_years",
    "ground_resolution_m",
]

STANDARDIZED = "standardized"
MISSING_UNIT = "missing_unit"
INVALID_UNIT = "invalid_unit"
NOT_FOUND = "not_found"

MASS_TO_KG: List[Tuple[str, float]] = [
    (r"^\s*(g|gram|grams|克)\s*$", 0.001),
    (r"^\s*(kg|kilogram|kilograms|千克|公斤|鍗冨厠|鍏枻)\s*$", 1.0),
    (r"^\s*(t|ton|tons|tonne|tonnes|吨|噸|鍚▅鍏惃)\s*$", 1000.0),
]

POWER_TO_W: List[Tuple[str, float]] = [
    (r"^\s*(w|watt|watts|瓦|鐡鐡︾壒)\s*$", 1.0),
    (r"^\s*(kw|kilowatt|kilowatts|千瓦|鍗冪摝)\s*$", 1000.0),
]

DISTANCE_TO_KM: List[Tuple[str, float]] = [
    (r"^\s*(m|meter|meters|metre|metres|米|绫硘鍏昂)\s*$", 0.001),
    (r"^\s*(km|kilometer|kilometers|kilometre|kilometres|公里|千米|鍏噷|鍗冪背)\s*$", 1.0),
]

LENGTH_TO_M: List[Tuple[str, float]] = [
    (r"^\s*(m|meter|meters|metre|metres|米|绫硘鍏昂)\s*$", 1.0),
    (r"^\s*(km|kilometer|kilometers|kilometre|kilometres|公里|千米|鍏噷|鍗冪背)\s*$", 1000.0),
]

TIME_TO_YEARS: List[Tuple[str, float]] = [
    (r"^\s*(s|sec|second|seconds|秒)\s*$", 1.0 / (365.25 * 24.0 * 60.0 * 60.0)),
    (r"^\s*(min|minute|minutes|分钟|分|鍒嗛挓|鍒?)\s*$", 1.0 / (365.25 * 24.0 * 60.0)),
    (r"^\s*(h|hr|hour|hours|小时|灏忔椂)\s*$", 1.0 / (365.25 * 24.0)),
    (r"^\s*(d|day|days|天|日)\s*$", 1.0 / 365.25),
    (r"^\s*(month|months|月|鏈坾涓湀)\s*$", 1.0 / 12.0),
    (r"^\s*(y|yr|yrs|year|years|年|骞?)\s*$", 1.0),
]

ANGLE_TO_DEG: List[Tuple[str, float]] = [
    (r"^\s*(deg|degree|degrees|°|度|掳|搴?)\s*$", 1.0),
]

PERIOD_TO_MIN: List[Tuple[str, float]] = [
    (r"^\s*(s|sec|second|seconds|秒|绉?)\s*$", 1.0 / 60.0),
    (r"^\s*(min|minute|minutes|分钟|分|鍒嗛挓|鍒?)\s*$", 1.0),
    (r"^\s*(h|hr|hour|hours|小时|灏忔椂)\s*$", 60.0),
    (r"^\s*(d|day|days|天|日)\s*$", 1440.0),
]

DATA_TO_GB: List[Tuple[str, float]] = [
    (r"^\s*(g|gb|gigabyte|gigabytes)\s*$", 1.0),
    (r"^\s*(t|tb|terabyte|terabytes)\s*$", 1024.0),
]

REVISIT_TO_HOURS: List[Tuple[str, float]] = [
    (r"^\s*(min|minute|minutes|分钟|分)\s*$", 1.0 / 60.0),
    (r"^\s*(h|hr|hour|hours|小时)\s*$", 1.0),
    (r"^\s*(d|day|days|天|日)\s*$", 24.0),
]

ORBIT_TYPE_MAP: Dict[str, str] = {
    "太阳同步轨道": "SSO",
    "太阳同步": "SSO",
    "澶槼鍚屾杞ㄩ亾": "SSO",
    "澶槼鍚屾": "SSO",
    "sso": "SSO",
    "sun-synchronous orbit": "SSO",
    "sun synchronous orbit": "SSO",
    "polar orbit": "polar orbit",
    "polar": "polar orbit",
    "极地轨道": "polar orbit",
    "极轨": "polar orbit",
    "鏋佸湴杞ㄩ亾": "polar orbit",
    "鏋佽建": "polar orbit",
    "leo": "LEO",
    "low earth orbit": "LEO",
    "低轨": "LEO",
    "近地轨道": "LEO",
    "近地": "LEO",
    "浣庤建": "LEO",
    "杩戝湴杞ㄩ亾": "LEO",
    "杩戝湴": "LEO",
    "geo": "GEO",
    "geostationary orbit": "GEO",
    "geostationary": "GEO",
    "geosynchronous orbit": "GEO",
    "地球静止轨道": "GEO",
    "地球同步轨道": "GEO",
    "鍦扮悆闈欐杞ㄩ亾": "GEO",
    "鍦扮悆鍚屾杞ㄩ亾": "GEO",
    "meo": "MEO",
    "medium earth orbit": "MEO",
    "中轨": "MEO",
    "中地球轨道": "MEO",
    "涓建": "MEO",
    "heo": "HEO",
    "highly elliptical orbit": "HEO",
    "高椭圆轨道": "HEO",
    "circular": "circular orbit",
    "circular orbit": "circular orbit",
    "near circular orbit": "circular orbit",
    "near-circular orbit": "circular orbit",
    "圆轨道": "circular orbit",
    "近圆轨道": "circular orbit",
    "圆形轨道": "circular orbit",
    "近圆": "circular orbit",
    "圆": "circular orbit",
    "鍦嗚建閬?": "circular orbit",
    "杩戝渾杞ㄩ亾": "circular orbit",
    "鍦嗗舰杞ㄩ亾": "circular orbit",
    "杩戝渾": "circular orbit",
    "elliptical orbit": "elliptical orbit",
    "elliptical": "elliptical orbit",
    "椭圆轨道": "elliptical orbit",
    "妞渾杞ㄩ亾": "elliptical orbit",
}


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().replace(",", "."))
        except ValueError:
            return None
    return None


def _convert_value(
    value: Any,
    unit: Optional[str],
    conversion_table: List[Tuple[str, float]],
) -> Tuple[Optional[float], str]:
    numeric_value = _as_float(value)
    if numeric_value is None:
        return None, NOT_FOUND
    if unit is None or str(unit).strip() == "":
        return numeric_value, MISSING_UNIT
    unit_text = str(unit).strip()
    for pattern, multiplier in conversion_table:
        if re.match(pattern, unit_text, re.IGNORECASE):
            return numeric_value * multiplier, STANDARDIZED
    return numeric_value, INVALID_UNIT


def _clean_orbit_type_text(raw_value: str) -> str:
    return re.sub(r"[\s\-_，,。:：；;]+", "", raw_value.strip().lower())


def _normalize_orbit_type(raw_value: Optional[str]) -> Tuple[Optional[str], bool]:
    if raw_value is None:
        return None, False
    cleaned = str(raw_value).strip().lower()
    if cleaned in ORBIT_TYPE_MAP:
        return ORBIT_TYPE_MAP[cleaned], True

    fuzzy = _clean_orbit_type_text(cleaned)
    if fuzzy in ORBIT_TYPE_MAP:
        return ORBIT_TYPE_MAP[fuzzy], True

    for key, value in ORBIT_TYPE_MAP.items():
        key_fuzzy = _clean_orbit_type_text(key.lower())
        if key_fuzzy and (key_fuzzy in fuzzy or fuzzy in key_fuzzy):
            return value, True
    return str(raw_value).strip(), False


def _default_unit_for_key(key: str) -> Optional[str]:
    if key in {"orbit_altitude_km", "semi_major_axis_km"}:
        return "km"
    if key == "payload_mass_kg":
        return "kg"
    if key == "power_required_w":
        return "W"
    if key in {"orbit_inclination_deg", "raan_deg", "arg_perigee_deg", "true_anomaly_deg"}:
        return "deg"
    if key == "orbit_period_min":
        return "min"
    if key == "mission_lifetime_years":
        return "years"
    if key == "ground_resolution_m":
        return "m"
    return None


def _entry(
    found: bool,
    value: Any,
    unit: Optional[str],
    source: str,
    *,
    unit_status: Optional[str] = None,
    raw_unit: Optional[str] = None,
    raw_text: Optional[str] = None,
) -> dict:
    has_raw_value = bool(found and value is not None)
    if unit_status in {INVALID_UNIT, MISSING_UNIT} and has_raw_value:
        entry = {
            "value": value,
            "unit": unit,
            "found": False,
            "source": source,
            "status": unit_status,
            "requires_confirmation": True,
        }
    else:
        available = has_raw_value
        entry = {
            "value": value if available else None,
            "unit": unit,
            "found": available,
            "source": source if available else "not_found",
            "status": "user_provided" if available else "missing",
            "requires_confirmation": False if available else True,
        }
    if raw_unit is not None:
        entry["raw_unit"] = raw_unit
    if raw_text:
        entry["raw_text"] = raw_text
    if unit_status in {STANDARDIZED, INVALID_UNIT, MISSING_UNIT}:
        entry["unit_status"] = unit_status
    return entry


def _normalize_numeric_entry(
    key: str,
    raw_entry: dict,
    source: str,
    conversion_table: List[Tuple[str, float]],
) -> dict:
    raw_unit = raw_entry.get("unit")
    value, unit_status = _convert_value(raw_entry.get("value"), raw_unit, conversion_table)
    return _entry(
        raw_entry.get("found"),
        value,
        _default_unit_for_key(key),
        source,
        unit_status=unit_status,
        raw_unit=raw_unit,
        raw_text=raw_entry.get("raw_text"),
    )


def _normalize_dimensionless_entry(key: str, raw_entry: dict, source: str) -> dict:
    value = _as_float(raw_entry.get("value"))
    return _entry(
        raw_entry.get("found"),
        value,
        _default_unit_for_key(key),
        source,
        raw_text=raw_entry.get("raw_text"),
    )


def normalize_llm_output(llm_raw: dict) -> dict:
    mp = llm_raw.get("explicit_params") or llm_raw.get("mission_parameters", {})
    result: Dict[str, Any] = {}
    source = "llm_extracted_normalized"

    result["orbit_altitude_km"] = _normalize_numeric_entry(
        "orbit_altitude_km", mp.get("orbit_altitude", {}), source, DISTANCE_TO_KM
    )
    result["payload_mass_kg"] = _normalize_numeric_entry(
        "payload_mass_kg", mp.get("payload_mass", {}), source, MASS_TO_KG
    )
    result["power_required_w"] = _normalize_numeric_entry(
        "power_required_w", mp.get("power_required", {}), source, POWER_TO_W
    )
    result["orbit_inclination_deg"] = _normalize_numeric_entry(
        "orbit_inclination_deg", mp.get("orbit_inclination", {}), source, ANGLE_TO_DEG
    )
    result["orbit_period_min"] = _normalize_numeric_entry(
        "orbit_period_min", mp.get("orbit_period", {}), source, PERIOD_TO_MIN
    )

    orbit = mp.get("orbit_type", {})
    orbit_val, _mapped = _normalize_orbit_type(orbit.get("value"))
    result["orbit_type"] = _entry(
        orbit.get("found"),
        orbit_val,
        None,
        source,
        raw_text=orbit.get("raw_text"),
    )

    result["mission_lifetime_years"] = _normalize_numeric_entry(
        "mission_lifetime_years", mp.get("mission_lifetime", {}), source, TIME_TO_YEARS
    )
    result["ground_resolution_m"] = _normalize_numeric_entry(
        "ground_resolution_m", mp.get("ground_resolution", {}), source, LENGTH_TO_M
    )

    for key in INTERNAL_PARAM_KEYS:
        result.setdefault(key, _entry(False, None, _default_unit_for_key(key), "not_found"))
    return result


def _normalize_rules_entry(key: str, raw_entry: dict, source: str) -> dict:
    if key in {"orbit_altitude_km", "semi_major_axis_km"}:
        return _normalize_numeric_entry(key, raw_entry, source, DISTANCE_TO_KM)
    if key == "payload_mass_kg":
        return _normalize_numeric_entry(key, raw_entry, source, MASS_TO_KG)
    if key == "power_required_w":
        return _normalize_numeric_entry(key, raw_entry, source, POWER_TO_W)
    if key in {"orbit_inclination_deg", "raan_deg", "arg_perigee_deg", "true_anomaly_deg"}:
        return _normalize_numeric_entry(key, raw_entry, source, ANGLE_TO_DEG)
    if key == "orbit_period_min":
        return _normalize_numeric_entry(key, raw_entry, source, PERIOD_TO_MIN)
    if key == "mission_lifetime_years":
        return _normalize_numeric_entry(key, raw_entry, source, TIME_TO_YEARS)
    if key == "ground_resolution_m":
        return _normalize_numeric_entry(key, raw_entry, source, LENGTH_TO_M)
    if key == "eccentricity":
        return _normalize_dimensionless_entry(key, raw_entry, source)
    if key == "orbit_type":
        orbit_val, _mapped = _normalize_orbit_type(raw_entry.get("value"))
        return _entry(
            raw_entry.get("found"),
            orbit_val,
            None,
            source,
            raw_text=raw_entry.get("raw_text"),
        )
    return _entry(False, None, _default_unit_for_key(key), "not_found")


def normalize_rules_output(rules_params: dict) -> dict:
    result = {}
    source = "rules_fallback"
    for key in INTERNAL_PARAM_KEYS:
        entry = rules_params.get(key, {})
        result[key] = _normalize_rules_entry(key, entry, source)
    return result


def build_not_found_params() -> dict:
    return {
        key: {
            "value": None,
            "unit": _default_unit_for_key(key),
            "found": False,
            "source": "not_found",
            "status": "missing",
            "requires_confirmation": True,
        }
        for key in INTERNAL_PARAM_KEYS
    }
