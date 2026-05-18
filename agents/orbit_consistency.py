"""
Orbit parameter consistency validation for spacecraft conceptual design.

Checks for contradictions between orbit type, orbit geometry, and user-supplied
orbital parameters. Severe contradictions block ordinary report generation.
"""

import re
from copy import deepcopy
from typing import Any, Dict, List, Optional, Set

from tools.orbit import R_EARTH, orbit_period_from_semi_major_axis


R_EARTH_KM = R_EARTH / 1000.0
PERIOD_WARNING_RELATIVE = 0.05
PERIOD_WARNING_MINUTES = 5.0
PERIOD_SEVERE_RELATIVE = 0.10
PERIOD_SEVERE_MINUTES = 10.0
SMA_ALTITUDE_TOLERANCE_KM = 20.0


class OrbitConflict:
    """Result of an orbit consistency check."""

    def __init__(
        self,
        field: str,
        level: str,
        message: str,
        conflict: Dict[str, Any],
        suggested_user_action: str,
    ):
        self.field = field
        self.level = level
        self.message = message
        self.conflict = conflict
        self.suggested_user_action = suggested_user_action

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "level": self.level,
            "message": self.message,
            "conflict": self.conflict,
            "suggested_user_action": self.suggested_user_action,
        }


def _is_available(entry: dict) -> bool:
    return bool(entry.get("found") and entry.get("value") is not None)


def _filtered_params_by_source(params: dict, source_filter: Optional[Set[str]]) -> dict:
    if source_filter is None:
        return params

    filtered = {}
    for key, entry in params.items():
        if key.startswith("_") or not isinstance(entry, dict):
            filtered[key] = deepcopy(entry)
            continue
        cloned = deepcopy(entry)
        if not (_is_available(cloned) and cloned.get("source") in source_filter):
            cloned["value"] = None
            cloned["found"] = False
            cloned["source"] = "not_found"
            cloned["status"] = "missing"
            cloned["requires_confirmation"] = True
        filtered[key] = cloned
    return filtered


def _add_stage(conflict: Optional[OrbitConflict], stage: str) -> Optional[OrbitConflict]:
    if conflict is not None:
        conflict.conflict.setdefault("stage", stage)
    return conflict


def _check_polar_inclination(orbit_type: str, params: dict) -> Optional[OrbitConflict]:
    """Polar orbit should have inclination near 90 deg."""

    incl = params.get("orbit_inclination_deg", {})
    if not _is_available(incl):
        return None

    inc_val = float(incl["value"])
    if inc_val < 80.0 or inc_val > 100.0:
        return OrbitConflict(
            field="orbit_inclination_deg",
            level="warning",
            message=(
                f"Polar orbit normally has inclination near 90 deg, "
                f"but {inc_val} deg was provided."
            ),
            conflict={
                "orbit_type": orbit_type,
                "provided_value": f"{inc_val} deg",
                "expected_range": "near 90 deg (80-100 deg)",
            },
            suggested_user_action="Please confirm whether the orbit type or inclination is correct.",
        )
    return None


def _check_sso_inclination(orbit_type: str, params: dict) -> Optional[OrbitConflict]:
    """SSO should have retrograde inclination (typically 97-99 deg for LEO)."""

    incl = params.get("orbit_inclination_deg", {})
    if not _is_available(incl):
        return None

    inc_val = float(incl["value"])
    if inc_val < 95.0 or inc_val > 105.0:
        return OrbitConflict(
            field="orbit_inclination_deg",
            level="warning",
            message=(
                "SSO normally has retrograde inclination (typically 97-99 deg "
                f"for common LEO altitudes), but {inc_val} deg was provided."
            ),
            conflict={
                "orbit_type": orbit_type,
                "provided_value": f"{inc_val} deg",
                "expected_range": "97-99 deg (typical LEO SSO)",
            },
            suggested_user_action="Please confirm whether the orbit type or inclination is correct.",
        )
    return None


