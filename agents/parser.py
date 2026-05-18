"""
Rules-based mission parameter parser.

This module is intentionally lightweight and remains the fallback path when
LLM extraction is disabled or fails. It extracts explicit text spans only;
unit conversion and schema normalization are handled in agents.normalizer.
"""

import re


NUM = r"(\d+(?:[.,]\d+)?)"
DISTANCE_UNIT = r"(km|kilometer|kilometers|kilometre|kilometres|公里|千米|m|meter|meters|metre|metres|米)"
MASS_UNIT = r"(kg|kilogram|kilograms|千克|公斤|g|gram|grams|克|t|ton|tons|tonne|tonnes|吨|噸)"
POWER_UNIT = r"(kw|kilowatt|kilowatts|千瓦|w|watt|watts|瓦)"
ANGLE_UNIT = r"(deg|degree|degrees|°|度)"
PERIOD_UNIT = r"(min|minute|minutes|分钟|分|h|hr|hour|hours|小时|s|sec|second|seconds|秒|d|day|days|天|日)"
LIFETIME_UNIT = r"(year|years|yr|yrs|y|年|month|months|月|d|day|days|天|日)"
ASSIGN_WORD = r"(?:=|:|：|为|是|改为|调整为|设为|设置为|改成)"

ALTITUDE_PATTERN = re.compile(
    r"(?:(?:orbit\s+altitude|altitude|轨道高度|高度)\s*" + ASSIGN_WORD + r"?\s*)?"
    + NUM
    + r"\s*"
    + DISTANCE_UNIT
    + r"(?=\s*(?:轨道|orbit|altitude|高度|$|[,，。;；]))",
    re.IGNORECASE,
)
MASS_PATTERN = re.compile(NUM + r"\s*" + MASS_UNIT, re.IGNORECASE)
POWER_PATTERN = re.compile(NUM + r"\s*" + POWER_UNIT, re.IGNORECASE)
INCLINATION_PATTERN = re.compile(
    r"(?:轨道倾角|倾角|inclination|(?<![A-Za-z])i\s*(?:=|:|：))\s*" + ASSIGN_WORD + r"?\s*"
    + NUM
    + r"\s*"
    + ANGLE_UNIT,
    re.IGNORECASE,
)
PERIOD_PATTERN = re.compile(
    r"(?:轨道周期|周期|orbital\s+period|period)\s*(?:约|大约)?" + ASSIGN_WORD + r"?\s*"
    + NUM
    + r"\s*"
    + PERIOD_UNIT,
    re.IGNORECASE,
)
RESOLUTION_PATTERN = re.compile(
    r"(?:(?:ground\s+resolution|resolution|分辨率)\s*" + ASSIGN_WORD + r"?\s*"
    + NUM
    + r"\s*"
    + DISTANCE_UNIT
    + r"|"
    + NUM
    + r"\s*"
    + DISTANCE_UNIT
    + r"\s*(?:ground\s+resolution|resolution|分辨率))",
    re.IGNORECASE,
)
LIFETIME_PATTERN = re.compile(
    r"(?:任务寿命|寿命|mission\s+lifetime|lifetime)\s*(?:约|大约)?" + ASSIGN_WORD + r"?\s*"
    + NUM
    + r"\s*"
    + LIFETIME_UNIT,
    re.IGNORECASE,
)
ECCENTRICITY_PATTERN = re.compile(
    r"(?:偏心率|eccentricity|(?<![A-Za-z])e\s*(?:=|:|：))\s*" + ASSIGN_WORD + r"?\s*" + NUM,
    re.IGNORECASE,
)
SEMI_MAJOR_AXIS_PATTERN = re.compile(
    r"(?:semi[-\s]?major axis|半长轴|sma|(?<![A-Za-z])a\s*(?:=|:|：))\s*" + ASSIGN_WORD + r"?\s*"
    + NUM
    + r"\s*"
    + DISTANCE_UNIT,
    re.IGNORECASE,
)
RAAN_PATTERN = re.compile(
    r"(?:raan|升交点赤经)\s*" + ASSIGN_WORD + r"?\s*" + NUM + r"\s*" + ANGLE_UNIT,
    re.IGNORECASE,
)
ARG_PERIGEE_PATTERN = re.compile(
    r"(?:arg(?:ument)?(?:\s+of)?\s+perigee|近地点幅角)\s*" + ASSIGN_WORD + r"?\s*"
    + NUM
    + r"\s*"
    + ANGLE_UNIT,
    re.IGNORECASE,
)
TRUE_ANOMALY_PATTERN = re.compile(
    r"(?:true anomaly|真近点角)\s*" + ASSIGN_WORD + r"?\s*" + NUM + r"\s*" + ANGLE_UNIT,
    re.IGNORECASE,
)


