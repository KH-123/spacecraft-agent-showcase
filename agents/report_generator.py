"""Markdown report generator for spacecraft conceptual design."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


PARAM_DISPLAY = {
    "orbit_altitude_km": ("轨道高度 (Orbit Altitude)", "km"),
    "payload_mass_kg": ("有效载荷质量 (Payload Mass)", "kg"),
    "power_required_w": ("功率需求 (Power Requirement)", "W"),
    "orbit_period_min": ("轨道周期 (Orbit Period)", "min"),
    "orbit_type": ("轨道类型 (Orbit Type)", ""),
    "orbit_inclination_deg": ("轨道倾角 (Orbit Inclination)", "deg"),
    "mission_lifetime_years": ("任务寿命 (Mission Lifetime)", "years"),
    "ground_resolution_m": ("地面分辨率 (Ground Resolution)", "m"),
}

SOURCE_DISPLAY = {
    "user_provided": "用户提供",
    "llm_extracted": "LLM 提取",
    "llm_extracted_normalized": "LLM 提取并标准化",
    "rules_extracted": "规则提取",
    "rules_fallback": "规则 fallback 提取",
    "llm_inferred": "LLM 推断，需确认",
    "rules_inferred": "规则推断，需确认",
    "user_confirmed_llm_inferred": "用户确认的草案推断",
    "inferred_from_orbit_type": "由轨道类型推断",
    "inferred_from_altitude": "由高度推断",
    "llm_estimated": "LLM 概念估算",
    "requires_external_simulation": "需外部仿真",
    "tool_computed": "工具计算",
    "default_assumption": "默认假设，需确认",
    "not_found": "未提供",
}


def generate_report(
    params: dict,
    missing_params: list,
    task_results: list,
    orbit_metadata: dict | None = None,
    orbit_conflicts: list | None = None,
    mission_context: dict | None = None,
    advisor_report: dict | None = None,
) -> str:
    """Generate a structured Markdown preliminary design report."""

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = [
        "# 航天器总体设计初步报告",
        "## Spacecraft Conceptual Design Preliminary Report",
        "",
        f"**生成时间 (Generated):** {now}",
        "**状态 (Status):** 初步估算 / Preliminary Estimate",
        "",
        "> 本报告仅用于概念设计辅助，不构成最终、认证或飞行合格结论。",
        "",
        "---",
        "",
    ]

    _append_parameter_table(lines, params, "## 1. 任务参数 (Mission Parameters)")
    _append_mission_context(lines, params, mission_context)
    _append_orbit_inference(lines, params, orbit_metadata)
    _append_orbit_conflicts(lines, orbit_conflicts)
    _append_missing_params(lines, missing_params)
    _append_task_results(lines, task_results)
    _append_advisor_report(lines, advisor_report)
    _append_confirmation_items(lines, missing_params)
    _append_recommendations(lines)
    return "\n".join(lines)


def generate_parameter_confirmation_report(
    params: dict,
    missing_params: list,
    validation_results: list,
    orbit_metadata: dict | None = None,
    orbit_conflicts: list | None = None,
    mission_context: dict | None = None,
    advisor_report: dict | None = None,
) -> str:
    """Generate a parameter confirmation report when blocking issues exist."""

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = [
        "# 参数确认请求",
        "## Parameter Confirmation Request",
        "",
        f"**生成时间 (Generated):** {now}",
        "**状态 (Status):** 参数异常或轨道定义不完整，已暂停普通报告生成。",
        "",
        "> 请先确认或修正以下参数，再重新运行参数级设计流程。",
        "",
        "---",
        "",
    ]

    _append_orbital_elements(lines, orbit_metadata)
    _append_missing_core_elements(lines, orbit_metadata)
    _append_orbit_warnings(lines, orbit_metadata)
    _append_orbit_conflicts(lines, orbit_conflicts, heading="## 1c. 轨道一致性冲突")
    _append_parameter_table(lines, params, "## 2. 已提取参数 (Extracted Parameters)")
    _append_validation_results(lines, validation_results)
    _append_missing_params(lines, missing_params, heading="## 5. 缺失参数 (Missing Parameters)")
    lines.extend(
        [
            "## 6. 建议操作 (Suggested Actions)",
            "",
            "1. 修改明显矛盾或超限的输入参数。",
            "2. 如果确实需要超出当前小卫星/LEO MVP 范围，请补充任务背景并使用更适合的分析工具。",
            "3. 补充表中标记为待确认或缺失的关键参数。",
            "",
            "---",
            "*本系统为概念设计辅助工具，不构成飞行合格结论。*",
        ]
    )
    return "\n".join(lines)


def _append_parameter_table(lines: list[str], params: dict, heading: str) -> None:
    lines.extend([heading, "", "| 参数 (Parameter) | 值 (Value) | 单位 (Unit) | 来源 (Source) | 状态 (Status) | 需确认 |", "|---|---|---|---|---|---|"])
    for key, (display_name, default_unit) in PARAM_DISPLAY.items():
        entry = params.get(key, {})
        if entry.get("found") and entry.get("value") is not None:
            value = _format_value(entry.get("value"))
            unit = entry.get("unit") or default_unit
            source = SOURCE_DISPLAY.get(entry.get("source"), entry.get("source", "未知"))
            status = entry.get("status", "available")
            status_display = {
                "user_provided": "已提供",
                "inferred": "已推断",
                "computed": "工具计算",
                "default_assumption": "默认假设",
                "available": "已提供",
            }.get(status, status)
            requires_conf = "是" if entry.get("requires_confirmation") else "否"
        else:
            value = "*待确认 (TBC)*"
            unit = entry.get("unit") or default_unit
            source = "未提供"
            status_display = "缺失"
            requires_conf = "是"
        lines.append(f"| {display_name} | {value} | {unit} | {source} | {status_display} | {requires_conf} |")
    lines.append("")


def _append_mission_context(
    lines: list[str],
    params: dict,
    mission_context: dict | None = None,
) -> None:
    # Try explicit mission_context first, then fall back to legacy locations
    context = mission_context
    if not context:
        context = params.get("_mission_context") or params.get("_extraction_metadata", {}).get("mission_context")
    if not context:
        return

    if not any(value not in (None, "", []) for value in context.values()):
        return

    lines.extend(["### 1a. 任务意图理解 (Mission Intent)", ""])

    # New-style mission_context fields
    mc_fields = [
        ("mission_type", "任务类型", None),
        ("target_region", "目标区域", None),
        ("revisit_time_h", "重访时间", "hours"),
        ("payload_type", "载荷类型", None),
        ("ground_resolution_m", "地面分辨率", "m"),
        ("swath_width_km", "幅宽", "km"),
        ("imaging_frequency", "成像频率", None),
        ("daily_data_volume_GB", "日数据量", "GB"),
        ("downlink_rate_Mbps", "下行速率", "Mbps"),
        ("mission_lifetime_year", "任务寿命", "year"),
        ("pointing_accuracy_deg", "指向精度", "deg"),
    ]
    has_new_style = any(context.get(field) is not None for field, _, _ in mc_fields)

    if has_new_style:
        for field, label, unit in mc_fields:
            value = context.get(field)
            if value is not None:
                suffix = f" {unit}" if unit else ""
                lines.append(f"- **{label}:** {value}{suffix}")
            else:
                lines.append(f"- **{label}:** 未明确")
    else:
        # Legacy fields
        lines.append(f"- **任务目标:** {context.get('mission_objective') or '未明确'}")
        lines.append(f"- **目标区域:** {context.get('target_region') or '未明确'}")
        lines.append(f"- **载荷提示:** {context.get('payload_type_hint') or '未明确'}")
        if context.get("revisit_requirement_hours") is not None:
            lines.append(f"- **重访需求:** {context.get('revisit_requirement_hours')} hours")
        requirements = context.get("performance_requirements", [])
        if requirements:
            lines.append("- **性能需求:**")
            for req in requirements:
                unit = req.get("unit") or ""
                lines.append(f"  - {req.get('name')}: {req.get('value')} {unit}".rstrip())
        notes = context.get("ambiguity_notes", [])
        if notes:
            lines.append("- **歧义/待确认:**")
            for note in notes:
                lines.append(f"  - {note}")
    lines.append("")


def _append_orbit_inference(
    lines: list[str],
    params: dict,
    orbit_metadata: dict | None,
) -> None:
    if not orbit_metadata or not orbit_metadata.get("inferred_parameters"):
        return
    lines.extend(["### 1b. 轨道参数推断 (Orbit Parameter Inference)", ""])
    lines.append(f"**轨道类型:** {params.get('orbit_type', {}).get('value', '未知')}")
    lines.append("")
    lines.append("**推断/计算参数:**")
    for field in orbit_metadata["inferred_parameters"]:
        entry = params.get(field, {})
        value = entry.get("value")
        unit = entry.get("unit") or ""
        note = orbit_metadata.get("inference_details", {}).get(field, "")
        source = SOURCE_DISPLAY.get(entry.get("source"), entry.get("source", "未知"))
        value_text = f"{_format_value(value)} {unit}".strip() if value is not None else "待确认"
        lines.append(f"- **{field}**: {value_text}，来源：{source}")
        if note:
            lines.append(f"  - {note}")
    lines.append(f"- **推断置信度:** {orbit_metadata.get('confidence', 0.0):.0%}")
    lines.append("")


def _append_orbital_elements(lines: list[str], orbit_metadata: dict | None) -> None:
    if not orbit_metadata or not orbit_metadata.get("element_table"):
        return
    lines.extend(["## 1a. 轨道六根数 (Orbital Elements)", ""])
    lines.append("| Element | Value | Unit | Source | Status | Requires Confirmation |")
    lines.append("|---|---:|---|---|---|---|")
    for row in orbit_metadata["element_table"]:
        value = row.get("value")
        value_text = "TBC" if value is None else _format_value(value)
        source = SOURCE_DISPLAY.get(row.get("source"), row.get("source", "未知"))
        lines.append(
            f"| {row.get('element')} | {value_text} | {row.get('unit') or ''} | "
            f"{source} | {row.get('status')} | {row.get('requires_confirmation')} |"
        )
    lines.append("")


def _append_missing_core_elements(lines: list[str], orbit_metadata: dict | None) -> None:
    missing_core = (orbit_metadata or {}).get("missing_core_elements", [])
    if not missing_core:
        return
    lines.extend(["## 1b. 缺失核心轨道参数", ""])
    lines.append("由于轨道定义不完整，普通 downstream 任务执行已跳过。")
    lines.append("")
    missing_reasons = (orbit_metadata or {}).get("missing_reasons", {})
    for field in missing_core:
        lines.append(f"- **{field}**: {missing_reasons.get(field, '该参数是轨道定义所需参数。')}")
    suggestions = (orbit_metadata or {}).get("next_step_suggestions", [])
    if suggestions:
        lines.append("")
        lines.append("**下一步建议:**")
        for suggestion in suggestions:
            lines.append(f"- {suggestion}")
    lines.append("")


def _append_orbit_warnings(lines: list[str], orbit_metadata: dict | None) -> None:
    warnings = (orbit_metadata or {}).get("warnings", [])
    if not warnings:
        return
    lines.extend(["## 1b. 轨道风险提示", ""])
    for warning in warnings:
        lines.append(f"- {warning}")
    lines.append("")


def _append_orbit_conflicts(
    lines: list[str],
    orbit_conflicts: list | None,
    heading: str = "### 1c. 轨道一致性校验 (Orbit Consistency Validation)",
) -> None:
    if not orbit_conflicts:
        return
    lines.extend([heading, ""])
    for conflict in orbit_conflicts:
        data = conflict.to_dict() if hasattr(conflict, "to_dict") else conflict
        lines.append(
            f"- **{str(data.get('level', 'warning')).upper()}** "
            f"{data.get('field')}: {data.get('message')}"
        )
        action = data.get("suggested_user_action")
        if action:
            lines.append(f"  - 建议：{action}")
    lines.append("")


def _append_missing_params(
    lines: list[str],
    missing_params: list,
    heading: str = "## 2. 缺失参数 (Missing Parameters)",
) -> None:
    if not missing_params:
        return
    lines.extend([heading, ""])
    for item in missing_params:
        severity_label = "必需" if item.get("severity") == "required" else "建议"
        lines.append(f"- **{item.get('description')}** [{severity_label}]: 请补充或确认。")
    lines.append("")


def _append_validation_results(lines: list[str], validation_results: list) -> None:
    severe_results = [item for item in validation_results if item.level == "severe"]
    warning_results = [item for item in validation_results if item.level == "warning"]
    if severe_results:
        lines.extend(["## 3. 严重参数异常 (Severe Parameter Errors)", ""])
        for result in severe_results:
            lines.append(f"- **{result.message}**")
        lines.append("")
    if warning_results:
        lines.extend(["## 4. 参数警告 (Parameter Warnings)", ""])
        for result in warning_results:
            lines.append(f"- {result.message}")
        lines.append("")


def _append_task_results(lines: list[str], task_results: list) -> None:
    lines.extend(["## 3. 分析结果 (Analysis Results)", ""])
    for task in task_results:
        if task.get("status") == "skipped":
            continue
        lines.extend([f"### {task.get('name', task.get('task_id', '未命名任务'))}", ""])
        if task.get("status") == "failed":
            lines.append("**状态:** 计算失败")
            for error in task.get("errors", []):
                lines.append(f"- 错误: {error}")
            lines.append("")
            continue
        if task.get("source") == "llm_estimated":
            _append_llm_estimate(lines, task)
            continue
        if task.get("source") == "requires_external_simulation":
            _append_external_simulation_item(lines, task)
            continue
        lines.append("**状态:** 计算完成")
        result = task.get("result")
        if result is None:
            lines.extend(["*无计算结果。*", ""])
            continue
        _append_deterministic_result(lines, task.get("task_id"), result)
        lines.append("")


def _append_deterministic_result(lines: list[str], task_id: str | None, result: dict) -> None:
    if task_id == "orbit_analysis":
        period = result.get("orbit_period", {})
        velocity = result.get("orbital_velocity", {})
        lines.append("#### 轨道周期 (Orbital Period)")
        lines.append(f"- 轨道周期: **{period.get('period_minutes', 'N/A')} min**")
        lines.append(f"- 半长轴: **{period.get('semi_major_axis_km', 'N/A')} km**")
        lines.append("#### 轨道速度 (Orbital Velocity)")
        lines.append(f"- 轨道速度: **{velocity.get('velocity_km_s', 'N/A')} km/s**")
    elif task_id == "mass_budget":
        lines.append("#### 质量预算 (Mass Budget)")
        for key in (
            "payload_mass_kg",
            "bus_mass_kg",
            "margin_mass_kg",
            "propellant_mass_kg",
            "total_dry_mass_kg",
            "total_mass_kg",
        ):
            if key in result:
                lines.append(f"- {key}: **{result[key]} kg**")
        breakdown = result.get("mass_breakdown", {})
        if breakdown:
            lines.append("#### 子系统质量分配")
            for subsystem, mass in breakdown.items():
                lines.append(f"- {subsystem}: **{mass} kg**")
    elif task_id == "solar_array":
        lines.append("#### 太阳能电池阵面积")
        lines.append(f"- 功率需求: **{result.get('power_required_w', 'N/A')} W**")
        lines.append(f"- 估算面积: **{result.get('area_m2', 'N/A')} m^2**")
    elif task_id == "battery":
        lines.append("#### 电池容量")
        lines.append(f"- 功率需求: **{result.get('power_required_w', 'N/A')} W**")
        lines.append(f"- 地影时长: **{result.get('eclipse_hours', 'N/A')} h**")
        lines.append(f"- 估算容量: **{result.get('capacity_ah', 'N/A')} Ah**")
    else:
        for key, value in result.items():
            lines.append(f"- {key}: {value}")

    assumptions = result.get("assumption") or result.get("assumptions") or []
    if assumptions:
        lines.append("#### 假设")
        for assumption in assumptions:
            lines.append(f"- {assumption}")


def _append_llm_estimate(lines: list[str], task: dict) -> None:
    result = task.get("result", {})
    value = result.get("value")
    unit = result.get("unit") or ""
    value_text = f"{value} {unit}".strip() if value is not None else "信息不足，无法给出具体数值"
    lines.append("**状态:** LLM 概念估算，未工程验证")
    lines.append(f"- 估算结果: {value_text}")
    lines.append(f"- 置信度: {result.get('confidence', 0.0):.0%}")
    for title, key in (("假设", "assumptions"), ("不确定性", "uncertainty_notes")):
        items = result.get(key, [])
        if items:
            lines.append(f"#### {title}")
            for item in items:
                lines.append(f"- {item}")
    if result.get("requires_confirmation"):
        lines.append("> 此估算需要用户确认，不能替代 deterministic tools 或工程仿真。")
    lines.append("")


def _append_external_simulation_item(lines: list[str], task: dict) -> None:
    result = task.get("result", {})
    lines.append("**状态:** 需要外部仿真，当前未验证")
    lines.append(f"- 来源: {task.get('source')}")
    lines.append(f"- 验证状态: {result.get('verification_status', 'not_verified')}")
    if result.get("target_region"):
        lines.append(f"- 目标区域: {result.get('target_region')}")
    if result.get("revisit_requirement_hours") is not None:
        lines.append(f"- 重访需求: {result.get('revisit_requirement_hours')} hours")
    for title, key in (("假设/说明", "assumptions"), ("不确定性", "uncertainty_notes")):
        items = result.get(key, [])
        if items:
            lines.append(f"#### {title}")
            for item in items:
                lines.append(f"- {item}")
    lines.append("")


def _append_advisor_report(lines: list[str], advisor_report: dict | None) -> None:
    if not advisor_report:
        return
    lines.extend(["## 3a. 设计建议与风险提示 (Design Advice & Risk)", ""])

    summary = advisor_report.get("design_summary", "")
    if summary:
        lines.append(f"**设计概况:** {summary}")
        lines.append("")

    risks = advisor_report.get("main_risks", [])
    if risks:
        lines.append("**主要风险:**")
        for risk in risks:
            lines.append(f"- {risk}")
        lines.append("")

    param_comments = advisor_report.get("parameter_comments", [])
    if param_comments:
        lines.append("**参数评价:**")
        for comment in param_comments:
            lines.append(f"- {comment}")
        lines.append("")

    suggestions = advisor_report.get("missing_parameter_suggestions", [])
    if suggestions:
        lines.append("**缺失参数建议:**")
        for suggestion in suggestions:
            lines.append(f"- {suggestion}")
        lines.append("")

    steps = advisor_report.get("recommended_next_steps", [])
    if steps:
        lines.append("**推荐下一步:**")
        for step in steps:
            lines.append(f"- {step}")
        lines.append("")

    limitations = advisor_report.get("limitations", [])
    if limitations:
        lines.append("**概念级限制:**")
        for limitation in limitations:
            lines.append(f"- {limitation}")
        lines.append("")

    snippets = advisor_report.get("rag_snippets_used", [])
    if snippets:
        lines.append("**参考知识片段:**")
        for s in snippets:
            lines.append(f"- {s}")
        lines.append("")

    if advisor_report.get("llm_synthesis_used"):
        lines.append("*本建议由 LLM 综合生成。*")
    else:
        lines.append("*本建议基于规则和本地知识库生成，未使用 LLM 综合。*")
    lines.append("")


def _append_confirmation_items(lines: list[str], missing_params: list) -> None:
    lines.extend(["## 4. 风险与待确认项 (Risks & Items to Confirm)", ""])
    if missing_params:
        lines.append("### 待确认参数")
        for item in missing_params:
            lines.append(f"- **{item.get('description')}**")
    else:
        lines.append("- 未发现必需参数缺失。")
    lines.append("")
    lines.append("### 已知限制")
    lines.append("- 所有计算结果均为概念设计阶段初步估算。")
    lines.append("- 当前工具不包含高保真轨道传播、覆盖重访仿真或星座相位优化。")
    lines.append("- LLM 估算项必须标记为概念估算或外部仿真需求，不得视为验证结果。")
    lines.append("")


def _append_recommendations(lines: list[str]) -> None:
    lines.extend(
        [
            "## 5. 后续建议 (Recommendations)",
            "",
            "- 补充缺失的核心轨道参数和任务约束。",
            "- 对覆盖、重访、星座和侧摆策略进行外部仿真。",
            "- 根据具体载荷和平台选型更新质量、电源和热控预算。",
            "",
            "---",
            "*本报告为初步概念设计估算，不构成飞行合格结论。*",
        ]
    )


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)
