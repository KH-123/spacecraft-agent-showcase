"""
RAG-enhanced LLM design advisor for spacecraft conceptual design.

This module is a **read-only** advisor layer that runs **after** the
deterministic design chain (extraction → normalization → orbit inference →
consistency checks → tools).  It may synthesise retrieved knowledge into
design advice, but must never modify parameters, override tool results, or
decide whether execution is allowed.

It first retrieves local Markdown knowledge, then may ask an OpenAI-compatible
LLM to synthesize that knowledge with the current design-state snapshot into an
``advisor_report``. The LLM synthesis step is optional and failure-tolerant.

The advisor can be called with or without an LLM client.  When no LLM client
is provided or the call fails, it falls back to returning retrieval-only /
rule-based Chinese advice derived from the current design state and any
available RAG snippets.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI

from agents.llm_extractor import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    parse_llm_json,
)
from agents.rag_retriever import retrieve

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def generate_design_advice(
    advisor_input: Dict[str, Any],
    llm_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Generate conceptual design advice based on the current design state.

    Parameters
    ----------
    advisor_input : dict
        Read-only snapshot of the current design state.  Expected keys::

            {
                "report_status": "...",          # optional current run status
                "raw_input_history": [...],       # optional session input history
                "current_round_input": "...",     # optional latest supplement text
                "explicit_parameters": {...},     # optional explicit-only snapshot
                "normalized_parameters": {...},   # alias for normalized_params
                "normalized_params": {...},       # the full params dict
                "mission_context": {...},         # from extract_mission_context()
                "inferred_parameters": [...],     # optional inferred fields
                "default_assumptions": [...],     # list of defaulted params
                "missing_parameters": [...],      # alias for missing_params
                "missing_params": [...],          # from identify_missing_parameters()
                "consistency_issues": [...],      # orbit consistency conflicts
                "validation_results": [...],      # hard-guardrail results
                "tool_results": [...],            # alias for task_results
                "task_results": [...],            # deterministic tool results
                "orbit_metadata": {...},          # orbit inference metadata
                "raw_user_input": "...",          # original user text
                "core_gate_passed": true/false,   # optional core orbit gate flag
            }

    llm_client : Any or None
        An optional OpenAI-compatible client instance. When omitted, the
        advisor tries to create one from ``LLM_API_KEY`` / ``LLM_BASE_URL``.
        If no client is available or the call fails, the advisor returns
        retrieval-only / rule-based Chinese advice.

    Returns
    -------
    dict
        An ``advisor_report`` with the following structure::

            {
                "design_summary": "...",
                "main_risks": [],
                "parameter_comments": [],
                "missing_parameter_suggestions": [],
                "recommended_next_steps": [],
                "next_actions": [],
                "limitations": [],
                "rag_snippets_used": [],
                "rag_references": [],
                "llm_synthesis_used": False,
            }

        All fields are safe to display in the UI.  The report is always
        returned — even when no knowledge is found or the LLM call fails.
    """
    report = _empty_report()

    # 1. Build a query from the available context
    query = _build_query(advisor_input)
    if not query:
        logger.info("design_advisor: empty query, returning empty report")
        return report

    # 2. Retrieve relevant knowledge snippets
    retrieved = retrieve(query, max_snippets=4, min_score=1)
    combined = _combine_retrieved_snippets(retrieved)
    if retrieved:
        report["rag_snippets_used"] = _extract_snippet_previews(combined)
        report["rag_references"] = _build_references(retrieved)

    fallback_actions = _generate_next_actions(advisor_input)

    # 3. If an LLM client is available, try to synthesise a structured report.
    # Retrieval happens first; snippets are read-only review context and never
    # write back into normalized parameters.
    active_llm_client = llm_client or _get_optional_llm_client()
    if active_llm_client is not None and combined:
        try:
            synthesis = _synthesise_with_llm(advisor_input, combined, active_llm_client)
            if synthesis:
                report.update(synthesis)
                if not report.get("next_actions"):
                    report["next_actions"] = fallback_actions
                report["llm_synthesis_used"] = True
                return report
        except Exception as exc:
            logger.warning("design_advisor: LLM synthesis failed, falling back: %s", exc)

    # 4. Fallback: generate rule-based Chinese advice
    _fill_rule_based_advice(report, advisor_input, combined)
    report["next_actions"] = fallback_actions
    return report


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _empty_report() -> Dict[str, Any]:
    return {
        "design_summary": "",
        "main_risks": [],
        "parameter_comments": [],
        "missing_parameter_suggestions": [],
        "recommended_next_steps": [],
        "next_actions": [],
        "limitations": [],
        "rag_snippets_used": [],
        "rag_references": [],
        "llm_synthesis_used": False,
    }


