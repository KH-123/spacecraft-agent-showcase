"""
Orbit intelligence helpers.

This module performs lightweight orbit interpretation for the MVP. It does not
do high-fidelity propagation. It only derives obvious conceptual orbital
parameters, records provenance, and identifies missing orbital elements before
downstream engineering tasks run.
"""

import math
import re
from typing import Any, Dict, List, Optional, Tuple

from tools.orbit import orbit_period_from_semi_major_axis


MU_EARTH = 3.986004418e14  # m^3/s^2
R_EARTH_KM = 6378.137
J2 = 1.08262668e-3

ORBIT_ELEMENT_KEYS = [
    "semi_major_axis_km",
    "eccentricity",
    "orbit_inclination_deg",
    "raan_deg",
    "arg_perigee_deg",
    "true_anomaly_deg",
]

# MVP core gate: semi-major axis, eccentricity, and inclination are required
# before ordinary tool execution.  A two-body period can be computed from
# semi-major axis alone, but the parameter-level design state is blocked until
# the orbit shape is explicitly available or cautiously inferred.
CORE_ORBIT_ELEMENT_KEYS = [
    "semi_major_axis_km",
    "eccentricity",
    "orbit_inclination_deg",
]

RECOMMENDED_ORBIT_ELEMENT_KEYS = []

DEFAULT_ANGLE_KEYS = [
    "raan_deg",
    "arg_perigee_deg",
    "true_anomaly_deg",
]


def _missing_entry(unit: Optional[str]) -> dict:
    return {
        "value": None,
        "unit": unit,
        "found": False,
        "source": "not_found",
        "status": "missing",
        "requires_confirmation": True,
    }


def _set_if_missing(params: dict, key: str, entry: dict, metadata: dict) -> None:
    existing = params.get(key, {})
    if existing.get("found") and existing.get("value") is not None:
        existing.setdefault("status", "user_provided")
        existing.setdefault("requires_confirmation", False)
        params[key] = existing
        return

    params[key] = entry
    if entry.get("found") and entry.get("value") is not None:
        metadata["inferred_parameters"].append(key)
    note = entry.get("inference_note")
    if note:
        metadata["inference_details"][key] = note
        metadata["assumptions"].append(note)


def _infer_sso_inclination(altitude_km: float) -> Tuple[Optional[float], str]:
    """Return an approximate SSO inclination using a simple J2 relation."""

    a_km = R_EARTH_KM + altitude_km
    a_m = a_km * 1000.0
    nodal_rate = 2.0 * math.pi / (365.25 * 86400.0)
    cos_i = -(
        2.0 * a_m ** 3.5 * nodal_rate
    ) / (3.0 * J2 * (R_EARTH_KM * 1000.0) ** 2 * math.sqrt(MU_EARTH))

    if -1.0 <= cos_i <= 1.0:
        inclination = round(math.degrees(math.acos(cos_i)), 1)
        note = (
            "Approximate SSO inclination from a simple J2 nodal precession "
            f"relation at altitude {altitude_km} km. This is an MVP "
            "conceptual estimate, not high-fidelity orbit propagation."
        )
        return inclination, note

    note = (
        "SSO inclination is typically near 97-99 deg for common LEO SSO. "
        f"The simple J2 estimate was out of range for altitude {altitude_km} km."
    )
    return None, note


def _extract_orbit_type_from_text(text: str) -> Optional[str]:
    text_lower = text.lower()
    patterns = [
        (r"太阳同步轨道|太阳同步|sun[-\s]?synchronous|sso", "SSO"),
        (r"极地轨道|极轨|polar orbit|\bpolar\b", "polar orbit"),
        (r"低轨|近地轨道|近地|low earth orbit|leo", "LEO"),
        (r"地球静止轨道|geostationary", "GEO"),
        (r"地球同步轨道|geosynchronous|geo", "GEO"),
        (r"中轨|中地球轨道|medium earth orbit|meo", "MEO"),
        (r"高椭圆轨道|highly elliptical orbit|heo", "HEO"),
        (r"圆轨道|近圆轨道|圆形轨道|near[-\s]?circular orbit|circular orbit|\bcircular\b", "circular orbit"),
        (r"椭圆轨道|elliptical orbit|\belliptical\b", "elliptical orbit"),
    ]
    for pattern, value in patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return value
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