def _check_sso_altitude(orbit_type: str, params: dict) -> Optional[OrbitConflict]:
    """SSO should be in the LEO altitude regime for this MVP."""

    alt = params.get("orbit_altitude_km", {})
    if not _is_available(alt):
        return None

    alt_val = float(alt["value"])
    if alt_val < 160.0 or alt_val > 2000.0:
        return OrbitConflict(
            field="orbit_altitude_km",
            level="severe",
            message=(
                f"SSO orbit with altitude {alt_val} km is contradictory. "
                "SSO is a LEO orbit typically below 2000 km."
            ),
            conflict={
                "orbit_type": orbit_type,
                "provided_value": f"{alt_val} km",
                "expected_range": "160-2000 km (LEO range)",
            },
            suggested_user_action="Please confirm whether the orbit type or altitude is correct.",
        )
    return None


def _check_geo_altitude(orbit_type: str, params: dict) -> Optional[OrbitConflict]:
    """GEO/geostationary altitude should be near 35786 km."""

    alt = params.get("orbit_altitude_km", {})
    if not _is_available(alt):
        return None

    alt_val = float(alt["value"])
    if alt_val < 35000.0 or alt_val > 36000.0:
        return OrbitConflict(
            field="orbit_altitude_km",
            level="severe",
            message=(
                f"GEO/geostationary orbit with altitude {alt_val} km is "
                "contradictory. GEO altitude is approximately 35,786 km."
            ),
            conflict={
                "orbit_type": orbit_type,
                "provided_value": f"{alt_val} km",
                "expected_range": "~35,786 km",
            },
            suggested_user_action="Please confirm whether the orbit type or altitude is correct.",
        )
    return None


def _check_geo_inclination(orbit_type: str, params: dict) -> Optional[OrbitConflict]:
    """Geostationary inclination should be near 0 deg."""

    incl = params.get("orbit_inclination_deg", {})
    if not _is_available(incl):
        return None

    inc_val = float(incl["value"])
    if inc_val > 5.0:
        return OrbitConflict(
            field="orbit_inclination_deg",
            level="warning",
            message=(
                f"Geostationary orbit normally has inclination near 0 deg, "
                f"but {inc_val} deg was provided."
            ),
            conflict={
                "orbit_type": orbit_type,
                "provided_value": f"{inc_val} deg",
                "expected_range": "near 0 deg",
            },
            suggested_user_action="Please confirm whether the orbit type or inclination is correct.",
        )
    return None


def _check_circular_eccentricity(orbit_type: str, params: dict) -> Optional[OrbitConflict]:
    """Circular orbit should have eccentricity near 0."""

    ecc = params.get("eccentricity", {})
    if not _is_available(ecc):
        return None

    ecc_val = float(ecc["value"])
    if ecc_val > 0.05:
        level = "severe" if ecc_val >= 0.10 else "warning"
        return OrbitConflict(
            field="eccentricity",
            level=level,
            message=(
                f"Circular orbit normally has eccentricity near 0, "
                f"but {ecc_val} was provided."
            ),
            conflict={
                "orbit_type": orbit_type,
                "provided_value": str(ecc_val),
                "expected_range": "near 0 (<= 0.05)",
            },
            suggested_user_action="Please confirm whether the orbit type or eccentricity is correct.",
        )
    return None


def _text_implies_circular_orbit(text: Optional[str]) -> bool:
    if not text:
        return False
    return bool(
        re.search(
            r"圆轨道|近圆轨道|圆形轨道|near[-\s]?circular orbit|circular orbit|\bcircular\b",
            text,
            re.IGNORECASE,
        )
    )