ALTITUDE_EXPLICIT_PATTERN = re.compile(
    r"(?:orbit\s+altitude|altitude|轨道高度|高度)\s*(?:=|:|：|为|是|改为|调整为|设为|设置为|改成)?\s*"
    + NUM
    + r"\s*"
    + DISTANCE_UNIT,
    re.IGNORECASE,
)
INCLINATION_EXPLICIT_PATTERN = re.compile(
    r"(?:轨道倾角|倾角|inclination)\s*(?:=|:|：|为|是|改为|调整为|设为|设置为|改成)?\s*"
    + NUM
    + r"\s*"
    + ANGLE_UNIT,
    re.IGNORECASE,
)
ECCENTRICITY_EXPLICIT_PATTERN = re.compile(
    r"(?:偏心率|eccentricity|(?<![A-Za-z])e)\s*(?:=|:|：|为|是|改为|调整为|设为|设置为|改成)?\s*"
    + NUM,
    re.IGNORECASE,
)
RESOLUTION_EXPLICIT_PATTERN = re.compile(
    r"(?:地面分辨率|分辨率|ground\s+resolution|resolution)\s*(?:=|:|：|为|是|改为|调整为|设为|设置为|改成)?\s*"
    + NUM
    + r"\s*"
    + DISTANCE_UNIT,
    re.IGNORECASE,
)
RAAN_EXPLICIT_PATTERN = re.compile(
    r"(?:raan|升交点赤经)\s*(?:=|:|：|为|是|改为|调整为|设为|设置为|改成)?\s*"
    + NUM
    + r"\s*"
    + ANGLE_UNIT,
    re.IGNORECASE,
)


ORBIT_TYPE_RULES = [
    (re.compile(r"圆轨道|近圆轨道|圆形轨道|near[-\s]?circular orbit|circular orbit|\bcircular\b", re.IGNORECASE), "circular orbit"),
    (re.compile(r"椭圆轨道|elliptical orbit|\belliptical\b", re.IGNORECASE), "elliptical orbit"),
    (re.compile(r"太阳同步轨道|太阳同步|sun[-\s]?synchronous|sso", re.IGNORECASE), "SSO"),
    (re.compile(r"极地轨道|极轨|polar orbit|\bpolar\b", re.IGNORECASE), "polar orbit"),
    (re.compile(r"低轨|近地轨道|近地|low earth orbit|leo", re.IGNORECASE), "LEO"),
    (re.compile(r"地球静止轨道|地球同步轨道|geostationary|geosynchronous|geo", re.IGNORECASE), "GEO"),
    (re.compile(r"中轨|中地球轨道|medium earth orbit|meo", re.IGNORECASE), "MEO"),
    (re.compile(r"高椭圆轨道|highly elliptical orbit|heo", re.IGNORECASE), "HEO"),
    (re.compile(r"\bGTO\b", re.IGNORECASE), "GTO"),
]


def _float(text: str) -> float:
    return float(text.replace(",", "."))


def _not_found(unit):
    return {"value": None, "unit": unit, "found": False, "source": "not_found"}


def _found(match: re.Match, value_group: int, unit_group=None) -> dict:
    return {
        "value": _float(match.group(value_group)),
        "unit": match.group(unit_group) if unit_group is not None else None,
        "found": True,
        "source": "extracted",
        "raw_text": match.group(0),
    }


def parse_mission_requirements(text: str) -> dict:
    """Parse explicit natural-language mission parameters using regex rules."""

    return {
        "orbit_altitude_km": _extract_altitude(text),
        "semi_major_axis_km": _extract_semi_major_axis(text),
        "eccentricity": _extract_eccentricity(text),
        "payload_mass_kg": _extract_mass(text),
        "power_required_w": _extract_power(text),
        "orbit_inclination_deg": _extract_inclination(text),
        "orbit_period_min": _extract_period(text),
        "raan_deg": _extract_raan(text),
        "arg_perigee_deg": _extract_arg_perigee(text),
        "true_anomaly_deg": _extract_true_anomaly(text),
        "orbit_type": _extract_orbit_type(text),
        "mission_lifetime_years": _extract_lifetime(text),
        "ground_resolution_m": _extract_resolution(text),
    }


