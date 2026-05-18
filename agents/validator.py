"""
Python hard guardrails for spacecraft conceptual design parameters.

This layer is deterministic and lightweight. It validates normalized
parameter values against MVP conceptual-design thresholds.
"""

from typing import List, Tuple


GUARDRAIL_DEFS: List[Tuple[str, str, float, float, float, float, float, float]] = [
    (
        "orbit_altitude_km",
        "轨道高度 (Orbit Altitude)",
        400.0, 800.0,
        200.0, 1200.0,
        160.0, 2000.0,
    ),
    (
        "mission_lifetime_years",
        "任务寿命 (Mission Lifetime)",
        1.0, 5.0,
        0.5, 10.0,
        0.0, 15.0,
    ),
    (
        "payload_mass_kg",
        "有效载荷质量 (Payload Mass)",
        5.0, 100.0,
        1.0, 300.0,
        -1.0, 300.0,
    ),
    (
        "power_required_w",
        "载荷功率 (Payload Power)",
        10.0, 300.0,
        1.0, 1000.0,
        -1.0, 1000.0,
    ),
]


class ValidationResult:
    """Result of validating a single parameter."""

    def __init__(
        self,
        param_key: str,
        display_name: str,
        value: float,
        level: str,
        message: str,
    ):
        self.param_key = param_key
        self.display_name = display_name
        self.value = value
        self.level = level
        self.message = message

    def to_dict(self) -> dict:
        return {
            "param_key": self.param_key,
            "display_name": self.display_name,
            "value": self.value,
            "level": self.level,
            "message": self.message,
        }


def validate_parameters(
    params: dict,
    source_filter: set[str] | None = None,
    include_missing: bool = True,
) -> List[ValidationResult]:
    """Validate mission parameters against hard guardrails."""

    results: List[ValidationResult] = []

    for (
        key,
        display_name,
        reasonable_min,
        reasonable_max,
        warning_min,
        warning_max,
        severe_min,
        severe_max,
    ) in GUARDRAIL_DEFS:
        entry = params.get(key, {})
        value = entry.get("value")
        found = entry.get("found", False)
        source = entry.get("source")
        status = entry.get("status")

        if (
            source_filter is not None
            and source not in source_filter
            and (found or status in {"invalid_unit", "missing_unit"})
        ):
            continue

        if status in {"invalid_unit", "missing_unit"}:
            raw_unit = entry.get("raw_unit")
            message = (
                f"{display_name}: 单位 {raw_unit!r} 无法可靠标准化，"
                "请确认数值和单位。"
            )
            results.append(
                ValidationResult(key, display_name, value, "warning", message)
            )
            entry["validation_status"] = "warning"
            params[key] = entry
            continue

        if not found or value is None:
            entry["validation_status"] = "not_validated"
            params[key] = entry
            if not include_missing or source_filter is not None:
                continue
            results.append(
                ValidationResult(
                    key,
                    display_name,
                    value,
                    "pass",
                    f"{display_name}: 未提供，跳过校验。",
                )
            )
            continue

        if value < severe_min or value > severe_max:
            message = _severe_message(
                key,
                display_name,
                value,
                severe_min,
                severe_max,
            )
            results.append(ValidationResult(key, display_name, value, "severe", message))
            entry["validation_status"] = "severe"
            params[key] = entry
            continue

        if value < warning_min or value > warning_max:
            message = (
                f"{display_name} = {value}，超出建议范围 "
                f"[{warning_min}, {warning_max}]，但尚未达到 severe 阈值。"
            )
            results.append(ValidationResult(key, display_name, value, "warning", message))
            entry["validation_status"] = "warning"
            params[key] = entry
            continue

        message = (
            f"{display_name} = {value}，位于概念设计合理范围 "
            f"[{reasonable_min}, {reasonable_max}]。"
        )
        results.append(ValidationResult(key, display_name, value, "pass", message))
        entry["validation_status"] = "pass"
        params[key] = entry

    return results


def _severe_message(
    key: str,
    display_name: str,
    value: float,
    severe_min: float,
    severe_max: float,
) -> str:
    if key == "payload_mass_kg" and value > 300.0:
        return (
            f"{display_name} = {value} kg > 300 kg，超出小卫星概念设计范围，"
            "建议重新评估任务规模。"
        )
    if key == "power_required_w" and value > 1000.0:
        return (
            f"{display_name} = {value} W > 1000 W，超出小卫星概念设计范围，"
            "建议重新评估载荷和平台功耗。"
        )
    if key == "orbit_altitude_km" and value < 160.0:
        return (
            f"{display_name} = {value} km < 160 km，轨道过低，"
            "大气阻力风险极高，不适合当前概念工具继续分析。"
        )
    if key == "orbit_altitude_km" and value > 2000.0:
        return (
            f"{display_name} = {value} km > 2000 km，超出当前 LEO 小卫星工具范围，"
            "请确认轨道类型或使用更适合的分析工具。"
        )
    if key == "mission_lifetime_years" and value <= 0:
        return f"{display_name} = {value} years，任务寿命必须大于 0。"
    if key == "mission_lifetime_years" and value > 15.0:
        return (
            f"{display_name} = {value} years > 15 years，超出典型小卫星寿命范围。"
        )
    return (
        f"{display_name} = {value}，超出 severe 阈值 "
        f"[{severe_min}, {severe_max}]。"
    )


def has_severe_errors(validation_results: List[ValidationResult]) -> bool:
    """Check if any validation result is severe."""

    return any(r.level == "severe" for r in validation_results)


def get_warnings(validation_results: List[ValidationResult]) -> List[ValidationResult]:
    """Return all warning-level validation results."""

    return [r for r in validation_results if r.level == "warning"]
