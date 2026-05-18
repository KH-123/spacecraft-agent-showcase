"""Candidate design draft generation for mission-level mode.

Drafts are concept-level suggestions. They are never tool-computed or
flight-qualified results. A draft only enters the deterministic parameter
workflow after the user explicitly adopts it.
"""

from __future__ import annotations

from typing import Any

from agents.normalizer import build_not_found_params


CONFIRMED_DRAFT_SOURCE = "user_confirmed_llm_inferred"


def generate_candidate_design_drafts(
    interpretation: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate 2-3 conceptual candidate parameter drafts."""

    payload_hint = interpretation.get("payload_type_hint") or "remote_sensing_payload_to_be_confirmed"
    missing_constraints = list(interpretation.get("missing_design_drivers", []))
    confidence = _base_confidence(interpretation)
    lifetime = interpretation.get("mission_lifetime_years") or 3.0
    ground_resolution = interpretation.get("spatial_resolution_m")

    return [
        _make_draft(
            draft_id="single_sso_baseline",
            draft_name="单星 SSO 基线草案",
            design_rationale=(
                "适合作为区域遥感任务的保守起点；太阳同步轨道便于获得相近地方时成像条件。"
            ),
            orbit_type="SSO",
            altitude_km=550.0,
            inclination_deg=97.6,
            payload_hint=payload_hint,
            payload_mass_kg=_payload_mass_hint(payload_hint, baseline=35.0),
            power_required_w=_power_hint(payload_hint, baseline=140.0),
            mission_lifetime_years=lifetime,
            ground_resolution_m=ground_resolution,
            key_assumptions=[
                "近圆 LEO/SSO 作为概念设计起点，偏心率暂按 0.0。",
                "重访能力尚未由覆盖仿真验证，单星可能无法满足很短重访需求。",
                "载荷质量和功耗为概念级占位，需要用户按传感器方案确认。",
            ],
            missing_constraints=missing_constraints,
            confidence=confidence,
            verification_status="conceptual_draft_not_verified",
        ),
        _make_draft(
            draft_id="regional_inclined_leo",
            draft_name="倾斜 LEO 区域覆盖草案",
            design_rationale=(
                "用于探索非太阳同步、面向区域覆盖的低轨方案；可能降低部分任务复杂度，"
                "但成像光照条件需要另行权衡。"
            ),
            orbit_type="LEO",
            altitude_km=500.0,
            inclination_deg=45.0,
            payload_hint=payload_hint,
            payload_mass_kg=_payload_mass_hint(payload_hint, baseline=30.0),
            power_required_w=_power_hint(payload_hint, baseline=120.0),
            mission_lifetime_years=lifetime,
            ground_resolution_m=ground_resolution,
            key_assumptions=[
                "倾角 45 deg 是区域覆盖权衡占位值，不代表已针对目标纬度优化。",
                "近圆轨道，偏心率暂按 0.0。",
                "覆盖、重访和侧摆收益需要外部覆盖仿真确认。",
            ],
            missing_constraints=missing_constraints,
            confidence=max(0.2, confidence - 0.08),
            verification_status="conceptual_draft_not_verified",
        ),
        _make_draft(
            draft_id="small_constellation_sso",
            draft_name="小星座 SSO 草案",
            design_rationale=(
                "用于应对较短重访需求；当前系统只对代表性单星做质量、电源和轨道工具计算，"
                "星座覆盖仍需外部仿真。"
            ),
            orbit_type="SSO",
            altitude_km=600.0,
            inclination_deg=97.8,
            payload_hint=payload_hint,
            payload_mass_kg=_payload_mass_hint(payload_hint, baseline=28.0),
            power_required_w=_power_hint(payload_hint, baseline=130.0),
            mission_lifetime_years=lifetime,
            ground_resolution_m=ground_resolution,
            key_assumptions=[
                "按 2-4 颗同类小卫星进行概念级讨论，具体星数未验证。",
                "每颗卫星采用近圆 SSO，偏心率暂按 0.0。",
                "重访、覆盖间隔和地面站调度必须通过外部覆盖仿真/任务分析确认。",
            ],
            missing_constraints=missing_constraints,
            confidence=max(0.2, confidence - 0.03),
            verification_status="requires_external_simulation",
            constellation_size_candidate="2-4 satellites",
        ),
    ]


def build_params_from_confirmed_draft(
    draft: dict[str, Any],
    interpretation: dict[str, Any],
) -> dict[str, Any]:
    """Convert a user-adopted draft into parameter-flow params."""

    params = build_not_found_params()
    assumptions = list(draft.get("key_assumptions", []))
    confidence = float(draft.get("confidence", 0.0))

    field_units = {
        "orbit_type": None,
        "orbit_altitude_km": "km",
        "orbit_inclination_deg": "deg",
        "eccentricity": None,
        "payload_mass_kg": "kg",
        "power_required_w": "W",
        "mission_lifetime_years": "years",
        "ground_resolution_m": "m",
    }
    draft_params = draft.get("parameter_values", {})
    for key, unit in field_units.items():
        value = draft_params.get(key)
        if value is None:
            continue
        params[key] = {
            "value": value,
            "unit": unit,
            "found": True,
            "source": CONFIRMED_DRAFT_SOURCE,
            "status": "user_confirmed",
            "confidence": confidence,
            "assumptions": assumptions,
            "requires_confirmation": False,
        }

    mission_context = {
        "input_type": interpretation.get("input_type"),
        "mission_objective": interpretation.get("mission_objective"),
        "target_region": interpretation.get("target_region"),
        "revisit_requirement_hours": interpretation.get("revisit_requirement_hours"),
        "payload_type_hint": interpretation.get("payload_type_hint"),
        "performance_requirements": interpretation.get("performance_requirements", []),
        "missing_params": interpretation.get("missing_design_drivers", []),
        "missing_design_drivers": interpretation.get("missing_design_drivers", []),
        "ambiguity_notes": interpretation.get("ambiguity_notes", []),
    }
    params["_mission_context"] = mission_context
    params["_draft_metadata"] = {
        "draft_id": draft.get("draft_id"),
        "draft_name": draft.get("draft_name"),
        "verification_status": draft.get("verification_status"),
        "requires_external_simulation": _draft_requires_external_simulation(
            draft, interpretation
        ),
        "source": CONFIRMED_DRAFT_SOURCE,
        "assumptions": assumptions,
    }
    params["_extraction_metadata"] = {
        "extraction_mode": "mission_draft_confirmed",
        "llm_status": "not_used_for_confirmed_draft",
        "fallback_reason": None,
        "normalization_source": "confirmed_mission_draft",
        "llm_raw_response": None,
        "llm_parsed_json": None,
        "explicit_params": _explicit_params_snapshot(params),
        "normalized_params": None,
        "mission_context": mission_context,
        "llm_enabled": False,
        "llm_api_key_present": False,
        "llm_base_url": None,
        "llm_model": None,
        "llm_timeout_seconds": None,
    }
    return params


def build_external_simulation_placeholders(
    interpretation: dict[str, Any],
    draft: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return not-verified placeholders for coverage/revisit-style needs."""

    needs_revisit = interpretation.get("revisit_requirement_hours") is not None
    needs_constellation = draft.get("constellation_size_candidate") is not None
    if not (needs_revisit or needs_constellation):
        return []

    target = interpretation.get("target_region") or "target region not specified"
    revisit = interpretation.get("revisit_requirement_hours")
    return [
        {
            "task_id": "coverage_revisit_external_simulation",
            "name": "覆盖/重访能力外部仿真需求",
            "status": "completed",
            "source": "requires_external_simulation",
            "result": {
                "value": None,
                "unit": None,
                "confidence": 0.0,
                "target_region": target,
                "revisit_requirement_hours": revisit,
                "verification_status": "not_verified",
                "assumptions": [
                    "当前 deterministic tools 不包含覆盖、重访或星座几何仿真。",
                    "候选草案只提供概念级参数入口，不验证覆盖率或重访时间。",
                ],
                "uncertainty_notes": [
                    "需要轨道传播、目标区域几何、传感器幅宽、侧摆策略和星座相位信息。",
                ],
                "requires_confirmation": True,
            },
        }
    ]


def _make_draft(
    *,
    draft_id: str,
    draft_name: str,
    design_rationale: str,
    orbit_type: str,
    altitude_km: float,
    inclination_deg: float,
    payload_hint: str,
    payload_mass_kg: float,
    power_required_w: float,
    mission_lifetime_years: float,
    ground_resolution_m: float | None,
    key_assumptions: list[str],
    missing_constraints: list[str],
    confidence: float,
    verification_status: str,
    constellation_size_candidate: str | None = None,
) -> dict[str, Any]:
    parameter_values = {
        "orbit_type": orbit_type,
        "orbit_altitude_km": altitude_km,
        "orbit_inclination_deg": inclination_deg,
        "eccentricity": 0.0,
        "payload_mass_kg": payload_mass_kg,
        "power_required_w": power_required_w,
        "mission_lifetime_years": mission_lifetime_years,
    }
    if ground_resolution_m is not None:
        parameter_values["ground_resolution_m"] = ground_resolution_m

    draft = {
        "draft_id": draft_id,
        "draft_name": draft_name,
        "design_rationale": design_rationale,
        "orbit_type_candidate": orbit_type,
        "altitude_range_or_value": f"{altitude_km:g} km",
        "inclination_hint_or_range": f"{inclination_deg:g} deg conceptual placeholder",
        "payload_type_hint": payload_hint,
        "key_assumptions": key_assumptions,
        "missing_constraints": missing_constraints,
        "confidence": round(confidence, 2),
        "requires_confirmation": True,
        "verification_status": verification_status,
        "parameter_values": parameter_values,
        "source": "llm_inferred",
    }
    if constellation_size_candidate:
        draft["constellation_size_candidate"] = constellation_size_candidate
    return draft


def _payload_mass_hint(payload_hint: str, baseline: float) -> float:
    lower = payload_hint.lower()
    if "sar" in lower:
        return max(baseline, 80.0)
    if "hyperspectral" in lower:
        return max(baseline, 55.0)
    if "thermal" in lower:
        return max(baseline, 45.0)
    return baseline


def _power_hint(payload_hint: str, baseline: float) -> float:
    lower = payload_hint.lower()
    if "sar" in lower:
        return max(baseline, 350.0)
    if "hyperspectral" in lower:
        return max(baseline, 220.0)
    if "thermal" in lower:
        return max(baseline, 180.0)
    return baseline


def _base_confidence(interpretation: dict[str, Any]) -> float:
    known_keys = [
        "mission_objective",
        "target_region",
        "revisit_requirement_hours",
        "sensor_type",
        "spatial_resolution_m",
        "swath_width_km",
        "mission_lifetime_years",
        "preferred_orbit_type",
    ]
    known_count = sum(1 for key in known_keys if interpretation.get(key) not in (None, "", []))
    return min(0.78, 0.42 + known_count * 0.04)


def _draft_requires_external_simulation(
    draft: dict[str, Any],
    interpretation: dict[str, Any],
) -> bool:
    return (
        draft.get("verification_status") == "requires_external_simulation"
        or interpretation.get("revisit_requirement_hours") is not None
    )


def _explicit_params_snapshot(params: dict[str, Any]) -> dict[str, Any]:
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