def _extract_altitude(text: str) -> dict:
    explicit_match = ALTITUDE_EXPLICIT_PATTERN.search(text)
    if explicit_match:
        return _found(explicit_match, 1, 2)

    match = ALTITUDE_PATTERN.search(text)
    if match:
        unit = str(match.group(2) or "").lower()
        raw_text = match.group(0)
        has_altitude_word = re.search(r"orbit\s+altitude|altitude|轨道高度|高度", raw_text, re.IGNORECASE)
        if unit in {"m", "meter", "meters", "metre", "metres", "米"} and not has_altitude_word:
            return _not_found("km")
        return _found(match, 1, 2)
    return _not_found("km")


def _extract_semi_major_axis(text: str) -> dict:
    match = SEMI_MAJOR_AXIS_PATTERN.search(text)
    if match:
        return _found(match, 1, 2)
    return _not_found("km")


def _extract_eccentricity(text: str) -> dict:
    explicit_match = ECCENTRICITY_EXPLICIT_PATTERN.search(text)
    if explicit_match:
        return _found(explicit_match, 1)

    match = ECCENTRICITY_PATTERN.search(text)
    if match:
        return _found(match, 1)
    return _not_found(None)


def _extract_mass(text: str) -> dict:
    match = MASS_PATTERN.search(text)
    if match:
        return _found(match, 1, 2)
    return _not_found("kg")


def _extract_power(text: str) -> dict:
    match = POWER_PATTERN.search(text)
    if match:
        return _found(match, 1, 2)
    return _not_found("W")


def _extract_inclination(text: str) -> dict:
    explicit_match = INCLINATION_EXPLICIT_PATTERN.search(text)
    if explicit_match:
        return _found(explicit_match, 1, 2)

    match = INCLINATION_PATTERN.search(text)
    if match:
        return _found(match, 1, 2)
    return _not_found("deg")


def _extract_period(text: str) -> dict:
    match = PERIOD_PATTERN.search(text)
    if match:
        return _found(match, 1, 2)
    return _not_found("min")


def _extract_raan(text: str) -> dict:
    explicit_match = RAAN_EXPLICIT_PATTERN.search(text)
    if explicit_match:
        return _found(explicit_match, 1, 2)

    match = RAAN_PATTERN.search(text)
    if match:
        return _found(match, 1, 2)
    return _not_found("deg")


def _extract_arg_perigee(text: str) -> dict:
    match = ARG_PERIGEE_PATTERN.search(text)
    if match:
        return _found(match, 1, 2)
    return _not_found("deg")


def _extract_true_anomaly(text: str) -> dict:
    match = TRUE_ANOMALY_PATTERN.search(text)
    if match:
        return _found(match, 1, 2)
    return _not_found("deg")


def _extract_orbit_type(text: str) -> dict:
    for pattern, value in ORBIT_TYPE_RULES:
        match = pattern.search(text)
        if match:
            return {
                "value": value,
                "unit": None,
                "found": True,
                "source": "extracted",
                "raw_text": match.group(0),
            }
    return _not_found(None)


def _extract_lifetime(text: str) -> dict:
    match = LIFETIME_PATTERN.search(text)
    if match:
        return _found(match, 1, 2)
    return _not_found("years")


def _extract_resolution(text: str) -> dict:
    explicit_match = RESOLUTION_EXPLICIT_PATTERN.search(text)
    if explicit_match:
        return _found(explicit_match, 1, 2)

    match = RESOLUTION_PATTERN.search(text)
    if not match:
        return _not_found("m")
    if match.group(1) is not None:
        return _found(match, 1, 2)
    return _found(match, 3, 4)


def identify_missing_parameters(params: dict) -> list:
    """Identify missing required and recommended parameters."""

    missing = []
    required_params = {
        "orbit_altitude_km": "轨道高度 (Orbit altitude)",
        "payload_mass_kg": "有效载荷质量 (Payload mass)",
    }
    recommended_params = {
        "power_required_w": "功率需求 (Power requirement)",
        "orbit_type": "轨道类型 (Orbit type)",
        "mission_lifetime_years": "任务寿命 (Mission lifetime)",
    }

    for key, desc in required_params.items():
        if key in params and not params[key].get("found"):
            missing.append({"parameter": key, "description": desc, "severity": "required"})

    for key, desc in recommended_params.items():
        if key in params and not params[key].get("found"):
            missing.append({"parameter": key, "description": desc, "severity": "recommended"})

    return missing
