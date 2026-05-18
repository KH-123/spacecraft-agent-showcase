"""
Task planner for spacecraft conceptual design.

The planner runs deterministic tools where available. Unsupported requests
may be passed to the concept-level LLM estimator, but those estimates never
replace deterministic tool results.
"""

from typing import Any, Dict, List, Optional

from agents.llm_estimator import estimate_conceptually
from tools.mass import mass_budget
from tools.orbit import orbit_period, orbital_velocity
from tools.power import battery_capacity, solar_array_area


def plan_analysis_tasks(params: dict) -> list:
    """Decompose normalized parameters into deterministic analysis tasks."""

    return [
        {
            "task_id": "orbit_analysis",
            "name": "轨道分析 (Orbit Analysis)",
            "description": "计算轨道周期和轨道速度",
            "depends_on": [],
            "required_params": ["orbit_altitude_km"],
            "status": "pending",
        },
        {
            "task_id": "mass_budget",
            "name": "质量预算估算 (Mass Budget Estimation)",
            "description": "估算航天器总质量和子系统质量分配",
            "depends_on": [],
            "required_params": ["payload_mass_kg"],
            "status": "pending",
        },
        {
            "task_id": "solar_array",
            "name": "太阳能电池阵面积估算 (Solar Array Sizing)",
            "description": "估算满足功率需求所需的太阳能电池阵面积",
            "depends_on": ["orbit_analysis"],
            "required_params": ["power_required_w"],
            "status": "pending",
        },
        {
            "task_id": "battery",
            "name": "电池容量估算 (Battery Capacity Estimation)",
            "description": "估算地影期间所需的电池容量",
            "depends_on": ["orbit_analysis"],
            "required_params": ["power_required_w"],
            "status": "pending",
        },
    ]


def execute_task(task: dict, params: dict) -> dict:
    """Execute one deterministic analysis task."""

    result = {
        "task_id": task["task_id"],
        "name": task["name"],
        "status": "completed",
        "result": None,
        "errors": [],
    }

    try:
        if task["task_id"] == "orbit_analysis":
            altitude = params.get("orbit_altitude_km", {}).get("value")
            if altitude is None:
                raise ValueError("缺少轨道高度参数 (orbit_altitude_km).")
            result["result"] = {
                "orbit_period": orbit_period(altitude),
                "orbital_velocity": orbital_velocity(altitude),
            }

        elif task["task_id"] == "mass_budget":
            payload_mass = params.get("payload_mass_kg", {}).get("value")
            if payload_mass is None:
                raise ValueError("缺少有效载荷质量参数 (payload_mass_kg).")
            orbit_type = _mass_budget_orbit_type(params)
            result["result"] = mass_budget(payload_mass, orbit_type=orbit_type)

        elif task["task_id"] == "solar_array":
            power = params.get("power_required_w", {}).get("value")
            if power is None:
                raise ValueError("缺少功率需求参数 (power_required_w).")
            result["result"] = solar_array_area(power)

        elif task["task_id"] == "battery":
            power = params.get("power_required_w", {}).get("value")
            if power is None:
                raise ValueError("缺少功率需求参数 (power_required_w).")
            eclipse_hours = 35.0 / 60.0
            result["result"] = battery_capacity(power, eclipse_hours)

        else:
            result["status"] = "failed"
            result["errors"].append(f"未知任务: {task['task_id']}")

    except Exception as exc:
        result["status"] = "failed"
        result["errors"].append(str(exc))

    return result


def _mass_budget_orbit_type(params: dict) -> str:
    """Choose a supported orbit class for the mass budget tool without editing params."""

    orbit_type = params.get("orbit_type", {}).get("value") or "LEO"
    if orbit_type in {"LEO", "SSO", "GEO"}:
        return orbit_type

    altitude = params.get("orbit_altitude_km", {}).get("value")
    if altitude is not None and float(altitude) <= 2000.0:
        return "LEO"
    return "LEO"


def execute_all_tasks(
    params: dict,
    extra_requests: Optional[List[Dict[str, Any]]] = None,
    tool_feedback_rounds: int = 1,
) -> list:
    """Execute all deterministic tasks in dependency order."""

    tasks = plan_analysis_tasks(params)
    results = []

    for task in tasks:
        deps_met = True
        for dep_id in task["depends_on"]:
            dep_result = next((r for r in results if r["task_id"] == dep_id), None)
            if dep_result is None or dep_result["status"] != "completed":
                deps_met = False
                break

        if deps_met:
            results.append(execute_task(task, params))
        else:
            results.append(
                {
                    "task_id": task["task_id"],
                    "name": task["name"],
                    "status": "skipped",
                    "result": None,
                    "errors": ["依赖任务未完成 (dependency not satisfied)."],
                }
            )

    failed_tool_results = [
        result for result in results
        if result.get("status") == "failed"
    ]
    if tool_feedback_rounds > 0 and failed_tool_results:
        extra_requests = list(extra_requests or [])
        for result in failed_tool_results:
            extra_requests.append(
                {
                    "task_id": f"{result['task_id']}_failure_feedback",
                    "name": f"{result.get('name', result['task_id'])}失败原因建议",
                    "description": (
                        "A deterministic tool failed. Provide concept-level "
                        "parameter correction suggestions only; do not replace "
                        f"the tool result. Errors: {result.get('errors', [])}"
                    ),
                }
            )

    if extra_requests:
        available_tools = [
            "orbit_period",
            "orbital_velocity",
            "mass_budget",
            "solar_array_area",
            "battery_capacity",
        ]
        for request in extra_requests:
            results.append(estimate_conceptually(request, params, available_tools))

    return results