def _get_optional_llm_client() -> Optional[OpenAI]:
    """Create an OpenAI-compatible client when advisor LLM synthesis is configured."""
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        return None
    try:
        return OpenAI(
            api_key=api_key,
            base_url=os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL),
        )
    except Exception as exc:
        logger.warning("design_advisor: cannot create LLM client, falling back: %s", exc)
        return None


def _build_query(advisor_input: Dict[str, Any]) -> str:
    """Build a concise retrieval query from the design state."""
    parts: List[str] = ["spacecraft conceptual design"]

    params = _params(advisor_input)
    orbit_meta = advisor_input.get("orbit_metadata", {})
    orbit_type = params.get("orbit_type", {}).get("value")
    if orbit_type:
        parts.append(str(orbit_type))

    ctx = advisor_input.get("mission_context", {})
    payload_type = ctx.get("payload_type")
    if payload_type:
        parts.append(str(payload_type))
    mission_type = ctx.get("mission_type")
    if mission_type:
        parts.append(str(mission_type))

    missing = _missing_params(advisor_input)
    if missing:
        descriptions = [m.get("description", "") for m in missing if m.get("description")]
        if descriptions:
            parts.append("missing: " + ", ".join(descriptions))

    issues = advisor_input.get("consistency_issues", [])
    if issues:
        fields = set()
        for issue in issues:
            data = _item_to_dict(issue)
            f = data.get("field")
            if f:
                fields.add(str(f))
        if fields:
            parts.append("conflict: " + ", ".join(sorted(fields)))

    if _inclination_missing(params, orbit_meta, missing):
        parts.append("orbit inclination coverage revisit")

    altitude = _entry_value(params, "orbit_altitude_km")
    altitude_value = _safe_float(altitude)
    if altitude_value is not None and altitude_value <= 350:
        parts.append("low LEO drag lifetime orbit maintenance")

    payload_text = _mission_payload_text(ctx)
    if _is_remote_sensing_context(ctx, advisor_input):
        parts.append("remote sensing payload resolution swath data volume")
    if any(term in payload_text for term in ("optical", "multispectral", "hyperspectral")):
        parts.append("optical remote sensing payload resolution swath data volume")
    if "sar" in payload_text:
        parts.append("SAR power data thermal")

    if ctx.get("revisit_time_h") is not None:
        parts.append("revisit swath pointing constellation")

    if _missing_context_or_param(ctx, params, "daily_data_volume_GB") or _missing_context_or_param(ctx, params, "downlink_rate_Mbps"):
        parts.append("communication data downlink remote sensing")

    if _defaulted_orbit_angles(advisor_input):
        parts.append("RAAN argument of perigee true anomaly confirmation")

    return " ".join(_dedupe_strings(parts))