def _is_circular_orbit_type(orbit_type: Optional[str]) -> bool:
    return str(orbit_type or "").strip().lower() in {
        "circular orbit",
        "near circular orbit",
        "near-circular orbit",
    }


def _is_elliptical_orbit_type(orbit_type: Optional[str]) -> bool:
    return str(orbit_type or "").strip().lower() in {
        "elliptical orbit",
        "highly elliptical orbit",
        "heo",
    }


def _record_orbit_semantics(
    params: dict,
    metadata: dict,
    *,
    shape_type: Optional[str] = None,
    source: str,
) -> None:
    semantics = params.setdefault("_orbit_semantics", {})
    metadata_semantics = metadata.setdefault("orbit_semantics", {})
    if shape_type:
        semantics["shape_type"] = shape_type
        semantics["shape_source"] = source
        metadata_semantics["shape_type"] = shape_type
        metadata_semantics["shape_source"] = source


def _compute_period_if_ready(params: dict, metadata: dict) -> None:
    period_entry = params.get("orbit_period_min", {})
    if period_entry.get("found") and period_entry.get("value") is not None:
        return

    semi_major_axis = params.get("semi_major_axis_km", {})
    if not semi_major_axis.get("found") or semi_major_axis.get("value") is None:
        return

    period = orbit_period_from_semi_major_axis(float(semi_major_axis["value"]))
    note = (
        "Orbit period computed with tools.orbit.orbit_period_from_semi_major_axis "
        "from semi-major axis using a two-body Keplerian estimate."
    )
    _set_if_missing(
        params,
        "orbit_period_min",
        {
            "value": period["period_minutes"],
            "unit": "min",
            "found": True,
            "source": "tool_computed",
            "status": "computed",
            "requires_confirmation": False,
            "inference_note": note,
            "confidence": 0.95,
        },
        metadata,
    )


def _ensure_element_entries(params: dict) -> None:
    units = {
        "semi_major_axis_km": "km",
        "eccentricity": None,
        "orbit_inclination_deg": "deg",
        "raan_deg": "deg",
        "arg_perigee_deg": "deg",
        "true_anomaly_deg": "deg",
    }
    for key, unit in units.items():
        params.setdefault(key, _missing_entry(unit))