def _has_circular_shape_semantics(
    orbit_type: Optional[str],
    params: dict,
    user_text: Optional[str] = None,
) -> bool:
    orbit_type_text = str(orbit_type or "").strip().lower()
    if orbit_type_text in {
        "elliptical orbit",
        "highly elliptical orbit",
        "heo",
    }:
        return False
    if orbit_type_text in {
        "circular orbit",
        "near circular orbit",
        "near-circular orbit",
    }:
        return True
    if _text_implies_circular_orbit(user_text):
        return True

    semantics = params.get("_orbit_semantics", {})
    if isinstance(semantics, dict):
        return semantics.get("shape_type") == "circular orbit"
    return False


def _check_leo_altitude(orbit_type: str, params: dict) -> Optional[OrbitConflict]:
    """LEO altitude should be in the 160-2000 km range."""

    alt = params.get("orbit_altitude_km", {})
    if not _is_available(alt):
        return None

    alt_val = float(alt["value"])
    if alt_val < 160.0 or alt_val > 2000.0:
        return OrbitConflict(
            field="orbit_altitude_km",
            level="severe",
            message=(
                f"LEO orbit with altitude {alt_val} km is contradictory. "
                "LEO altitude is typically 160-2000 km."
            ),
            conflict={
                "orbit_type": orbit_type,
                "provided_value": f"{alt_val} km",
                "expected_range": "160-2000 km",
            },
            suggested_user_action="Please confirm whether the orbit type or altitude is correct.",
        )
    return None


def compute_orbit_period_min_from_semi_major_axis(semi_major_axis_km: float) -> float:
    """Compute two-body orbital period from semi-major axis in kilometers."""

    result = orbit_period_from_semi_major_axis(float(semi_major_axis_km))
    return float(result["period_minutes"])


def expected_period_from_available_geometry(params: dict) -> tuple[Optional[float], str]:
    """Return expected period from semi-major axis or altitude-derived SMA."""

    semi_major_axis = params.get("semi_major_axis_km", {})
    if _is_available(semi_major_axis):
        return (
            round(compute_orbit_period_min_from_semi_major_axis(float(semi_major_axis["value"])), 2),
            "semi_major_axis_km",
        )

    altitude = params.get("orbit_altitude_km", {})
    if _is_available(altitude):
        derived_sma = R_EARTH_KM + float(altitude["value"])
        return (
            round(compute_orbit_period_min_from_semi_major_axis(derived_sma), 2),
            "orbit_altitude_km->semi_major_axis_km",
        )

    return None, "not_available"


def _check_altitude_sma_consistency(params: dict) -> Optional[OrbitConflict]:
    """Check whether altitude and semi-major axis describe the same orbit size."""

    altitude = params.get("orbit_altitude_km", {})
    semi_major_axis = params.get("semi_major_axis_km", {})
    if not _is_available(altitude) or not _is_available(semi_major_axis):
        return None

    expected_sma = R_EARTH_KM + float(altitude["value"])
    provided_sma = float(semi_major_axis["value"])
    diff = abs(provided_sma - expected_sma)
    if diff <= SMA_ALTITUDE_TOLERANCE_KM:
        return None

    return OrbitConflict(
        field="semi_major_axis_km",
        level="warning",
        message=(
            f"Semi-major axis {provided_sma:.2f} km is not consistent with "
            f"altitude {float(altitude['value']):.2f} km. Two-body circular "
            f"geometry expects approximately {expected_sma:.2f} km."
        ),
        conflict={
            "orbit_altitude_km": f"{float(altitude['value']):.2f} km",
            "provided_semi_major_axis": f"{provided_sma:.2f} km",
            "expected_semi_major_axis": f"{expected_sma:.2f} km",
            "difference_km": round(diff, 2),
        },
        suggested_user_action="Please confirm whether altitude or semi-major axis is intended.",
    )