def _extract_snippet_previews(combined: str) -> List[str]:
    """Extract short source + snippet previews from the combined snippet string."""
    previews: List[str] = []
    current_source = ""
    current_lines: List[str] = []

    def flush() -> None:
        if not current_source:
            return
        text = " ".join(line.strip() for line in current_lines if line.strip())
        if text:
            previews.append(f"{current_source}: {text[:220]}")
        else:
            previews.append(current_source)

    for line in combined.split("\n"):
        if line.startswith("--- "):
            flush()
            current_source = line[4:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    flush()
    return previews[:5]


def _line_ref(item: Dict[str, Any]) -> str:
    start = item.get("start_line")
    end = item.get("end_line")
    if not start:
        return ""
    if end and end != start:
        return f"L{start}-L{end}"
    return f"L{start}"


def _combine_retrieved_snippets(results: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for item in results or []:
        line_ref = _line_ref(item)
        source = item.get("source_file", "")
        heading = item.get("heading", "")
        ref = f"{source}:{line_ref}" if line_ref else source
        parts.append(f"--- {ref} - {heading}")
        parts.append(str(item.get("snippet", "")))
    return "\n\n".join(parts)


def _build_references(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    references: List[Dict[str, Any]] = []
    for item in results or []:
        references.append(
            {
                "source_file": item.get("source_file", ""),
                "heading": item.get("heading", ""),
                "start_line": item.get("start_line"),
                "end_line": item.get("end_line"),
                "line_ref": _line_ref(item),
                "short_snippet": item.get("short_snippet") or str(item.get("snippet", ""))[:180],
                "score": item.get("score", 0),
            }
        )
    return references[:5]


def _item_to_dict(item: Any) -> dict[str, Any]:
    if hasattr(item, "to_dict"):
        return item.to_dict()
    if isinstance(item, dict):
        return item
    return {"value": str(item)}


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_risk_hints(combined: str) -> List[str]:
    """Heuristically extract sentences that look like risk descriptions."""
    risks: List[str] = []
    for line in combined.split("\n"):
        lower = line.lower().strip()
        if any(kw in lower for kw in ("risk", "caution", "注意", "风险", "warning", "限制")):
            risks.append(line[:200])
    return risks[:5]


def _params(advisor_input: Dict[str, Any]) -> Dict[str, Any]:
    return advisor_input.get("normalized_parameters") or advisor_input.get("normalized_params") or {}


def _missing_params(advisor_input: Dict[str, Any]) -> List[Dict[str, Any]]:
    return advisor_input.get("missing_parameters") or advisor_input.get("missing_params") or []


def _tool_results(advisor_input: Dict[str, Any]) -> List[Dict[str, Any]]:
    return advisor_input.get("tool_results") or advisor_input.get("task_results") or []


def _entry(params: Dict[str, Any], *keys: str) -> Dict[str, Any]:
    for key in keys:
        item = params.get(key)
        if isinstance(item, dict):
            return item
    return {}


def _entry_found(params: Dict[str, Any], *keys: str) -> bool:
    item = _entry(params, *keys)
    return bool(item.get("found")) and item.get("value") is not None


def _entry_value(params: Dict[str, Any], *keys: str) -> Any:
    item = _entry(params, *keys)
    if item.get("found") and item.get("value") is not None:
        return item.get("value")
    return None


def _dedupe_strings(items: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        if not item:
            continue
        normalized = item.strip()
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _mission_payload_text(ctx: Dict[str, Any]) -> str:
    return " ".join(
        str(value).lower()
        for value in (
            ctx.get("mission_type"),
            ctx.get("payload_type"),
            ctx.get("imaging_frequency"),
        )
        if value not in (None, "", [])
    )


def _raw_text(advisor_input: Dict[str, Any]) -> str:
    history = advisor_input.get("raw_input_history") or []
    if isinstance(history, list) and history:
        history_text = "\n".join(str(item) for item in history if item)
    else:
        history_text = ""
    return "\n".join(
        part
        for part in (
            str(advisor_input.get("raw_user_input") or ""),
            history_text,
            str(advisor_input.get("current_round_input") or ""),
        )
        if part
    )


def _is_remote_sensing_context(ctx: Dict[str, Any], advisor_input: Dict[str, Any]) -> bool:
    text = f"{_mission_payload_text(ctx)} {_raw_text(advisor_input).lower()}"
    terms = (
        "remote_sensing",
        "remote sensing",
        "earth observation",
        "optical",
        "multispectral",
        "hyperspectral",
        "sar",
        "遥感",
        "光学",
        "多光谱",
        "高光谱",
        "雷达",
        "观测",
    )
    return any(term in text for term in terms)


def _missing_context_or_param(
    ctx: Dict[str, Any],
    params: Dict[str, Any],
    field: str,
    *aliases: str,
) -> bool:
    if ctx.get(field) not in (None, "", []):
        return False
    return not _entry_found(params, field, *aliases)


def _inclination_missing(
    params: Dict[str, Any],
    orbit_meta: Dict[str, Any] | None,
    missing: List[Dict[str, Any]] | None,
) -> bool:
    if _entry_found(params, "orbit_inclination_deg", "inclination_deg"):
        return False

    for row in (orbit_meta or {}).get("element_table", []):
        if row.get("element") in {"inclination_deg", "orbit_inclination_deg"} and row.get("value") is not None:
            return False

    missing_core = set((orbit_meta or {}).get("missing_core_elements", []))
    if missing_core.intersection({"orbit_inclination_deg", "inclination_deg"}):
        return True

    for item in missing or []:
        text = f"{item.get('parameter', '')} {item.get('description', '')}".lower()
        if "inclination" in text or "倾角" in text:
            return True

    return True


def _defaulted_orbit_angles(advisor_input: Dict[str, Any]) -> List[str]:
    angle_fields = {"raan_deg", "arg_perigee_deg", "true_anomaly_deg"}
    fields: List[str] = []
    for item in advisor_input.get("default_assumptions") or []:
        if isinstance(item, dict):
            field = item.get("field")
        else:
            field = str(item)
        if field in angle_fields:
            fields.append(field)

    orbit_meta = advisor_input.get("orbit_metadata") or {}
    for field in orbit_meta.get("defaulted_parameters", []):
        if field in angle_fields:
            fields.append(field)

    params = _params(advisor_input)
    for field in angle_fields:
        entry = params.get(field, {})
        if isinstance(entry, dict) and entry.get("source") == "default_assumption":
            fields.append(field)

    return _dedupe_strings(fields)


def _has_circular_nonzero_eccentricity(
    advisor_input: Dict[str, Any],
    params: Dict[str, Any],
    issues: List[Any],
) -> bool:
    text = _raw_text(advisor_input).lower()
    circular_text = any(term in text for term in ("circular", "圆轨道", "圆形轨道", "近圆"))
    ecc = _safe_float(_entry_value(params, "eccentricity"))
    if circular_text and ecc is not None and abs(ecc) > 1e-6:
        return True

    for issue in issues:
        data = _item_to_dict(issue)
        issue_text = f"{data.get('field', '')} {data.get('message', '')} {data.get('suggested_user_action', '')}".lower()
        if data.get("level") == "severe" and (
            ("circular" in issue_text and "eccentric" in issue_text)
            or ("圆" in issue_text and "偏心" in issue_text)
        ):
            return True
    return False


def _looks_like_task_goal(advisor_input: Dict[str, Any], params: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
    engineering_fields = (
        "orbit_type",
        "orbit_altitude_km",
        "semi_major_axis_km",
        "eccentricity",
        "orbit_inclination_deg",
        "inclination_deg",
        "payload_mass_kg",
        "power_required_w",
        "payload_power_W",
    )
    has_engineering = any(_entry_found(params, field) for field in engineering_fields)
    if has_engineering:
        return False

    has_context = any(ctx.get(key) not in (None, "", []) for key in (
        "mission_type",
        "target_region",
        "revisit_time_h",
        "payload_type",
    ))
    text = _raw_text(advisor_input).lower()
    goal_terms = ("设计", "帮我", "希望", "任务", "revisit", "遥感", "satellite", "mission")
    return has_context or any(term in text for term in goal_terms)


def _add_action(
    actions: List[Dict[str, str]],
    *,
    action_type: str,
    priority: str,
    title: str,
    reason: str,
    suggested_user_reply: str,
) -> None:
    if any(action.get("title") == title for action in actions):
        return
    actions.append(
        {
            "action_type": action_type,
            "priority": priority,
            "title": title,
            "reason": reason,
            "suggested_user_reply": suggested_user_reply,
        }
    )


def _generate_next_actions(advisor_input: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate concise state-aware next actions without modifying parameters."""
    params = _params(advisor_input)
    ctx = advisor_input.get("mission_context") or {}
    missing = _missing_params(advisor_input)
    issues = advisor_input.get("consistency_issues") or []
    orbit_meta = advisor_input.get("orbit_metadata") or {}
    actions: List[Dict[str, str]] = []

    if _looks_like_task_goal(advisor_input, params, ctx):
        _add_action(
            actions,
            action_type="switch_to_task_mode",
            priority="high",
            title="建议使用任务级需求模式",
            reason="当前输入更像任务目标，适合先由任务级模式生成候选参数草案，再进入参数级校验。",
            suggested_user_reply="请切换到任务级需求模式，生成候选参数草案。",
        )
        return actions

    if _has_circular_nonzero_eccentricity(advisor_input, params, issues):
        _add_action(
            actions,
            action_type="ask_user",
            priority="high",
            title="确认圆轨道与偏心率",
            reason="当前同时给出圆轨道语义和非零 eccentricity，存在物理/语义矛盾。",
            suggested_user_reply="改为圆轨道，偏心率用0；或保留偏心率0.10，轨道类型改为椭圆轨道。",
        )

    if _inclination_missing(params, orbit_meta, missing):
        _add_action(
            actions,
            action_type="ask_user",
            priority="high",
            title="补充轨道倾角",
            reason="当前缺少核心轨道倾角，无法判断覆盖和重访，也无法通过 core orbit gate。",
            suggested_user_reply="倾角用51.6度。若希望太阳同步轨道，请说明采用 SSO。",
        )

    if advisor_input.get("core_gate_passed") is False and not actions:
        _add_action(
            actions,
            action_type="ask_user",
            priority="high",
            title="补充核心轨道参数",
            reason="当前核心轨道门控未通过，需要先补齐半长轴、偏心率或倾角等关键参数。",
            suggested_user_reply="请补充缺失的核心轨道参数，例如高度500km、圆轨道、倾角51.6度。",
        )

    defaulted_angles = _defaulted_orbit_angles(advisor_input)
    if defaulted_angles:
        _add_action(
            actions,
            action_type="confirm_assumption",
            priority="medium",
            title="确认默认轨道角参数",
            reason="当前部分轨道角参数由系统默认设为0 deg，需要用户确认。",
            suggested_user_reply="确认 RAAN=0度，近地点幅角=0度，真近点角=0度。",
        )

    remote_sensing = _is_remote_sensing_context(ctx, advisor_input)
    if remote_sensing and (
        _missing_context_or_param(ctx, params, "ground_resolution_m")
        or _missing_context_or_param(ctx, params, "swath_width_km")
    ):
        _add_action(
            actions,
            action_type="suggest_optional",
            priority="medium",
            title="补充载荷性能参数",
            reason="遥感任务需要分辨率和幅宽才能判断任务能力和重访合理性。",
            suggested_user_reply="分辨率10米，幅宽50公里。",
        )

    if ctx.get("revisit_time_h") is not None and (
        _missing_context_or_param(ctx, params, "swath_width_km")
        or _missing_context_or_param(ctx, params, "pointing_accuracy_deg")
    ):
        _add_action(
            actions,
            action_type="suggest_optional",
            priority="medium",
            title="补充重访能力约束",
            reason="重访周期不仅由轨道决定，还与幅宽、侧摆能力和星座规模有关。",
            suggested_user_reply="幅宽50公里，允许侧摆成像。",
        )

    if remote_sensing and (
        _missing_context_or_param(ctx, params, "daily_data_volume_GB")
        or _missing_context_or_param(ctx, params, "downlink_rate_Mbps")
    ):
        _add_action(
            actions,
            action_type="suggest_optional",
            priority="medium",
            title="补充数据量或下行速率",
            reason="遥感任务需要数据生成、星上存储和下行链路闭环。",
            suggested_user_reply="日数据量50GB，下行速率100Mbps。",
        )

    priority_rank = {"high": 0, "medium": 1, "low": 2}
    actions.sort(key=lambda item: priority_rank.get(item.get("priority", "low"), 2))
    return actions[:5]


def _fill_rule_based_advice(
    report: Dict[str, Any],
    advisor_input: Dict[str, Any],
    combined: str,
) -> None:
    """Fill the advisor report with rule-based Chinese advice.

    This is the primary fallback when no LLM client is available.  It
    analyses the current design state and produces structured advice
    without calling any external API.
    """
    params = _params(advisor_input)
    ctx = advisor_input.get("mission_context", {})
    missing = _missing_params(advisor_input)
    issues = advisor_input.get("consistency_issues", [])
    validation = advisor_input.get("validation_results", [])
    task_results = _tool_results(advisor_input)
    orbit_meta = advisor_input.get("orbit_metadata", {})
    defaults = advisor_input.get("default_assumptions", [])

    # --- Design summary ---
    summary_parts = []
    orbit_type = params.get("orbit_type", {}).get("value")
    altitude = params.get("orbit_altitude_km", {}).get("value")
    mass = params.get("payload_mass_kg", {}).get("value")
    power = params.get("power_required_w", {}).get("value")
    payload_type = ctx.get("payload_type")
    mission_type = ctx.get("mission_type")

    if orbit_type:
        summary_parts.append(f"轨道类型：{orbit_type}")
    if altitude is not None:
        summary_parts.append(f"轨道高度：{altitude} km")
    if mass is not None:
        summary_parts.append(f"载荷质量：{mass} kg")
    if power is not None:
        summary_parts.append(f"功率需求：{power} W")
    if payload_type:
        summary_parts.append(f"载荷类型：{payload_type}")
    if mission_type:
        summary_parts.append(f"任务类型：{mission_type}")

    if summary_parts:
        report["design_summary"] = "当前设计概况：" + "；".join(summary_parts) + "。"
    else:
        report["design_summary"] = "当前设计参数不足，无法生成完整概况。"

    # --- Main risks ---
    risks: List[str] = []

    # Check for severe validation errors
    for v in validation:
        data = _item_to_dict(v)
        if data.get("level") == "severe":
            risks.append(f"参数严重异常：{data.get('message', '')}")

    # Check for severe orbit conflicts
    for issue in issues:
        data = _item_to_dict(issue)
        if data.get("level") == "severe":
            risks.append(f"轨道矛盾：{data.get('message', '')}")

    # Check for missing core orbit elements
    missing_core = (orbit_meta or {}).get("missing_core_elements", [])
    if missing_core:
        risks.append(f"缺少核心轨道参数：{', '.join(missing_core)}，无法执行下游工具计算。")

    # Low altitude drag risk
    altitude_value = _safe_float(altitude)
    mass_value = _safe_float(mass)
    power_value = _safe_float(power)

    if altitude_value is not None and altitude_value <= 350:
        risks.append(f"轨道高度 {altitude} km 较低，大气阻力风险较高，可能影响任务寿命。")

    # High altitude beyond LEO
    if altitude_value is not None and altitude_value > 2000:
        risks.append(f"轨道高度 {altitude} km 超出当前 LEO 小卫星工具范围。")

    # Large mass
    if mass_value is not None and mass_value > 300:
        risks.append(f"载荷质量 {mass} kg 超出小卫星概念设计范围，建议重新评估任务规模。")

    # High power
    if power_value is not None and power_value > 1000:
        risks.append(f"功率需求 {power} W 超出小卫星概念设计范围。")

    # Missing inclination for LEO
    if orbit_type == "LEO" and not params.get("orbit_inclination_deg", {}).get("found"):
        risks.append("LEO 轨道未指定倾角，无法唯一确定轨道面。")

    # Default assumptions
    if defaults:
        default_names = [
            str(item.get("field", item)) if isinstance(item, dict) else str(item)
            for item in defaults
        ]
        risks.append(f"以下参数使用了默认假设，需用户确认：{', '.join(default_names)}。")

    # RAG-based risk hints
    if combined:
        rag_risks = _extract_risk_hints(combined)
        risks.extend(rag_risks)

    report["main_risks"] = risks if risks else ["未发现明显风险。"]

    # --- Parameter comments ---
    comments: List[str] = []
    for v in validation:
        data = _item_to_dict(v)
        level = data.get("level")
        if level == "warning":
            comments.append(f"参数警告：{data.get('message', '')}")
        elif level == "pass":
            comments.append(f"参数正常：{data.get('message', '')}")

    if not comments:
        comments.append("当前参数未发现异常。")
    report["parameter_comments"] = comments

    # --- Missing parameter suggestions ---
    suggestions: List[str] = []
    for m in missing:
        sev = m.get("severity", "recommended")
        desc = m.get("description", m.get("parameter", ""))
        if sev == "required":
            suggestions.append(f"【必需】{desc}：请补充该参数以继续完整分析。")
        else:
            suggestions.append(f"【建议】{desc}：补充后可获得更全面的设计评估。")

    # Mission context missing suggestions
    ctx_missing = []
    if ctx.get("payload_type") is None:
        ctx_missing.append("载荷类型")
    if ctx.get("target_region") is None:
        ctx_missing.append("目标区域")
    if ctx.get("ground_resolution_m") is None:
        ctx_missing.append("地面分辨率")
    if ctx.get("daily_data_volume_GB") is None:
        ctx_missing.append("日数据量")
    if ctx.get("downlink_rate_Mbps") is None:
        ctx_missing.append("下行数据率")
    if ctx.get("swath_width_km") is None:
        ctx_missing.append("幅宽")

    if ctx_missing:
        suggestions.append(f"【建议】任务上下文待补充：{', '.join(ctx_missing)}。补充后 RAG-enhanced design advisor 可提供更针对性的只读设计建议。")

    if not suggestions:
        suggestions.append("当前参数较为完整，未发现明显缺失。")
    report["missing_parameter_suggestions"] = suggestions

    # --- Recommended next steps ---
    steps: List[str] = []
    if missing_core:
        steps.append("补充核心轨道参数（半长轴、倾角），以解锁下游工具计算。")
    if any(_item_to_dict(v).get("level") == "severe" for v in validation):
        steps.append("修正严重参数异常后重新运行分析。")
    if any(_item_to_dict(i).get("level") == "severe" for i in issues):
        steps.append("修正轨道矛盾后重新运行分析。")
    if altitude_value is not None and altitude_value <= 350:
        steps.append("评估低轨大气阻力对任务寿命的影响，考虑适当提高轨道高度。")
    if ctx_missing:
        steps.append("补充任务上下文信息，以获得更精确的设计建议。")
    if task_results:
        steps.append("查看 deterministic tools 计算结果，评估方案可行性。")
    steps.append("本报告为概念设计阶段初步估算，建议后续使用专业工具进行详细仿真验证。")

    report["recommended_next_steps"] = steps

    # --- Limitations ---
    report["limitations"] = [
        "所有计算结果均为概念设计阶段初步估算，不构成飞行合格结论。",
        "当前工具不包含高保真轨道传播、覆盖重访仿真或星座相位优化。",
        "LLM 估算项必须标记为概念估算或外部仿真需求，不得视为验证结果。",
        "RAG-enhanced design advisor 基于本地知识库和可选 LLM 综合，知识库内容有限，建议补充更多设计参考文档。",
    ]
    if not combined:
        report["limitations"].insert(
            0,
            "当前未检索到相关知识库内容，建议向 docs/rag_knowledge/ 添加设计参考文档。",
        )


def _synthesise_with_llm(
    advisor_input: Dict[str, Any],
    combined: str,
    llm_client: Any,
) -> Optional[Dict[str, Any]]:
    """Attempt to synthesise a structured advisor report via LLM.

    Uses a supplied OpenAI-compatible client.  The app does not create or pass
    a client by default, so this path is optional and never blocks the main
    deterministic workflow.
    """
    payload = {
        "advisor_input": _compact_advisor_input(advisor_input),
        "retrieved_knowledge": combined[:2000],
        "required_schema": _empty_report(),
    }
    response = llm_client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", DEFAULT_MODEL),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a RAG-enhanced spacecraft conceptual design advisor. "
                    "Return ONLY valid JSON matching the advisor_report schema. "
                    "Write user-visible advice in Chinese. Retrieved knowledge "
                    "and advisor_input are read-only context. Do not modify "
                    "parameters, infer replacement engineering values, override "
                    "deterministic tool results, or decide whether the core gate passes."
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        temperature=0.2,
        max_tokens=1600,
        timeout=int(os.environ.get("LLM_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))),
    )
    raw = response.choices[0].message.content or ""
    parsed = parse_llm_json(raw)
    if not isinstance(parsed, dict):
        return None

    clean = _empty_report()
    for key in clean:
        if key in parsed and key not in {"llm_synthesis_used"}:
            clean[key] = parsed[key]
    clean["rag_snippets_used"] = _extract_snippet_previews(combined) if combined else []
    if "rag_references" not in parsed:
        clean["rag_references"] = _extract_references_from_combined(combined)
    return clean


def _extract_references_from_combined(combined: str) -> List[Dict[str, Any]]:
    references: List[Dict[str, Any]] = []
    for line in combined.splitlines():
        if not line.startswith("--- "):
            continue
        header = line[4:].strip()
        source_part, _, heading = header.partition(" - ")
        source_file, _, line_ref = source_part.partition(":")
        references.append(
            {
                "source_file": source_file,
                "heading": heading,
                "line_ref": line_ref,
                "short_snippet": "",
            }
        )
    return references[:5]


def _compact_advisor_input(advisor_input: Dict[str, Any]) -> Dict[str, Any]:
    params = _params(advisor_input)
    return {
        "report_status": advisor_input.get("report_status"),
        "raw_input_history": advisor_input.get("raw_input_history", []),
        "current_round_input": advisor_input.get("current_round_input", ""),
        "core_gate_passed": advisor_input.get("core_gate_passed"),
        "parameters": {
            key: {
                "value": entry.get("value"),
                "unit": entry.get("unit"),
                "source": entry.get("source"),
                "status": entry.get("status"),
                "requires_confirmation": entry.get("requires_confirmation"),
            }
            for key, entry in params.items()
            if not key.startswith("_") and isinstance(entry, dict)
        },
        "explicit_parameters": advisor_input.get("explicit_parameters", {}),
        "mission_context": advisor_input.get("mission_context", {}),
        "missing_params": _missing_params(advisor_input),
        "consistency_issues": [
            _item_to_dict(item) for item in advisor_input.get("consistency_issues", [])
        ],
        "validation_results": [
            _item_to_dict(item) for item in advisor_input.get("validation_results", [])
        ],
        "tool_results": _tool_results(advisor_input),
        "orbit_metadata": advisor_input.get("orbit_metadata", {}),
        "default_assumptions": advisor_input.get("default_assumptions", []),
        "raw_user_input": advisor_input.get("raw_user_input", ""),
    }