def interpret_orbit_parameters(
    params: dict,
    user_text: Optional[str] = None,
) -> Tuple[dict, Dict[str, Any]]:
    """Infer lightweight orbital parameters and prepare completeness metadata."""

    _ensure_element_entries(params)
    metadata: Dict[str, Any] = {
        "status": "ok",
        "inferred_parameters": [],
        "defaulted_parameters": [],
        "missing_core_elements": [],
        "missing_recommended_elements": [],
        "missing_reasons": {},
        "next_step_suggestions": [],
        "assumptions": [],
        "warnings": [],
        "confidence": 1.0,
        "inference_details": {},
        "element_table": [],
    }

    orbit_entry = params.get("orbit_type", {})
    orbit_type = orbit_entry.get("value") if orbit_entry.get("found") else None
    text_implies_circular = _text_implies_circular_orbit(user_text)
    circular_semantics_active = _is_circular_orbit_type(orbit_type) or (
        text_implies_circular and not _is_elliptical_orbit_type(orbit_type)
    )
    if orbit_type is None and user_text:
        orbit_type = _extract_orbit_type_from_text(user_text)
        if orbit_type:
            params["orbit_type"] = {
                "value": orbit_type,
                "unit": None,
                "found": True,
                "source": "inferred_from_orbit_type",
                "status": "inferred",
                "requires_confirmation": True,
            }
            metadata["inferred_parameters"].append("orbit_type")
            circular_semantics_active = _is_circular_orbit_type(orbit_type) or (
                text_implies_circular and not _is_elliptical_orbit_type(orbit_type)
            )

    if circular_semantics_active:
        _record_orbit_semantics(
            params,
            metadata,
            shape_type="circular orbit",
            source="orbit_type" if _is_circular_orbit_type(orbit_type) else "user_text",
        )

    altitude = params.get("orbit_altitude_km", {})
    if altitude.get("found") and altitude.get("value") is not None:
        semi_major_axis = round(R_EARTH_KM + float(altitude["value"]), 3)
        _set_if_missing(
            params,
            "semi_major_axis_km",
            {
                "value": semi_major_axis,
                "unit": "km",
                "found": True,
                "source": "inferred_from_altitude",
                "status": "inferred",
                "requires_confirmation": False,
                "inference_note": (
                    "Semi-major axis inferred as Earth mean equatorial radius "
                    f"({R_EARTH_KM} km) plus orbit altitude."
                ),
                "confidence": 0.95,
            },
            metadata,
        )
        if float(altitude["value"]) <= 350.0:
            metadata["warnings"].append(
                "Atmospheric drag risk is elevated for very low LEO altitudes "
                f"such as {altitude['value']} km. This MVP does not perform "
                "high-fidelity drag or lifetime propagation."
            )

    if orbit_type == "polar orbit":
        _set_if_missing(
            params,
            "orbit_inclination_deg",
            {
                "value": 90.0,
                "unit": "deg",
                "found": True,
                "source": "inferred_from_orbit_type",
                "status": "inferred",
                "requires_confirmation": True,
                "inference_note": "Polar orbit typically has inclination near 90 deg.",
                "confidence": 0.85,
            },
            metadata,
        )
    elif orbit_type == "SSO":
        if altitude.get("found") and altitude.get("value") is not None:
            inclination, note = _infer_sso_inclination(float(altitude["value"]))
        else:
            inclination = None
            note = (
                "SSO inclination is typically near 97-99 deg for common LEO "
                "altitudes. Provide altitude for a simple J2 estimate."
            )
        _set_if_missing(
            params,
            "orbit_inclination_deg",
            {
                "value": inclination,
                "unit": "deg",
                "found": inclination is not None,
                "source": "inferred_from_orbit_type",
                "status": "inferred" if inclination is not None else "missing",
                "requires_confirmation": True,
                "inference_note": note,
                "confidence": 0.7 if inclination is not None else 0.4,
            },
            metadata,
        )
    elif orbit_type == "GEO":
        _set_if_missing(
            params,
            "orbit_inclination_deg",
            {
                "value": 0.0,
                "unit": "deg",
                "found": True,
                "source": "inferred_from_orbit_type",
                "status": "inferred",
                "requires_confirmation": True,
                "inference_note": "Geostationary orbit inclination is near 0 deg.",
                "confidence": 0.9,
            },
            metadata,
        )
        _set_if_missing(
            params,
            "eccentricity",
            {
                "value": 0.0,
                "unit": None,
                "found": True,
                "source": "inferred_from_orbit_type",
                "status": "inferred",
                "requires_confirmation": True,
                "inference_note": "Geostationary orbit is expected to be near circular.",
                "confidence": 0.9,
            },
            metadata,
        )
    elif circular_semantics_active:
        _set_if_missing(
            params,
            "eccentricity",
            {
                "value": 0.0,
                "unit": None,
                "found": True,
                "source": "inferred_from_orbit_type",
                "status": "inferred",
                "requires_confirmation": True,
                "inference_note": "Circular orbit has eccentricity near 0.",
                "confidence": 0.9,
            },
            metadata,
        )

    _compute_period_if_ready(params, metadata)

    # Angular elements can default to zero for conceptual phasing only.
    for key in DEFAULT_ANGLE_KEYS:
        _set_if_missing(
            params,
            key,
            {
                "value": 0.0,
                "unit": "deg",
                "found": True,
                "source": "default_assumption",
                "status": "default_assumption",
                "requires_confirmation": True,
                "inference_note": (
                    f"{key} defaulted to 0 deg for conceptual analysis. "
                    "User confirmation is required."
                ),
                "confidence": 0.3,
            },
            metadata,
        )
        if params[key].get("source") == "default_assumption":
            metadata["defaulted_parameters"].append(key)

    _apply_completeness_gate(params, metadata)
    metadata["element_table"] = build_orbital_elements_table(params)

    confidences = [
        params[key].get("confidence")
        for key in ORBIT_ELEMENT_KEYS
        if isinstance(params.get(key), dict) and params[key].get("confidence") is not None
    ]
    if confidences:
        metadata["confidence"] = round(sum(confidences) / len(confidences), 2)

    return params, metadata