def _check_orbit_period_consistency(params: dict) -> Optional[OrbitConflict]:
    """Compare user-provided orbital period with two-body period from geometry."""

    period_entry = params.get("orbit_period_min", {})
    if not _is_available(period_entry):
        return None

    expected_period, source = expected_period_from_available_geometry(params)
    if expected_period is None:
        return None

    provided_period = float(period_entry["value"])
    diff_min = abs(provided_period - expected_period)
    relative_diff = diff_min / expected_period if expected_period else 0.0

    if relative_diff <= PERIOD_WARNING_RELATIVE and diff_min <= PERIOD_WARNING_MINUTES:
        return None

    level = (
        "severe"
        if relative_diff > PERIOD_SEVERE_RELATIVE and diff_min > PERIOD_SEVERE_MINUTES
        else "warning"
    )
    return OrbitConflict(
        field="orbit_period_min",
        level=level,
        message=(
            f"Provided orbit period {provided_period:.2f} min is inconsistent "
            f"with the two-body estimate {expected_period:.2f} min from {source}. "
            f"Difference is {diff_min:.2f} min ({relative_diff:.1%})."
        ),
        conflict={
            "provided_period_min": round(provided_period, 2),
            "computed_period_min": round(expected_period, 2),
            "computed_from": source,
            "difference_min": round(diff_min, 2),
            "relative_difference": round(relative_diff, 4),
            "warning_threshold": f">{PERIOD_WARNING_RELATIVE:.0%} or >{PERIOD_WARNING_MINUTES} min",
            "severe_threshold": f">{PERIOD_SEVERE_RELATIVE:.0%} and >{PERIOD_SEVERE_MINUTES} min",
        },
        suggested_user_action=(
            "Please confirm the orbit period, altitude, or semi-major axis. "
            "The check uses a two-body conceptual estimate, not high-fidelity propagation."
        ),
    )


ORBIT_CONSISTENCY_CHECKS: Dict[str, List] = {
    "polar orbit": [_check_polar_inclination],
    "SSO": [_check_sso_inclination, _check_sso_altitude],
    "GEO": [_check_geo_altitude, _check_geo_inclination],
    "geostationary orbit": [_check_geo_altitude, _check_geo_inclination],
    "geosynchronous orbit": [_check_geo_altitude],
    "circular orbit": [_check_circular_eccentricity],
    "LEO": [_check_leo_altitude],
}


def validate_orbit_consistency(
    params: dict,
    *,
    stage: str = "post_inference",
    source_filter: Optional[Set[str]] = None,
    user_text: Optional[str] = None,
) -> List[OrbitConflict]:
    """Validate orbit parameters for contradictions.

    ``source_filter`` lets app.py run a first pass over explicit user input
    before any inferred/default/tool-computed values are merged in.
    """

    check_params = _filtered_params_by_source(params, source_filter)
    results: List[OrbitConflict] = []

    for generic_check in (
        _check_altitude_sma_consistency,
        _check_orbit_period_consistency,
    ):
        conflict = _add_stage(generic_check(check_params), stage)
        if conflict is not None:
            results.append(conflict)

    orbit_entry = check_params.get("orbit_type", {})
    orbit_type = orbit_entry.get("value") if _is_available(orbit_entry) else None

    has_circular_semantics = _has_circular_shape_semantics(
        orbit_type,
        check_params,
        user_text,
    )
    if has_circular_semantics:
        conflict = _add_stage(_check_circular_eccentricity("circular orbit", check_params), stage)
        if conflict is not None:
            results.append(conflict)

    if orbit_type is None:
        return results

    checks = ORBIT_CONSISTENCY_CHECKS.get(orbit_type, [])
    for check_fn in checks:
        if check_fn is _check_circular_eccentricity and has_circular_semantics:
            continue
        conflict = _add_stage(check_fn(orbit_type, check_params), stage)
        if conflict is not None:
            results.append(conflict)

    return results


def has_severe_orbit_conflicts(conflicts: List[OrbitConflict]) -> bool:
    """Return True if any orbit consistency conflict is severe."""

    return any(c.level == "severe" for c in conflicts)