def _apply_completeness_gate(params: dict, metadata: dict) -> None:
    for key in CORE_ORBIT_ELEMENT_KEYS:
        entry = params.get(key, {})
        if not entry.get("found") or entry.get("value") is None:
            metadata["missing_core_elements"].append(key)

    for key in RECOMMENDED_ORBIT_ELEMENT_KEYS:
        entry = params.get(key, {})
        if not entry.get("found") or entry.get("value") is None:
            metadata["missing_recommended_elements"].append(key)

    altitude = params.get("orbit_altitude_km", {}).get("value")
    orbit_type = params.get("orbit_type", {}).get("value")

    if "orbit_inclination_deg" in metadata["missing_core_elements"]:
        if orbit_type == "LEO" and altitude is not None:
            reason = (
                f"LEO + {altitude} km identifies the altitude class but does "
                "not uniquely determine orbital inclination."
            )
            suggestion = (
                "Please provide inclination_deg, or specify a more specific "
                "orbit type such as polar orbit, SSO, or equatorial orbit."
            )
        else:
            reason = "Orbital inclination is required before downstream orbit analysis."
            suggestion = "Please provide inclination_deg or a more specific orbit type."
        metadata["missing_reasons"]["orbit_inclination_deg"] = reason
        metadata["next_step_suggestions"].append(suggestion)

    if "semi_major_axis_km" in metadata["missing_core_elements"]:
        metadata["missing_reasons"]["semi_major_axis_km"] = (
            "Semi-major axis is required. It can be inferred from altitude for "
            "a circular-altitude style input, or provided directly."
        )
        metadata["next_step_suggestions"].append(
            "Please provide orbit_altitude_km or semi_major_axis_km."
        )

    if "eccentricity" in metadata["missing_recommended_elements"]:
        metadata["missing_reasons"]["eccentricity"] = (
            "Eccentricity is recommended to define orbit shape. It is inferred "
            "only from explicit circular/GEO semantics, not from a generic LEO label."
        )
        metadata["next_step_suggestions"].append(
            "If a near-circular orbit is intended, specify circular orbit or provide eccentricity."
        )

    seen = set()
    metadata["next_step_suggestions"] = [
        item for item in metadata["next_step_suggestions"]
        if not (item in seen or seen.add(item))
    ]
    metadata["status"] = (
        "missing_core_elements"
        if metadata["missing_core_elements"]
        else "complete"
    )


def build_orbital_elements_table(params: dict) -> List[dict]:
    rows = []
    labels = {
        "semi_major_axis_km": "semi_major_axis_km",
        "eccentricity": "eccentricity",
        "orbit_inclination_deg": "inclination_deg",
        "raan_deg": "raan_deg",
        "arg_perigee_deg": "arg_perigee_deg",
        "true_anomaly_deg": "true_anomaly_deg",
    }
    for key in ORBIT_ELEMENT_KEYS:
        entry = params.get(key, _missing_entry("deg" if key.endswith("_deg") else None))
        rows.append({
            "element": labels[key],
            "value": entry.get("value"),
            "unit": entry.get("unit"),
            "source": entry.get("source", "not_found"),
            "status": entry.get("status") or (
                "available" if entry.get("found") and entry.get("value") is not None else "missing"
            ),
            "requires_confirmation": bool(entry.get("requires_confirmation", False)),
        })
    return rows
