"""Streamlit UI helpers for the spacecraft design demo."""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any, Iterable

import streamlit as st

from agents.mission_context_extractor import build_mission_context_display_rows


STATUS_CLASS = {
    "未运行": "status-neutral",
    "解析中": "status-active",
    "已完成": "status-success",
    "需要补充参数": "status-warning",
    "存在严重冲突": "status-danger",
}

USE_MODE_PARAMETER = "参数级设计模式"
USE_MODE_MISSION = "任务级需求模式"

SOURCE_LABELS = {
    "user_provided": "用户提供",
    "llm_extracted": "LLM 提取",
    "llm_extracted_normalized": "LLM 提取",
    "rules_extracted": "规则提取",
    "rules_fallback": "规则 fallback",
    "user_updated": "用户显式修改",
    "llm_inferred": "LLM 推断",
    "rules_inferred": "规则推断",
    "user_confirmed_llm_inferred": "用户确认的草案推断",
    "user_confirmed": "用户确认",
    "inferred_from_altitude": "由高度推断",
    "inferred_from_orbit_type": "由轨道类型推断",
    "default_assumption": "默认假设",
    "llm_estimated": "LLM 概念估算",
    "requires_external_simulation": "需外部仿真",
    "tool_computed": "工具计算",
    "not_found": "未提供",
}

STATUS_LABELS = {
    "user_provided": "已提供",
    "user_confirmed": "用户已确认",
    "user_updated": "用户显式修改",
    "inferred": "已推断",
    "computed": "工具计算",
    "default_assumption": "默认假设",
    "missing": "缺失",
    "available": "已提供",
    "not_found": "缺失",
    "invalid_unit": "单位待确认",
    "missing_unit": "单位缺失",
}

PARAM_SOURCE_CATEGORIES = {
    "explicit": {"user_provided", "llm_extracted", "llm_extracted_normalized", "rules_extracted", "rules_fallback", "user_confirmed_llm_inferred", "user_confirmed", "user_updated"},
    "inferred": {"inferred_from_altitude", "inferred_from_orbit_type", "llm_inferred", "rules_inferred", "tool_computed"},
    "default": {"default_assumption"},
    "missing": {"not_found"},
}

EXECUTION_LOG_SESSION_KEY = "execution_logs"
EXECUTION_LOG_MAX_ENTRIES = 80

EVENT_TYPE_LABELS = {
    "new_design_started": "开始新方案",
    "design_updated_from_natural_language": "补充 / 修改当前方案",
    "confirmation_patch_created": "生成 confirmation_patch",
    "confirmation_patch_applied": "应用 confirmation_patch",
    "validation_completed": "校验完成",
    "severe_blocked": "severe 阻断",
    "core_gate_passed": "core gate 通过",
    "core_gate_failed": "core gate 未通过",
    "tools_executed": "deterministic tools 已运行",
    "advisor_generated": "advisor 已生成",
    "saved_state_rendered": "已渲染当前方案",
    "parameter_overwritten": "参数覆盖修改",
    "pipeline_rerun_started": "重新运行 pipeline",
}

TASK_PARAM_DISPLAY = [
    ("orbit_type", "轨道类型", ""),
    ("orbit_altitude_km", "轨道高度", "km"),
    ("payload_mass_kg", "载荷质量", "kg"),
    ("power_required_w", "载荷功率", "W"),
    ("orbit_period_min", "轨道周期", "min"),
    ("mission_lifetime_years", "任务寿命", "year"),
    ("ground_resolution_m", "地面分辨率", "m"),
    ("daily_data_volume_GB", "日数据量", "GB"),
]

ORBIT_ELEMENT_DISPLAY = [
    ("semi_major_axis_km", "半长轴"),
    ("eccentricity", "偏心率"),
    ("inclination_deg", "轨道倾角"),
    ("raan_deg", "升交点赤经"),
    ("arg_perigee_deg", "近地点幅角"),
    ("true_anomaly_deg", "真近点角"),
]

ORBIT_ELEMENT_PARAM_DISPLAY = [
    ("semi_major_axis_km", "半长轴", "km"),
    ("eccentricity", "偏心率", ""),
    ("orbit_inclination_deg", "轨道倾角", "deg"),
    ("raan_deg", "升交点赤经", "deg"),
    ("arg_perigee_deg", "近地点幅角", "deg"),
    ("true_anomaly_deg", "真近点角", "deg"),
]

PARAMETER_EXAMPLE_INPUTS = {
    "完整概念设计": "LEO，圆轨道，500km，倾角51.6度，光学遥感，目标马来西亚，6小时重访，载荷20kg，功率200W",
    "缺少核心参数": "LEO，圆轨道，300km，载荷20kg，功率200W",
    "参数矛盾": "LEO，圆轨道，300km，偏心率0.10，倾角10度，载荷20kg，功率200W",
}


def build_execution_log_entry(
    event_type: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    round_number: int | None = None,
    sequence: int | None = None,
) -> dict[str, Any]:
    """Build a session-local execution log entry."""

    return {
        "sequence": sequence,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "round": round_number,
        "event_type": event_type,
        "message": message,
        "details": details or {},
    }


def append_execution_log_entry(
    logs: list[dict[str, Any]],
    event_type: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    round_number: int | None = None,
    max_entries: int = EXECUTION_LOG_MAX_ENTRIES,
) -> dict[str, Any]:
    """Append an execution event to a mutable list and keep it bounded."""

    sequence = len(logs) + 1
    entry = build_execution_log_entry(
        event_type,
        message,
        details=details,
        round_number=round_number,
        sequence=sequence,
    )
    logs.append(entry)
    if len(logs) > max_entries:
        del logs[:-max_entries]
    return entry


def append_execution_log(
    event_type: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    round_number: int | None = None,
) -> dict[str, Any]:
    """Append a UI execution event into Streamlit session_state."""

    logs = st.session_state.setdefault(EXECUTION_LOG_SESSION_KEY, [])
    return append_execution_log_entry(
        logs,
        event_type,
        message,
        details=details,
        round_number=round_number,
    )


def reset_execution_logs() -> None:
    """Clear session-local execution logs for a fresh design scheme."""

    st.session_state[EXECUTION_LOG_SESSION_KEY] = []


def get_execution_logs(limit: int = 20) -> list[dict[str, Any]]:
    """Return recent session-local execution log entries."""

    logs = st.session_state.get(EXECUTION_LOG_SESSION_KEY, [])
    return list(logs[-limit:])


def apply_console_style() -> None:
    """Apply a clean white scientific-console style."""

    st.markdown(
        """
        <style>
        :root {
            --console-blue: #183b63;
            --console-blue-soft: #eef4fb;
            --console-border: #d9e2ec;
            --console-muted: #6b7280;
            --console-bg: #ffffff;
            --console-card: #ffffff;
            --console-soft: #f7f9fc;
            --console-warning: #fff7df;
            --console-warning-border: #ecd38b;
            --console-danger: #fff0f0;
            --console-danger-border: #efb2b2;
            --console-success: #effaf3;
            --console-success-border: #a9d9b8;
        }
        .stApp { background: var(--console-bg); }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1180px;
        }
        h1, h2, h3 { color: #102a43; letter-spacing: 0; }
        [data-testid="stMetricValue"] { color: #102a43; }
        .console-header {
            border: 1px solid var(--console-border);
            background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
            border-radius: 8px;
            padding: 1.35rem 1.5rem;
            margin-bottom: 1rem;
        }
        .console-title {
            font-size: 1.85rem;
            font-weight: 700;
            color: #102a43;
            margin-bottom: 0.25rem;
        }
        .console-subtitle {
            font-size: 0.98rem;
            color: #486581;
            margin-bottom: 0.8rem;
        }
        .status-pill {
            display: inline-block;
            border-radius: 999px;
            padding: 0.22rem 0.7rem;
            font-size: 0.82rem;
            font-weight: 600;
            border: 1px solid var(--console-border);
            color: #334e68;
            background: #f5f7fa;
        }
        .status-active {
            color: #183b63;
            background: var(--console-blue-soft);
            border-color: #b8cbe0;
        }
        .status-success {
            color: #1f6f3d;
            background: var(--console-success);
            border-color: var(--console-success-border);
        }
        .status-warning {
            color: #8a6116;
            background: var(--console-warning);
            border-color: var(--console-warning-border);
        }
        .status-danger {
            color: #9b1c1c;
            background: var(--console-danger);
            border-color: var(--console-danger-border);
        }
        .section-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: #102a43;
            margin: 0.8rem 0 0.35rem;
        }
        .section-note {
            color: #627d98;
            font-size: 0.9rem;
            margin-bottom: 0.65rem;
        }
        .summary-box {
            border-radius: 8px;
            border: 1px solid var(--console-border);
            padding: 1rem 1.1rem;
            background: #ffffff;
            margin: 0.8rem 0;
        }
        .summary-box.success {
            background: var(--console-success);
            border-color: var(--console-success-border);
        }
        .summary-box.warning {
            background: var(--console-warning);
            border-color: var(--console-warning-border);
        }
        .summary-box.danger {
            background: var(--console-danger);
            border-color: var(--console-danger-border);
        }
        .log-box {
            border: 1px solid var(--console-border);
            background: #0f172a;
            color: #e5edf6;
            border-radius: 8px;
            padding: 0.85rem 1rem;
            height: 230px;
            overflow-y: auto;
            font-family: Consolas, "Courier New", monospace;
            font-size: 0.86rem;
            line-height: 1.65;
        }
        .log-line {
            border-bottom: 1px solid rgba(226, 232, 240, 0.08);
            padding: 0.08rem 0;
        }
        .small-muted {
            color: #6b7280;
            font-size: 0.86rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(status: str, target: Any | None = None) -> None:
    status_class = STATUS_CLASS.get(status, "status-neutral")
    renderer = target.markdown if target is not None else st.markdown
    renderer(
        f"""
        <div class="console-header">
          <div class="console-title">航天器总体设计 AI Agent Demo</div>
          <div class="console-subtitle">面向低轨遥感小卫星概念设计的参数解析、轨道推断与初步方案生成</div>
          <span class="status-pill {status_class}">当前状态：{html.escape(status)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_mode_selector() -> str:
    st.markdown('<div class="section-title">使用模式</div>', unsafe_allow_html=True)
    return st.radio(
        "选择使用模式",
        options=[USE_MODE_PARAMETER, USE_MODE_MISSION],
        index=0,
        horizontal=True,
        label_visibility="collapsed",
        captions=[
            "适合专业用户，直接输入轨道、载荷、功率等参数。",
            "适合新手，从任务目标出发，由 Agent 引导补充约束。",
        ],
        key="use_mode",
    )


def render_input_panel() -> tuple[str, bool, bool, bool]:
    st.markdown('<div class="section-title">1. 参数级输入区</div>', unsafe_allow_html=True)
    _render_parameter_input_help()
    has_state = bool(st.session_state.get("current_design_state"))
    _render_design_state_status(st.session_state.get("current_design_state"))

    if has_state:
        st.markdown('<div class="section-note">补充 / 修改当前方案</div>', unsafe_allow_html=True)
        st.caption(
            "最新显式输入会覆盖当前方案中的同名用户参数；inferred/default 参数会在每轮重新计算；"
            "所有修改仍会重新经过 validation / orbit_consistency / tools / advisor。"
        )
        st.session_state.setdefault("mission_update_input", "")
        user_input = st.text_area(
            "补充 / 修改当前方案",
            height=120,
            placeholder=(
                "你可以直接输入新参数覆盖当前方案，例如：\n"
                "- 高度改为500km\n"
                "- RAAN改为30度\n"
                "- 倾角改为97.4度\n"
                "- 载荷功率改为300W\n"
                "- 目标区域改为新加坡"
            ),
            label_visibility="collapsed",
            key="mission_update_input",
        )
    else:
        _render_parameter_examples()
        st.session_state.setdefault("mission_input", "")
        user_input = st.text_area(
            "任务需求",
            height=140,
            placeholder="例如：LEO300km，圆轨道，载荷30kg，功率200W，倾角51.6度",
            label_visibility="collapsed",
            key="mission_input",
        )

    col1, col2, col3, col4 = st.columns([1.25, 1.45, 1, 2.2])
    with col1:
        start_new = st.button("开始新方案", type="primary", width="stretch")
    with col2:
        update_current = st.button(
            "补充 / 修改当前方案",
            width="stretch",
            disabled=not has_state,
        )
    with col3:
        clear = st.button("清空输入", width="stretch", on_click=_clear_input_state)
    with col4:
        st.markdown(
            f'<div class="small-muted">运行状态：{html.escape(st.session_state.get("run_status", "未运行"))}</div>',
            unsafe_allow_html=True,
        )
    return user_input, start_new, update_current, clear


def _render_parameter_input_help() -> None:
    with st.expander("如何输入参数", expanded=True):
        st.info(
            "mission_context 是可选加分项：不提供也可以运行参数级流程；提供任务类型、目标区域、重访时间、"
            "载荷类型、分辨率、幅宽、数据量或下行速率后，RAG-enhanced design advisor 会给出更具体的概念级设计评审。"
        )
        st.markdown(
            """
            参数级模式适用于已有参数方案的校验、计算和设计评审。如果只有任务目标、没有具体参数，建议切换到任务级需求模式。

            建议至少提供：轨道类型 / 高度 / 倾角、轨道形状或偏心率、载荷质量 / 载荷功率。

            可选任务上下文包括：任务类型、目标区域、重访需求、载荷类型、分辨率、幅宽、数据量、下行速率。

            `mission_context` 只用于界面展示和 RAG-enhanced 设计评审，不参与 core orbit gate，也不触发 deterministic tools。
            """
        )


def _render_parameter_examples() -> None:
    st.markdown('<div class="section-note">示例输入（仅用于人工演示，不参与业务逻辑）</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for index, (label, text) in enumerate(PARAMETER_EXAMPLE_INPUTS.items()):
        with cols[index]:
            st.button(
                label,
                key=f"example_{index}",
                width="stretch",
                on_click=_set_parameter_example,
                args=(text,),
            )


def _set_parameter_example(text: str) -> None:
    st.session_state["mission_input"] = text
    st.session_state["mission_update_input"] = text


def _render_design_state_status(design_state: dict[str, Any] | None) -> None:
    if not design_state:
        _summary_html(
            "warning",
            [
                "当前没有已保存方案。点击“开始新方案”会从输入框创建新的参数级设计状态。",
                "已有方案后，可用“补充 / 修改当前方案”在当前会话内合并新增显式参数。",
            ],
        )
        return

    history = design_state.get("raw_input_history") or []
    missing = design_state.get("missing_core_elements") or [
        item.get("parameter") or item.get("description", "")
        for item in design_state.get("missing_parameters", [])
    ]
    missing_text = ", ".join(str(item) for item in missing if item) or "无核心缺失项"
    _summary_html(
        "success" if design_state.get("report_status") == "已完成" else "warning",
        [
            "当前已有会话内设计状态，可继续补充或修改。",
            f"累计输入轮次：{len(history)}。",
            f"当前 report_status：{design_state.get('report_status') or '未运行'}。",
            f"当前仍缺：{missing_text}。",
        ],
    )


def render_mission_input_panel() -> tuple[str, bool, bool]:
    st.markdown('<div class="section-title">1. 任务目标输入</div>', unsafe_allow_html=True)
    user_input = st.text_area(
        "任务目标",
        value=st.session_state.get("mission_goal_input", ""),
        height=140,
        placeholder="例如：帮我设计一颗6小时访问一次马来西亚的遥感卫星",
        label_visibility="collapsed",
        key="mission_goal_input",
    )
    col1, col2, col3 = st.columns([1.7, 1, 3])
    with col1:
        analyze = st.button("开始任务理解", type="primary", width="stretch")
    with col2:
        clear = st.button("清空任务", width="stretch", on_click=_clear_task_state)
    with col3:
        st.markdown(
            f'<div class="small-muted">当前模式：{USE_MODE_MISSION}</div>',
            unsafe_allow_html=True,
        )
    return user_input, analyze, clear


def _clear_input_state() -> None:
    st.session_state["mission_input"] = ""
    st.session_state["mission_update_input"] = ""
    st.session_state["run_status"] = "未运行"
    st.session_state.pop("current_design_state", None)
    st.session_state.pop("mission_context", None)


def _clear_task_state() -> None:
    st.session_state["mission_goal_input"] = ""
    st.session_state["run_status"] = "未运行"


def render_mission_guidance_panel(
    guidance: dict[str, Any] | None,
    inactive: bool = False,
) -> str | None:
    st.markdown('<div class="section-title">2. 任务理解与约束补充</div>', unsafe_allow_html=True)

    if inactive or not guidance:
        st.markdown(
            '<div class="section-note">等待任务目标输入。任务级模式只做需求理解和约束引导，不执行工程计算。</div>',
            unsafe_allow_html=True,
        )
        _summary_html("warning", ["尚未开始任务级引导。", "请输入任务目标后，系统会列出需要补充的设计约束。"])
        return None

    context = guidance.get("mission_context", {})
    st.markdown('<div class="section-note">Agent 识别到的任务意图</div>', unsafe_allow_html=True)
    st.dataframe(_intent_rows(context), width="stretch", hide_index=True)

    st.markdown('<div class="section-note">需要补充的关键设计约束</div>', unsafe_allow_html=True)
    st.dataframe(guidance.get("constraints", []), width="stretch", hide_index=True)

    selected_draft_id = None
    drafts = guidance.get("candidate_drafts", [])
    if drafts:
        st.markdown('<div class="section-note">候选参数草案（概念级，未验证）</div>', unsafe_allow_html=True)
        st.dataframe(_draft_overview_rows(drafts), width="stretch", hide_index=True)
        for draft in drafts:
            with st.expander(draft.get("draft_name", "候选草案"), expanded=False):
                st.markdown(f"**设计理由：** {draft.get('design_rationale', '')}")
                st.markdown(f"**验证状态：** `{draft.get('verification_status', 'not_verified')}`")
                st.markdown(f"**requires_confirmation：** `{draft.get('requires_confirmation', True)}`")
                st.markdown("**关键假设**")
                for assumption in draft.get("key_assumptions", []):
                    st.markdown(f"- {assumption}")
                missing_constraints = draft.get("missing_constraints", [])
                if missing_constraints:
                    st.markdown("**仍需补充/确认的约束**")
                    for item in missing_constraints:
                        st.markdown(f"- `{item}`")
                st.dataframe(
                    _draft_parameter_rows(draft),
                    width="stretch",
                    hide_index=True,
                )
                if st.button(
                    "采用该草案继续分析",
                    key=f"adopt_{draft.get('draft_id')}",
                    width="stretch",
                ):
                    selected_draft_id = draft.get("draft_id")

    _summary_html(
        "warning",
        [
            "任务级草案均为概念级建议，不是工程验证结果。",
            "采用草案后，草案参数会标记为 user_confirmed_llm_inferred。",
            "覆盖、重访、星座能力等仍需外部仿真；现有 deterministic tools 只在参数级流程中运行。",
        ],
    )

    if guidance.get("report"):
        with st.expander("任务需求理解与约束补充建议", expanded=False):
            st.markdown(guidance["report"])
    return selected_draft_id


def render_mission_debug_panel(guidance: dict[str, Any] | None) -> None:
    with st.expander("高级调试信息", expanded=False):
        st.json(guidance or {})


def render_parameter_cards(
    params: dict[str, Any] | None,
    orbit_metadata: dict[str, Any] | None,
    inactive: bool = False,
) -> None:
    st.markdown('<div class="section-title">2. 参数显示区域</div>', unsafe_allow_html=True)
    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.markdown('<div class="section-note">轨道六根数</div>', unsafe_allow_html=True)
        st.dataframe(
            _orbital_element_rows(orbit_metadata, inactive=inactive),
            width="stretch",
            hide_index=True,
        )
    with col2:
        st.markdown('<div class="section-note">任务 / 载荷参数</div>', unsafe_allow_html=True)
        st.dataframe(
            _task_parameter_rows(params, inactive=inactive),
            width="stretch",
            hide_index=True,
        )


def render_current_design_summary_card(design_state: dict[str, Any] | None) -> None:
    """Render the latest effective current_design_state summary."""

    if not design_state:
        return

    st.markdown('<div class="section-title">2a. 当前方案摘要</div>', unsafe_allow_html=True)
    st.caption(
        "这是 current_design_state 的当前有效方案摘要，不是原始 raw input。"
        "raw_input_history 会保留原始输入用于审计，不会被确认表单覆盖。"
    )
    st.dataframe(_design_summary_rows(design_state), width="stretch", hide_index=True)
    st.info(
        "当前等效方案描述 / 自动生成摘要："
        + _build_equivalent_design_description(design_state)
    )

    last_rows = _last_confirmation_rows(design_state)
    if last_rows:
        st.markdown("**最近一次应用记录**")
        st.caption("patch_source = parameter_confirmation_form")
        st.dataframe(last_rows, width="stretch", hide_index=True)


def render_raw_input_history_panel(design_state: dict[str, Any] | None) -> None:
    """Render immutable raw input history as an audit expander."""

    if not design_state:
        return
    history = design_state.get("raw_input_history") or []
    if not history:
        return

    with st.expander("原始输入历史 / 审计记录", expanded=False):
        st.caption(
            "以下内容来自 raw_input_history，仅用于审计。当前有效方案请以上方 current_design_state 摘要为准；"
            "参数确认表单不会覆盖这里的原始输入。"
        )
        rows = [
            {"轮次": index + 1, "原始输入": str(text)}
            for index, text in enumerate(history)
        ]
        st.dataframe(rows, width="stretch", hide_index=True)


def render_parameter_understanding_panel(
    params: dict[str, Any] | None,
    orbit_metadata: dict[str, Any] | None,
    mission_context: dict[str, Any] | None,
    missing_params: list[dict[str, Any]] | None,
    validation_results: Iterable[Any] | None,
    orbit_conflicts: Iterable[Any] | None,
    inactive: bool = False,
) -> None:
    """Render a detailed parameter understanding panel with tabs.

    Shows:
    - Tab 1: 用户显式参数 (explicit user params)
    - Tab 2: 任务上下文 (mission context)
    - Tab 3: 系统推断参数 (inferred parameters)
    - Tab 4: 默认假设参数 (default assumptions)
    - Tab 5: 缺失/待确认参数 (missing params)
    - Tab 6: 一致性检查 (consistency issues)
    """
    st.markdown('<div class="section-title">3. 参数理解结果</div>', unsafe_allow_html=True)
    if inactive or not params:
        st.markdown('<div class="section-note">等待任务输入后显示参数理解详情。</div>', unsafe_allow_html=True)
        return

    tab_labels = [
        "用户显式参数",
        "任务上下文",
        "系统推断参数",
        "默认假设参数",
        "缺失/待确认",
        "一致性检查",
    ]
    tabs = st.tabs(tab_labels)

    # --- Tab 1: 用户显式参数 ---
    with tabs[0]:
        explicit_rows = _explicit_param_rows(params)
        if explicit_rows:
            st.dataframe(explicit_rows, width="stretch", hide_index=True)
        else:
            st.markdown("未识别到用户显式参数。")

    # --- Tab 2: 任务上下文 ---
    with tabs[1]:
        if mission_context:
            ctx_rows = build_mission_context_display_rows(mission_context)
            st.dataframe(ctx_rows, width="stretch", hide_index=True)
        else:
            st.markdown("未提取到任务上下文信息。")

    # --- Tab 3: 系统推断参数 ---
    with tabs[2]:
        inferred_rows = _inferred_param_rows(params, orbit_metadata)
        if inferred_rows:
            st.dataframe(inferred_rows, width="stretch", hide_index=True)
        else:
            st.markdown("无系统推断参数。")

    # --- Tab 4: 默认假设参数 ---
    with tabs[3]:
        default_rows = _default_param_rows(params, orbit_metadata)
        if default_rows:
            st.dataframe(default_rows, width="stretch", hide_index=True)
        else:
            st.markdown("无默认假设参数。")

    # --- Tab 5: 缺失/待确认参数 ---
    with tabs[4]:
        missing_rows = _missing_param_rows(params, missing_params)
        if missing_rows:
            st.dataframe(missing_rows, width="stretch", hide_index=True)
        else:
            st.markdown("未发现缺失参数。")

    # --- Tab 6: 一致性检查 ---
    with tabs[5]:
        conflict_rows = _consistency_rows(validation_results, orbit_conflicts)
        if conflict_rows:
            st.dataframe(conflict_rows, width="stretch", hide_index=True)
        else:
            st.markdown("未发现一致性问题。")


def render_patch_view_panel(patch_view: dict[str, Any] | None) -> None:
    """Render a best-effort diff for multi-turn parameter updates."""
    if not patch_view:
        return

    st.markdown('<div class="section-title">3a. 本轮参数变更 / Patch View</div>', unsafe_allow_html=True)
    st.caption(
        "说明：raw input history 保留原始输入；current_design_state 是当前有效方案；"
        "inferred/default 每轮重新计算，不覆盖 user explicit。"
    )
    st.markdown(
        '<div class="section-note">仅展示本轮显式输入如何合并到当前方案；inferred/default 不参与合并，也不会覆盖 user explicit。</div>',
        unsafe_allow_html=True,
    )
    if patch_view.get("source") == CONFIRMATION_FORM_SOURCE:
        st.caption("本轮 Patch 来源：parameter_confirmation_form。只有勾选并确认的 user_confirmed 字段进入合并。")

    added = patch_view.get("added") or []
    modified = patch_view.get("modified") or []
    retained = patch_view.get("retained") or []
    not_merged = patch_view.get("not_merged") or []
    current_missing = patch_view.get("current_missing") or []

    tab_labels = ["本轮新增", "本轮修改", "本轮保留", "未参与合并", "当前仍缺"]
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        _render_patch_rows(added, empty_text="本轮没有识别到新增 user explicit 参数或 mission_context。")
    with tabs[1]:
        _render_patch_rows(modified, empty_text="本轮没有识别到显式参数修改。", show_previous=True)
    with tabs[2]:
        _render_patch_rows(retained, empty_text="没有需要从上一轮保留的显式参数。")
    with tabs[3]:
        _render_patch_rows(
            not_merged,
            empty_text="未发现上一轮 inferred/default 参数。它们仍会在本轮重新计算，不作为用户显式输入合并。",
        )
    with tabs[4]:
        if current_missing:
            for item in current_missing:
                st.markdown(f"- `{item}`")
        else:
            st.markdown("当前没有核心缺失项；任务级性能约束仍可继续补充。")


def render_status_card(
    can_continue: bool,
    skip_reason: str | None,
    orbit_metadata: dict[str, Any] | None,
    validation_results: Iterable[Any] | None,
    orbit_conflicts: Iterable[Any] | None,
    missing: list[dict[str, Any]] | None,
) -> None:
    """Render a flow status card at the top of the results area."""
    severe_items = _validation_by_level(validation_results, "severe")
    warning_items = _validation_by_level(validation_results, "warning")
    severe_conflicts = _conflicts_by_level(orbit_conflicts, "severe")
    warning_conflicts = _conflicts_by_level(orbit_conflicts, "warning")
    missing_core = list((orbit_metadata or {}).get("missing_core_elements", []))

    # Determine status kind
    if can_continue:
        kind = "success"
        title = "流程状态：正常"
        messages = ["当前核心检查通过，可以继续生成普通初步方案。"]
    elif skip_reason == "severe_user_provided_parameter":
        kind = "danger"
        title = "流程状态：参数异常"
        messages = ["用户明确输入的参数存在严重异常，已停止参数补全和普通报告生成。"]
    elif skip_reason == "severe_explicit_orbit_conflict":
        kind = "danger"
        title = "流程状态：轨道矛盾"
        messages = ["用户明确输入的轨道参数存在严重矛盾，已停止参数补全和普通报告生成。"]
    elif skip_reason == "missing_core_orbital_elements":
        kind = "warning"
        title = "流程状态：参数不完整"
        messages = ["当前缺少核心轨道参数，已暂停后续任务分析。"]
    elif skip_reason == "severe_validation_or_orbit_conflict":
        kind = "danger"
        title = "流程状态：严重冲突"
        messages = ["当前存在严重参数错误或轨道矛盾，已停止普通报告生成。"]
    else:
        kind = "warning"
        title = "流程状态：待确认"
        messages = ["当前需要补充或确认参数后再继续。"]

    # Add detail messages
    for field in missing_core:
        reason = (orbit_metadata or {}).get("missing_reasons", {}).get(
            field, "该参数是后续轨道分析所需的核心参数。"
        )
        messages.append(f"• {field} 缺失：{reason}")

    for suggestion in (orbit_metadata or {}).get("next_step_suggestions", []):
        messages.append(f"• 建议：{suggestion}")

    for warning in (orbit_metadata or {}).get("warnings", []):
        messages.append(f"• 轨道风险提示：{warning}")

    for item in severe_conflicts + warning_conflicts:
        messages.append(f"• 轨道一致性：{item.get('message', '')}")
        action = item.get("suggested_user_action")
        if action:
            messages.append(f"  → {action}")

    for item in severe_items + warning_items:
        messages.append(f"• 参数校验：{item.get('message', '')}")

    for item in missing or []:
        if item.get("severity") == "required":
            messages.append(f"• 缺少必需参数：{item.get('description')}")

    if not messages:
        messages.append("未发现阻断项。")

    # Render as expander with status badge
    status_badge = {
        "success": "✅",
        "warning": "⚠️",
        "danger": "🚫",
    }.get(kind, "ℹ️")

    with st.expander(f"{status_badge} {title}", expanded=True):
        for msg in _dedupe(messages):
            st.markdown(msg)


def render_summary_panel(
    *,
    inactive: bool,
    can_continue: bool,
    skip_reason: str | None,
    missing: list[dict[str, Any]] | None,
    validation_results: Iterable[Any] | None,
    orbit_metadata: dict[str, Any] | None,
    orbit_conflicts: Iterable[Any] | None,
    report: str | None,
) -> None:
    st.markdown('<div class="section-title">4. 确定性计算 / 概念报告</div>', unsafe_allow_html=True)
    if inactive:
        _summary_html("warning", ["等待任务输入。", "点击开始解析后，系统会显示参数、轨道推断和后续建议。"])
        return

    messages: list[str] = []
    severe_items = _validation_by_level(validation_results, "severe")
    warning_items = _validation_by_level(validation_results, "warning")
    severe_conflicts = _conflicts_by_level(orbit_conflicts, "severe")
    warning_conflicts = _conflicts_by_level(orbit_conflicts, "warning")
    missing_core = list((orbit_metadata or {}).get("missing_core_elements", []))

    if can_continue:
        messages.append("当前核心检查通过，可以继续生成普通初步方案。")
    elif skip_reason == "severe_user_provided_parameter":
        messages.append("用户明确输入的参数存在严重异常，已停止参数补全和普通报告生成。")
    elif skip_reason == "severe_explicit_orbit_conflict":
        messages.append("用户明确输入的轨道参数存在严重矛盾，已停止参数补全和普通报告生成。")
    elif skip_reason == "missing_core_orbital_elements":
        messages.append("当前缺少核心轨道参数，已暂停后续任务分析。")
    elif skip_reason == "severe_validation_or_orbit_conflict":
        messages.append("当前存在严重参数错误或轨道矛盾，已停止普通报告生成。")
    else:
        messages.append("当前需要补充或确认参数后再继续。")

    for field in missing_core:
        reason = (orbit_metadata or {}).get("missing_reasons", {}).get(
            field,
            "该参数是后续轨道分析所需的核心参数。",
        )
        messages.append(f"{field} 缺失：{reason}")

    for suggestion in (orbit_metadata or {}).get("next_step_suggestions", []):
        messages.append(f"建议：{suggestion}")

    for warning in (orbit_metadata or {}).get("warnings", []):
        messages.append(f"轨道风险提示：{warning}")

    for item in severe_conflicts + warning_conflicts:
        messages.append(f"轨道一致性检查：{item.get('message', '')}")
        action = item.get("suggested_user_action")
        if action:
            messages.append(f"建议：{action}")

    for item in severe_items + warning_items:
        messages.append(f"参数校验：{item.get('message', '')}")

    for item in missing or []:
        if item.get("severity") == "required":
            messages.append(f"缺少必需参数：{item.get('description')}")

    if not messages:
        messages.append("未发现阻断项。")

    box_kind = "success" if can_continue else ("danger" if severe_items or severe_conflicts else "warning")
    _summary_html(box_kind, _dedupe(messages))

    if report:
        with st.expander("完整报告", expanded=False):
            st.markdown(report)


def render_advisor_panel(advisor_report: dict[str, Any] | None) -> None:
    """Render the RAG-enhanced design advisor panel."""
    st.markdown('<div class="section-title">5. 知识增强设计评审</div>', unsafe_allow_html=True)

    if not advisor_report:
        st.markdown('<div class="section-note">未生成设计建议。</div>', unsafe_allow_html=True)
        return

    summary = advisor_report.get("design_summary", "")
    risks = advisor_report.get("main_risks", [])
    param_comments = advisor_report.get("parameter_comments", [])
    suggestions = advisor_report.get("missing_parameter_suggestions", [])
    steps = advisor_report.get("recommended_next_steps", [])
    actions = advisor_report.get("next_actions", [])
    limitations = advisor_report.get("limitations", [])
    snippets = advisor_report.get("rag_snippets_used", [])
    references = advisor_report.get("rag_references", [])
    llm_used = advisor_report.get("llm_synthesis_used", False)

    _render_targeted_clarifications(actions)
    _render_agent_actions(actions)
    _render_rag_references(references)

    tab_labels = []
    tab_contents = []

    if summary:
        tab_labels.append("设计概况")
        tab_contents.append(("设计概况", summary))

    if risks:
        tab_labels.append("主要风险")
        tab_contents.append(("主要风险", risks))

    if param_comments:
        tab_labels.append("参数评价")
        tab_contents.append(("参数评价", param_comments))

    if suggestions:
        tab_labels.append("缺失参数建议")
        tab_contents.append(("缺失参数建议", suggestions))

    if steps:
        tab_labels.append("推荐下一步")
        tab_contents.append(("推荐下一步", steps))

    if limitations:
        tab_labels.append("概念级限制")
        tab_contents.append(("概念级限制", limitations))

    if snippets:
        tab_labels.append("参考知识")
        tab_contents.append(("参考知识", snippets))

    if not tab_labels and actions:
        if llm_used:
            st.caption("本建议由 RAG-enhanced LLM advisor 综合生成。")
        else:
            st.caption("本建议基于规则和本地知识库生成，未使用 LLM 综合。")
        return

    if not tab_labels:
        st.markdown('<div class="section-note">设计建议内容为空。</div>', unsafe_allow_html=True)
        return

    tabs = st.tabs(tab_labels)
    for i, (title, content) in enumerate(tab_contents):
        with tabs[i]:
            if isinstance(content, str):
                st.markdown(content)
            elif isinstance(content, list):
                for item in content:
                    st.markdown(f"- {item}")
            elif isinstance(content, dict):
                st.json(content)

    if llm_used:
        st.caption("本建议由 RAG-enhanced LLM advisor 综合生成。")
    else:
        st.caption("本建议基于规则和本地知识库生成，未使用 LLM 综合。")


def _render_rag_references(references: list[Any]) -> None:
    refs = [ref for ref in references if isinstance(ref, dict)]
    if not refs:
        return

    with st.expander("参考依据", expanded=False):
        for ref in refs[:5]:
            source_file = str(ref.get("source_file") or "unknown")
            line_ref = str(ref.get("line_ref") or "")
            heading = str(ref.get("heading") or "未命名小节")
            snippet = str(ref.get("short_snippet") or "").strip()
            source_label = f"{source_file}:{line_ref}" if line_ref else source_file
            st.markdown(f"- `{source_label}` - {heading}")
            if snippet:
                st.caption(snippet[:180])


def _normalize_action(action: Any) -> dict[str, str]:
    if isinstance(action, dict):
        return {
            "priority": str(action.get("priority") or "medium"),
            "action_type": str(action.get("action_type") or "suggest_optional"),
            "title": str(action.get("title") or "下一步建议"),
            "reason": str(action.get("reason") or ""),
            "suggested_user_reply": str(action.get("suggested_user_reply") or ""),
        }
    return {
        "priority": "medium",
        "action_type": "suggest_optional",
        "title": "下一步建议",
        "reason": str(action),
        "suggested_user_reply": "",
    }


def _action_list(actions: Any) -> list[Any]:
    if isinstance(actions, list):
        return actions
    if actions:
        return [actions]
    return []


def _render_targeted_clarifications(actions: list[Any]) -> None:
    high_questions = [
        _normalize_action(action)
        for action in _action_list(actions)
        if _normalize_action(action).get("priority") == "high"
        and _normalize_action(action).get("action_type") in {"ask_user", "confirm_assumption"}
    ][:3]
    if not high_questions:
        return

    with st.expander("最小追问", expanded=True):
        for action in high_questions:
            st.markdown(f"**{action['title']}**")
            if action.get("reason"):
                st.markdown(action["reason"])
            if action.get("suggested_user_reply"):
                st.markdown(f"建议回复：`{action['suggested_user_reply']}`")


def _render_agent_actions(actions: list[Any]) -> None:
    normalized = [_normalize_action(action) for action in _action_list(actions)]
    if not normalized:
        return

    st.markdown("#### 下一步建议 / Agent Actions")
    priority_label = {"high": "高优先级", "medium": "中优先级", "low": "低优先级"}
    for action in normalized[:5]:
        priority = action.get("priority", "medium")
        title = action.get("title", "下一步建议")
        reason = action.get("reason", "")
        action_type = action.get("action_type", "suggest_optional")
        suggested = action.get("suggested_user_reply", "")
        label = priority_label.get(priority, priority)
        box_kind = "danger" if priority == "high" else ("warning" if priority == "medium" else "success")
        messages = [
            f"{label} / {action_type}",
            f"【{title}】",
        ]
        if reason:
            messages.append(f"原因：{reason}")
        if suggested:
            messages.append(f"建议回复：{suggested}")
        _summary_html(box_kind, messages)


CONFIRMATION_FORM_SOURCE = "parameter_confirmation_form"
CONFIRMATION_SUPPORTED_FIELDS = {
    "orbit_type",
    "orbit_inclination_deg",
    "eccentricity",
    "raan_deg",
    "arg_perigee_deg",
    "true_anomaly_deg",
}
CONFIRMATION_DEFAULT_UNITS = {
    "orbit_type": "",
    "orbit_inclination_deg": "deg",
    "eccentricity": "",
    "raan_deg": "deg",
    "arg_perigee_deg": "deg",
    "true_anomaly_deg": "deg",
}


def render_confirmation_panel(design_state: dict[str, Any] | None) -> None:
    """Render a structured confirmation form for core orbit parameters."""
    if not design_state:
        return

    items = build_confirmation_items(design_state)
    if not items:
        return

    st.markdown('<div class="section-title">5a. 待确认参数 / 参数确认表单</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-note">表单只生成 confirmation_patch，不直接修改 normalized_parameters。'
        '应用后会作为 user_confirmed 显式参数合并到当前 design_state，并重新运行完整参数级流程。</div>',
        unsafe_allow_html=True,
    )
    st.info(
        "本轮结构化表单只支持核心轨道参数和默认角参数。mission_context 是可选加分项，"
        "可通过“补充 / 修改当前方案”自然语言输入补充；它只用于 RAG-enhanced design advisor 和设计评审，"
        "不参与 core orbit gate，也不触发 deterministic tools。"
    )

    edited_rows = render_confirmation_table(items)
    patch, errors = collect_confirmation_patch(items, edited_rows)
    for error in errors:
        st.warning(error)

    selected_count = len((patch or {}).get("engineering_parameters") or {})
    if st.button(
        "应用所选确认",
        width="stretch",
        disabled=selected_count == 0 or bool(errors),
        help="只应用已勾选且 user value 有效的字段；不会自动应用 advisor 建议。",
    ):
        st.session_state["pending_confirmation_patch"] = patch
        st.rerun()


def build_confirmation_items(design_state: dict[str, Any]) -> list[dict[str, Any]]:
    params = design_state.get("normalized_parameters") or {}
    advisor_report = design_state.get("advisor_report") or {}
    actions = [_normalize_action(action) for action in _action_list(advisor_report.get("next_actions"))]
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_item(
        field: str,
        *,
        issue: str,
        action: str,
        priority: str,
        recommended_value: Any = "",
        recommended_unit: str | None = None,
        blocking: bool = False,
    ) -> None:
        normalized_field = _normalize_confirmation_field(field)
        if normalized_field not in CONFIRMATION_SUPPORTED_FIELDS or normalized_field in seen:
            return
        seen.add(normalized_field)
        entry = params.get(normalized_field, {}) if isinstance(params.get(normalized_field), dict) else {}
        current_value = entry.get("value")
        current_unit = entry.get("unit") or CONFIRMATION_DEFAULT_UNITS.get(normalized_field, "")
        if recommended_value in (None, "") and current_value not in (None, ""):
            recommended_value = current_value
        if recommended_unit is None:
            recommended_unit = current_unit
        items.append(
            {
                "apply": False,
                "field": normalized_field,
                "current_value": current_value,
                "current_unit": current_unit,
                "current_source": entry.get("source") or "not_found",
                "issue": issue,
                "recommended_value": "" if recommended_value is None else recommended_value,
                "user_value": "" if recommended_value is None else recommended_value,
                "unit": recommended_unit or "",
                "action": action,
                "priority": priority,
                "blocking": blocking,
            }
        )

    for field in design_state.get("missing_core_elements") or []:
        normalized_field = _normalize_confirmation_field(str(field))
        if normalized_field == "orbit_inclination_deg":
            add_item(
                normalized_field,
                issue="缺少 core orbit gate 所需轨道倾角。51.6 deg 只是示例值，用户可修改。",
                action="added",
                priority="high",
                recommended_value="51.6",
                recommended_unit="deg",
                blocking=True,
            )
        else:
            add_item(
                normalized_field,
                issue="缺少 core orbit gate 所需核心轨道参数。",
                action="added",
                priority="high",
                recommended_value="",
                recommended_unit=CONFIRMATION_DEFAULT_UNITS.get(normalized_field, ""),
                blocking=True,
            )

    severe_items = []
    for item in (design_state.get("consistency_issues") or []) + (design_state.get("validation_results") or []):
        item_dict = _to_dict(item)
        if item_dict.get("level") == "severe":
            severe_items.append(item_dict)
    for item in severe_items:
        field = _normalize_confirmation_field(
            str(item.get("field") or item.get("param_key") or item.get("display_name") or "")
        )
        message = str(item.get("message") or "存在 severe consistency issue，需要用户确认。")
        if field == "eccentricity" or _message_mentions_eccentricity(message):
            add_item(
                "eccentricity",
                issue=f"{message} 修复方向 1：改为圆轨道，确认 eccentricity = 0。",
                action="modified",
                priority="high",
                recommended_value="0",
                recommended_unit="",
                blocking=True,
            )
            current_ecc = (params.get("eccentricity") or {}).get("value")
            add_item(
                "orbit_type",
                issue=(
                    "修复方向 2：保留当前 eccentricity="
                    f"{_format_value(current_ecc)}，将轨道形状 / orbit_type 改为 elliptical orbit。"
                ),
                action="modified",
                priority="high",
                recommended_value="elliptical orbit",
                recommended_unit="",
                blocking=True,
            )

    for item in design_state.get("default_assumptions") or []:
        if not isinstance(item, dict):
            continue
        field = _normalize_confirmation_field(str(item.get("field") or ""))
        if field not in {"raan_deg", "arg_perigee_deg", "true_anomaly_deg"}:
            continue
        add_item(
            field,
            issue="当前值来自 default_assumption，需要用户确认后才可视为显式约束。",
            action="confirmed",
            priority="medium",
            recommended_value=item.get("value") if item.get("value") is not None else 0,
            recommended_unit=item.get("unit") or "deg",
            blocking=False,
        )

    for action in actions:
        field = _field_from_action(action)
        if not field:
            continue
        add_item(
            field,
            issue=action.get("reason") or "高优先级 Agent Action 建议用户确认该参数。",
            action="added" if field == "orbit_inclination_deg" else "modified",
            priority=action.get("priority") or "high",
            recommended_value="51.6" if field == "orbit_inclination_deg" else "",
            recommended_unit=CONFIRMATION_DEFAULT_UNITS.get(field, ""),
            blocking=action.get("priority") == "high",
        )

    return items[:8]


def render_confirmation_table(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in items:
        rows.append(
            {
                "apply": bool(item.get("apply", False)),
                "priority": item.get("priority", "medium"),
                "field": item.get("field", ""),
                "current value": _format_value_with_unit(item.get("current_value"), item.get("current_unit")),
                "source": item.get("current_source") or "not_found",
                "issue": item.get("issue", ""),
                "recommended value": _format_value(item.get("recommended_value")),
                "user value": _format_value(item.get("user_value")),
                "unit": item.get("unit", ""),
                "action": item.get("action", "confirmed"),
                "blocking": "是" if item.get("blocking") else "否",
            }
        )

    edited = st.data_editor(
        rows,
        key="confirmation_table_editor",
        width="stretch",
        hide_index=True,
        column_config={
            "apply": st.column_config.CheckboxColumn("apply", help="勾选后才会写入 confirmation_patch"),
            "priority": st.column_config.TextColumn("priority", disabled=True),
            "field": st.column_config.TextColumn("field", disabled=True),
            "current value": st.column_config.TextColumn("current value", disabled=True),
            "source": st.column_config.TextColumn("source", disabled=True),
            "issue": st.column_config.TextColumn("issue", disabled=True),
            "recommended value": st.column_config.TextColumn("recommended value", disabled=True),
            "user value": st.column_config.TextColumn("user value"),
            "unit": st.column_config.SelectboxColumn("unit", options=["", "deg"]),
            "action": st.column_config.TextColumn("action", disabled=True),
            "blocking": st.column_config.TextColumn("blocking", disabled=True),
        },
    )
    return _table_records(edited)


def _normalize_confirmation_field(field: str) -> str:
    mapping = {
        "orbit_type": "orbit_type",
        "orbit type": "orbit_type",
        "orbit_shape": "orbit_type",
        "orbit shape": "orbit_type",
        "inclination_deg": "orbit_inclination_deg",
        "inclination": "orbit_inclination_deg",
        "轨道倾角": "orbit_inclination_deg",
        "倾角": "orbit_inclination_deg",
        "eccentricity": "eccentricity",
        "偏心率": "eccentricity",
        "raan": "raan_deg",
        "raan_deg": "raan_deg",
        "arg_perigee": "arg_perigee_deg",
        "arg_perigee_deg": "arg_perigee_deg",
        "argument of perigee": "arg_perigee_deg",
        "近地点幅角": "arg_perigee_deg",
        "true_anomaly": "true_anomaly_deg",
        "true_anomaly_deg": "true_anomaly_deg",
        "true anomaly": "true_anomaly_deg",
        "真近点角": "true_anomaly_deg",
    }
    normalized = field.strip()
    return mapping.get(normalized, mapping.get(normalized.lower(), normalized))


def _message_mentions_eccentricity(message: str) -> bool:
    lower = message.lower()
    return any(token in lower for token in ("eccentricity", "circular", "偏心", "圆轨道", "非零"))


def _field_from_action(action: dict[str, str]) -> str:
    text = " ".join(
        str(action.get(key) or "")
        for key in ("title", "reason", "suggested_user_reply")
    ).lower()
    if "inclination" in text or "倾角" in text:
        return "orbit_inclination_deg"
    if "orbit_type" in text or "orbit type" in text or "elliptical" in text:
        return "orbit_type"
    if "eccentricity" in text or "偏心" in text:
        return "eccentricity"
    if "raan" in text:
        return "raan_deg"
    if "arg_perigee" in text or "argument of perigee" in text or "近地点幅角" in text:
        return "arg_perigee_deg"
    if "true_anomaly" in text or "true anomaly" in text or "真近点角" in text:
        return "true_anomaly_deg"
    return ""


def _table_records(table_data: Any) -> list[dict[str, Any]]:
    if hasattr(table_data, "to_dict"):
        try:
            return list(table_data.to_dict("records"))
        except TypeError:
            return []
    if isinstance(table_data, list):
        return [row for row in table_data if isinstance(row, dict)]
    if isinstance(table_data, dict):
        return [row for row in table_data.values() if isinstance(row, dict)]
    return []


def _parse_confirmation_number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def _format_value_with_unit(value: Any, unit: Any) -> str:
    if value in (None, ""):
        return "-"
    suffix = f" {unit}" if unit not in (None, "") else ""
    return f"{_format_value(value)}{suffix}"


def _confirmation_patch_note(engineering: dict[str, dict[str, Any]]) -> str:
    parts = []
    for field, entry in engineering.items():
        value = entry.get("value")
        if value in (None, ""):
            continue
        unit = entry.get("unit") or ""
        suffix = f" {unit}" if unit else ""
        action = entry.get("action") or "confirmed"
        parts.append(f"{field}={value}{suffix} {action}")
    joined = "; ".join(parts) if parts else "no valid selected fields"
    return f"确认表单：{joined}"


def validate_confirmation_value(field: str, value: Any) -> str | None:
    """Return a Chinese validation message when a confirmation value is invalid."""

    if field == "orbit_type":
        if str(value or "").strip():
            return None
        return "轨道类型不能为空。"

    numeric_value = _parse_confirmation_number(value)
    if numeric_value is None:
        return f"{field} 的 user value 无效，请输入数字。"
    if field == "orbit_inclination_deg" and not (0.0 <= numeric_value <= 180.0):
        return "倾角应在 0–180 deg 范围内。"
    if field == "eccentricity" and not (0.0 <= numeric_value < 1.0):
        return "eccentricity 应满足 0 <= e < 1。"
    if field == "raan_deg" and not (0.0 <= numeric_value < 360.0):
        return "RAAN 应在 0–360 deg 范围内，且小于 360 deg。"
    if field == "arg_perigee_deg" and not (0.0 <= numeric_value < 360.0):
        return "近地点幅角应在 0–360 deg 范围内，且小于 360 deg。"
    if field == "true_anomaly_deg" and not (0.0 <= numeric_value < 360.0):
        return "真近点角应在 0–360 deg 范围内，且小于 360 deg。"
    return None


def collect_confirmation_patch(
    items: list[dict[str, Any]],
    edited_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    item_by_field = {item.get("field"): item for item in items}
    engineering: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    for row in edited_rows:
        if not row.get("apply"):
            continue
        field = str(row.get("field") or "")
        if field not in item_by_field or field not in CONFIRMATION_SUPPORTED_FIELDS:
            continue

        raw_value = row.get("user value")
        error = validate_confirmation_value(field, raw_value)
        if error:
            errors.append(error)
            continue

        unit = str(row.get("unit") or CONFIRMATION_DEFAULT_UNITS.get(field, ""))
        if field == "orbit_type":
            value: Any = str(raw_value).strip()
            unit = ""
        else:
            value = _parse_confirmation_number(raw_value)
            if field == "eccentricity":
                unit = ""
            elif unit != "deg":
                errors.append(f"{field} 当前仅支持 deg 单位。")
                continue

        engineering[field] = {
            "value": value,
            "unit": unit,
            "source": "user_confirmed",
            "status": "user_confirmed",
            "requires_confirmation": False,
            "confirmation_source": CONFIRMATION_FORM_SOURCE,
            "action": row.get("action") or item_by_field[field].get("action") or "confirmed",
        }

    patch = {
        "source": CONFIRMATION_FORM_SOURCE,
        "raw_action_note": _confirmation_patch_note(engineering),
        "engineering_parameters": engineering,
        "mission_context": {},
    }
    return patch, errors


def _suggested_reply_for_missing(field: str, actions: list[dict[str, str]]) -> str:
    field_lower = field.lower()
    if "inclination" in field_lower or "倾角" in field:
        return "倾角用51.6度，或说明采用 SSO / polar / equatorial。"
    for action in actions:
        if action.get("priority") == "high" and action.get("suggested_user_reply"):
            return action["suggested_user_reply"]
    return f"请补充 {_reply_field_name(field)}=..."


def _reply_field_name(field: str) -> str:
    return {
        "raan_deg": "RAAN",
        "arg_perigee_deg": "argument of perigee",
        "true_anomaly_deg": "true anomaly",
        "orbit_inclination_deg": "inclination",
        "inclination_deg": "inclination",
        "eccentricity": "eccentricity",
    }.get(field, field)


def _suggested_reply_for_issue(field: str, message: str, actions: list[dict[str, str]]) -> str:
    combined = f"{field} {message}".lower()
    if "eccentricity" in combined or "偏心" in combined:
        return "改为圆轨道，偏心率用0；或：保留 eccentricity=0.10，轨道类型改为 elliptical orbit。"
    for action in actions:
        if action.get("priority") == "high" and action.get("suggested_user_reply"):
            return action["suggested_user_reply"]
    return "请确认该参数，并给出修正后的显式输入。"


def _normalize_execution_entries(entries: list[Any] | None) -> list[dict[str, Any]]:
    normalized = []
    for index, entry in enumerate(entries or [], start=1):
        if isinstance(entry, dict):
            item = dict(entry)
            item.setdefault("sequence", index)
            item.setdefault("event_type", "legacy")
            item.setdefault("message", "")
            item.setdefault("details", {})
            normalized.append(item)
        else:
            normalized.append(
                {
                    "sequence": index,
                    "timestamp": "",
                    "round": None,
                    "event_type": "legacy",
                    "message": str(entry),
                    "details": {},
                }
            )
    return normalized


def _format_execution_log_line(entry: dict[str, Any]) -> str:
    event_type = entry.get("event_type") or "legacy"
    label = EVENT_TYPE_LABELS.get(event_type, event_type)
    round_value = entry.get("round")
    round_text = f"R{round_value}" if round_value not in (None, "") else "R-"
    timestamp = entry.get("timestamp") or "--:--:--"
    message = entry.get("message") or ""
    return f"[{timestamp}] [{round_text}] {label}：{message}"


def _execution_log_detail_rows(details: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for key, value in details.items():
        rows.append({"字段": str(key), "值": _compact_detail_value(value)})
    return rows

def _compact_detail_value(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        preview = ", ".join(str(item) for item in items[:8])
        return preview + (" ..." if len(items) > 8 else "")
    if isinstance(value, dict):
        pairs = list(value.items())[:8]
        preview = "; ".join(f"{key}={val}" for key, val in pairs)
        return preview + (" ..." if len(value) > 8 else "")
    return str(value)


def render_execution_log(entries: list[Any] | None) -> None:
    st.markdown('<div class="section-title">6. 执行日志区域</div>', unsafe_allow_html=True)
    log_entries = _normalize_execution_entries(entries)
    if not log_entries:
        st.markdown("暂无执行日志。")
        return

    visible_entries = log_entries[-20:]
    html_lines = "".join(
        f'<div class="log-line">{html.escape(_format_execution_log_line(entry))}</div>'
        for entry in visible_entries
    )
    st.markdown(f'<div class="log-box">{html_lines}</div>', unsafe_allow_html=True)

    detail_entries = [entry for entry in visible_entries if entry.get("details")]
    if detail_entries:
        with st.expander("查看日志详情", expanded=False):
            for entry in detail_entries:
                st.markdown(f"**{_format_execution_log_line(entry)}**")
                detail_rows = _execution_log_detail_rows(entry.get("details") or {})
                if detail_rows:
                    st.dataframe(detail_rows, width="stretch", hide_index=True)


def render_debug_panel(
    *,
    params: dict[str, Any] | None,
    validation_results: Iterable[Any] | None,
    orbit_metadata: dict[str, Any] | None,
    orbit_conflicts: Iterable[Any] | None,
    task_results: list[dict[str, Any]] | None,
    execute_all_tasks_called: bool,
    skip_reason: str | None,
) -> None:
    metadata = (params or {}).get("_extraction_metadata", {})
    safe_params = {
        key: value for key, value in (params or {}).items()
        if not key.startswith("_")
    }

    with st.expander("高级调试信息", expanded=False):
        st.write("LLM 配置")
        st.json({
            "llm_api_key_present": metadata.get("llm_api_key_present", False),
            "llm_base_url": metadata.get("llm_base_url"),
            "llm_model": metadata.get("llm_model"),
            "llm_timeout_seconds": metadata.get("llm_timeout_seconds"),
        })
        st.write("参数提取元数据")
        st.json({
            "extraction_mode": metadata.get("extraction_mode"),
            "llm_status": metadata.get("llm_status"),
            "fallback_reason": metadata.get("fallback_reason"),
            "normalization_source": metadata.get("normalization_source"),
            "execute_all_tasks_called": execute_all_tasks_called,
            "execute_all_tasks_skip_reason": skip_reason,
        })
        st.write("LLM raw response")
        st.code(metadata.get("llm_raw_response") or "N/A", language="json")
        st.write("Parsed LLM JSON")
        st.json(metadata.get("llm_parsed_json") or {})
        st.write("Explicit params")
        st.json(metadata.get("explicit_params") or {})
        st.write("Normalized params")
        st.json(safe_params)
        st.write("Mission context")
        st.json((params or {}).get("_mission_context") or metadata.get("mission_context") or {})
        st.write("Inference metadata")
        st.json((params or {}).get("_inference_metadata") or {})
        st.write("Validation raw result")
        st.json([_to_dict(item) for item in (validation_results or [])])
        st.write("Orbit metadata")
        st.json(orbit_metadata or {})
        st.write("Orbit consistency conflicts")
        st.json([_to_dict(item) for item in (orbit_conflicts or [])])
        st.write("Task results")
        st.json(task_results or [])


def render_report_download(report: str, filename: str, label: str, path: str) -> None:
    st.download_button(
        label=label,
        data=report,
        file_name=filename,
        mime="text/markdown",
    )
    st.caption(f"报告已自动保存至：`{path}`")


def _design_summary_rows(design_state: dict[str, Any]) -> list[dict[str, Any]]:
    params = design_state.get("normalized_parameters") or {}
    context = design_state.get("mission_context") or {}
    rows: list[dict[str, Any]] = []

    rows.extend(_param_summary_row(params, "orbit_type", "轨道", "orbit_type / orbit_class"))
    orbit_shape = _orbit_shape_text(params)
    if orbit_shape != "-":
        rows.append(_summary_row("轨道", "orbit_shape", orbit_shape, "current_design_state"))
    for key, label in (
        ("orbit_altitude_km", "orbit_altitude_km"),
        ("semi_major_axis_km", "semi_major_axis_km"),
        ("orbit_inclination_deg", "orbit_inclination_deg"),
        ("eccentricity", "eccentricity"),
        ("orbit_period_min", "orbit_period_min"),
        ("raan_deg", "raan_deg"),
        ("arg_perigee_deg", "arg_perigee_deg"),
        ("true_anomaly_deg", "true_anomaly_deg"),
    ):
        rows.extend(_param_summary_row(params, key, "轨道", label))

    for key, label in (
        ("payload_mass_kg", "payload_mass_kg"),
        ("power_required_w", "payload_power_W"),
        ("satellite_mass_kg", "satellite_mass_kg"),
        ("mission_lifetime_years", "mission_lifetime_year"),
    ):
        rows.extend(_param_summary_row(params, key, "载荷 / 平台", label))

    rows.extend(_mission_context_summary_rows(context))

    core_gate = "通过" if not (design_state.get("missing_core_elements") or []) else "未通过"
    severe_count = _issue_level_count(design_state, "severe")
    warning_count = _issue_level_count(design_state, "warning")
    rows.extend(
        [
            _summary_row("状态", "report_status", design_state.get("report_status") or "未运行", "pipeline"),
            _summary_row("状态", "core gate", core_gate, "orbit_metadata"),
            _summary_row("状态", "severe issue 数量", str(severe_count), "validation / orbit_consistency"),
            _summary_row("状态", "warning 数量", str(warning_count), "validation / orbit_consistency"),
            _summary_row("状态", "当前仍缺参数", _current_missing_text(design_state), "validation / orbit_gate"),
            _summary_row("状态", "默认假设确认", _default_confirmation_text(design_state), "current_design_state"),
        ]
    )
    return rows or [_summary_row("状态", "当前方案", "尚无可用工程参数", "current_design_state")]


def _build_equivalent_design_description(design_state: dict[str, Any]) -> str:
    params = design_state.get("normalized_parameters") or {}
    parts = []
    orbit_type = _param_value_text(params, "orbit_type")
    if orbit_type != "-":
        parts.append(orbit_type)
    shape = _orbit_shape_text(params)
    if shape != "-" and shape not in parts:
        parts.append(shape)
    for key, prefix in (
        ("orbit_altitude_km", ""),
        ("orbit_inclination_deg", "倾角"),
        ("eccentricity", "偏心率"),
        ("payload_mass_kg", "载荷"),
        ("power_required_w", "功率"),
    ):
        text = _param_value_text(params, key)
        if text != "-":
            parts.append(f"{prefix}{text}" if prefix else text)

    context_summary = _mission_context_summary(design_state.get("mission_context") or {})
    if context_summary != "未提供":
        parts.append(context_summary)
    missing_text = _current_missing_text(design_state)
    if missing_text != "无核心缺失项":
        parts.append(f"当前仍缺 {missing_text}")
    return "，".join(parts) if parts else "当前方案尚无可用工程参数。"


def _summary_row(category: str, item: str, value: Any, source: str) -> dict[str, Any]:
    return {
        "类别": category,
        "项目": item,
        "当前值": _format_value(value) if value not in (None, "") else "-",
        "来源/状态": source,
    }


def _param_summary_row(
    params: dict[str, Any],
    key: str,
    category: str,
    label: str,
) -> list[dict[str, Any]]:
    text = _param_value_text(params, key)
    if text == "-":
        return []
    return [_summary_row(category, label, text, _param_source_text(params, key))]


def _mission_context_summary_rows(context: dict[str, Any]) -> list[dict[str, Any]]:
    labels = {
        "mission_type": "mission_type",
        "payload_type": "payload_type",
        "target_region": "target_region",
        "revisit_time_h": "revisit_time_h",
        "ground_resolution_m": "ground_resolution_m",
        "swath_width_km": "swath_width_km",
        "daily_data_volume_GB": "daily_data_volume_GB",
        "downlink_rate_Mbps": "downlink_rate_Mbps",
    }
    rows = []
    for key, label in labels.items():
        value = context.get(key)
        if value not in (None, "", []):
            rows.append(_summary_row("mission_context", label, value, "mission_context / read_only"))
    return rows


def _issue_level_count(design_state: dict[str, Any], level: str) -> int:
    items = list(design_state.get("validation_results") or [])
    items.extend(design_state.get("consistency_issues") or [])
    return sum(1 for item in items if _to_dict(item).get("level") == level)


def _default_confirmation_text(design_state: dict[str, Any]) -> str:
    fields = []
    for item in design_state.get("default_assumptions") or []:
        if not isinstance(item, dict):
            continue
        if item.get("requires_confirmation", True):
            field = item.get("field")
            if field:
                fields.append(str(field))
    return "仍需确认：" + "，".join(fields) if fields else "无待确认默认假设"


def _last_confirmation_rows(design_state: dict[str, Any]) -> list[dict[str, Any]]:
    patch_view = design_state.get("patch_view") or {}
    if patch_view.get("source") != CONFIRMATION_FORM_SOURCE:
        return []

    rows = []
    for item in (patch_view.get("added") or []) + (patch_view.get("modified") or []):
        action = item.get("action") or "-"
        if action not in {"added", "modified", "confirmed"}:
            continue
        old_value = _format_value_with_unit(item.get("previous_value"), item.get("previous_unit"))
        new_value = _format_value_with_unit(item.get("value"), item.get("unit"))
        rows.append(
            {
                "confirmed_at_round": item.get("confirmed_at_round") or patch_view.get("confirmed_at_round") or "-",
                "action": action,
                "field": item.get("field") or "-",
                "old value -> new value": f"{old_value} -> {new_value}",
                "old source -> new source": f"{item.get('previous_source') or '-'} -> {item.get('new_source') or item.get('source') or '-'}",
                "category": item.get("category") or "-",
            }
        )
    return rows


def _param_value_text(params: dict[str, Any], key: str) -> str:
    entry = params.get(key, {}) if isinstance(params.get(key), dict) else {}
    if not entry.get("found") or entry.get("value") is None:
        return "-"
    return _format_value_with_unit(entry.get("value"), entry.get("unit"))


def _param_source_text(params: dict[str, Any], key: str) -> str:
    entry = params.get(key, {}) if isinstance(params.get(key), dict) else {}
    source = entry.get("source") or "not_found"
    source_text = SOURCE_LABELS.get(source, source)
    if entry.get("requires_confirmation"):
        source_text += " / 需确认"
    return source_text


def _orbit_shape_text(params: dict[str, Any]) -> str:
    orbit_type = str((params.get("orbit_type") or {}).get("value") or "").lower()
    if "circular" in orbit_type:
        return "圆轨道"
    if "elliptical" in orbit_type or orbit_type == "heo":
        return "椭圆轨道"
    ecc_entry = params.get("eccentricity", {}) if isinstance(params.get("eccentricity"), dict) else {}
    ecc = ecc_entry.get("value")
    if ecc is None:
        return "-"
    try:
        return "圆轨道" if abs(float(ecc)) <= 1e-6 else "非零偏心率轨道"
    except (TypeError, ValueError):
        return "-"


def _mission_context_summary(context: dict[str, Any]) -> str:
    labels = {
        "mission_type": "任务",
        "target_region": "区域",
        "payload_type": "载荷",
        "revisit_time_h": "重访",
        "ground_resolution_m": "分辨率",
        "swath_width_km": "幅宽",
        "daily_data_volume_GB": "日数据量",
        "downlink_rate_Mbps": "下行速率",
    }
    parts = []
    for key, label in labels.items():
        value = context.get(key)
        if value not in (None, "", []):
            parts.append(f"{label}:{_format_value(value)}")
    return "；".join(parts) if parts else "未提供"


def _current_missing_text(design_state: dict[str, Any]) -> str:
    names: list[str] = []
    names.extend(str(item) for item in design_state.get("missing_core_elements") or [] if item)
    for item in design_state.get("missing_parameters") or []:
        if not isinstance(item, dict):
            continue
        name = item.get("parameter") or item.get("description")
        if name:
            names.append(str(name))
    deduped = _dedupe(names)
    return "，".join(deduped) if deduped else "无核心缺失项"


def _render_patch_rows(
    rows: list[dict[str, Any]],
    *,
    empty_text: str,
    show_previous: bool = False,
) -> None:
    if not rows:
        st.markdown(empty_text)
        return

    table_rows = []
    for item in rows:
        value_text = _format_value(item.get("value"))
        previous_value_text = _format_value(item.get("previous_value"))
        unit = item.get("unit") or "-"
        previous_unit = item.get("previous_unit") or unit
        row = {
            "field": item.get("field", "-"),
            "value": value_text,
            "unit": unit,
            "source": item.get("source") or "-",
            "action": item.get("action") or "-",
            "status": item.get("status") or "-",
            "requires_confirmation": bool(item.get("requires_confirmation")),
            "category": item.get("category") or item.get("kind") or "-",
            "round": item.get("round_label") or "-",
            "confirmed_at_round": item.get("confirmed_at_round") or "-",
            "patch_source": item.get("patch_source") or item.get("merge_source") or "-",
            "origin": item.get("update_origin") or "-",
        }
        if item.get("previous_source") or item.get("new_source"):
            row["source_change"] = f"{item.get('previous_source') or '-'} -> {item.get('new_source') or item.get('source') or '-'}"
        if show_previous:
            row["old_value"] = previous_value_text
            row["old_unit"] = previous_unit
            row["new_value"] = value_text
            row["new_unit"] = unit
            row["change"] = f"{previous_value_text} {previous_unit} -> {value_text} {unit}".strip()
            row["old value -> new value"] = row["change"]
        table_rows.append(row)
    st.dataframe(table_rows, width="stretch", hide_index=True)


def _intent_rows(context: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"项目": "输入类型", "识别结果": context.get("input_type") or "未明确", "状态": _known_status(context.get("input_type"))},
        {"项目": "任务目标", "识别结果": context.get("mission_objective") or "未明确", "状态": _known_status(context.get("mission_objective"))},
        {"项目": "目标区域", "识别结果": context.get("target_region") or "未明确", "状态": _known_status(context.get("target_region"))},
        {"项目": "重访/访问需求", "识别结果": _format_hours(context.get("revisit_requirement_hours")), "状态": _known_status(context.get("revisit_requirement_hours"))},
        {"项目": "载荷类型提示", "识别结果": context.get("payload_type_hint") or "未明确", "状态": _known_status(context.get("payload_type_hint"))},
        {
            "项目": "性能需求",
            "识别结果": _format_requirements(context.get("performance_requirements", [])),
            "状态": _known_status(context.get("performance_requirements")),
        },
    ]


def _orbital_element_rows(
    orbit_metadata: dict[str, Any] | None,
    inactive: bool,
) -> list[dict[str, Any]]:
    if inactive or not orbit_metadata:
        return [
            {
                "参数": label,
                "数值": "-",
                "单位": "-",
                "来源": "未解析",
                "状态": "尚未解析",
                "需确认": "-",
            }
            for _, label in ORBIT_ELEMENT_DISPLAY
        ]

    rows = []
    for row in orbit_metadata.get("element_table", []):
        status = row.get("status") or "missing"
        source = row.get("source") or "not_found"
        requires_confirmation = bool(row.get("requires_confirmation", False))
        status_label = STATUS_LABELS.get(status, status)
        if row.get("value") is None:
            status_label = "缺失"
        elif requires_confirmation and status_label not in {"缺失", "默认假设"}:
            status_label = "需确认"

        rows.append({
            "参数": _element_label(row.get("element")),
            "数值": _format_value(row.get("value")),
            "单位": row.get("unit") or "-",
            "来源": SOURCE_LABELS.get(source, source),
            "状态": status_label,
            "需确认": "是" if requires_confirmation else "否",
        })
    return rows


def _task_parameter_rows(
    params: dict[str, Any] | None,
    inactive: bool,
) -> list[dict[str, Any]]:
    rows = []
    for key, label, fallback_unit in TASK_PARAM_DISPLAY:
        if inactive or not params:
            rows.append({
                "参数": label,
                "数值": "-",
                "单位": fallback_unit or "-",
                "来源": "未解析",
                "状态": "尚未解析",
            })
            continue

        entry = params.get(key, {})
        found = bool(entry.get("found")) and entry.get("value") is not None
        source = entry.get("source") if found else "not_found"
        rows.append({
            "参数": label,
            "数值": _format_value(entry.get("value")) if found else "未提供",
            "单位": entry.get("unit") or fallback_unit or "-",
            "来源": SOURCE_LABELS.get(source, source),
            "状态": _task_status(entry, found),
        })
    return rows


def _task_status(entry: dict[str, Any], found: bool) -> str:
    if not found:
        return "缺失"
    if entry.get("requires_confirmation"):
        return "需确认"
    status = entry.get("status") or entry.get("source") or "available"
    return STATUS_LABELS.get(status, "已提供")


def _element_label(element: str | None) -> str:
    labels = dict(ORBIT_ELEMENT_DISPLAY)
    return labels.get(element or "", element or "-")


def _format_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def _known_status(value: Any) -> str:
    return "已识别" if value else "待补充"


def _format_requirements(requirements: list[dict[str, Any]]) -> str:
    if not requirements:
        return "未明确"
    parts = []
    for item in requirements:
        unit = item.get("unit") or ""
        parts.append(f"{item.get('name')}: {item.get('value')} {unit}".strip())
    return "; ".join(parts)


def _format_hours(value: Any) -> str:
    if value is None:
        return "未明确"
    return f"{_format_value(value)} hours"


def _draft_overview_rows(drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for draft in drafts:
        rows.append({
            "草案": draft.get("draft_name"),
            "轨道候选": draft.get("orbit_type_candidate"),
            "高度": draft.get("altitude_range_or_value"),
            "倾角提示": draft.get("inclination_hint_or_range"),
            "载荷提示": draft.get("payload_type_hint"),
            "置信度": _format_value(draft.get("confidence")),
            "验证状态": draft.get("verification_status"),
            "需确认": "是" if draft.get("requires_confirmation", True) else "否",
        })
    return rows


def _draft_parameter_rows(draft: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "参数": key,
            "候选值": _format_value(value),
            "来源": "llm_inferred / conceptual_draft",
            "验证状态": draft.get("verification_status", "not_verified"),
        }
        for key, value in (draft.get("parameter_values") or {}).items()
    ]


def _summary_html(kind: str, messages: list[str]) -> None:
    items = "".join(f"<li>{html.escape(message)}</li>" for message in messages)
    st.markdown(
        f'<div class="summary-box {kind}"><ul>{items}</ul></div>',
        unsafe_allow_html=True,
    )


def _validation_by_level(items: Iterable[Any] | None, level: str) -> list[dict[str, Any]]:
    return [
        data for data in (_to_dict(item) for item in (items or []))
        if data.get("level") == level
    ]


def _conflicts_by_level(items: Iterable[Any] | None, level: str) -> list[dict[str, Any]]:
    return [
        data for data in (_to_dict(item) for item in (items or []))
        if data.get("level") == level
    ]


def _to_dict(item: Any) -> dict[str, Any]:
    if hasattr(item, "to_dict"):
        return item.to_dict()
    if isinstance(item, dict):
        return item
    return {"value": str(item)}


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


# ---------------------------------------------------------------------------
# New helpers for parameter understanding panel
# ---------------------------------------------------------------------------


def _explicit_param_rows(params: dict[str, Any]) -> list[dict[str, Any]]:
    """Build rows for explicit (user-provided) parameters."""
    rows = []
    for key, label, fallback_unit in TASK_PARAM_DISPLAY + ORBIT_ELEMENT_PARAM_DISPLAY:
        entry = params.get(key, {})
        source = entry.get("source", "not_found")
        if source not in PARAM_SOURCE_CATEGORIES.get("explicit", set()):
            continue
        found = bool(entry.get("found")) and entry.get("value") is not None
        rows.append({
            "参数": label,
            "数值": _format_value(entry.get("value")) if found else "未提供",
            "单位": entry.get("unit") or fallback_unit or "-",
            "来源": SOURCE_LABELS.get(source, source),
            "状态": _task_status(entry, found),
            "需确认": "是" if entry.get("requires_confirmation") else "否",
        })
    return rows


def _inferred_param_rows(
    params: dict[str, Any],
    orbit_metadata: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Build rows for system-inferred parameters."""
    rows = []
    inferred_fields = set((orbit_metadata or {}).get("inferred_parameters", []))
    for key, label, fallback_unit in TASK_PARAM_DISPLAY:
        entry = params.get(key, {})
        source = entry.get("source", "not_found")
        if source not in PARAM_SOURCE_CATEGORIES.get("inferred", set()) and key not in inferred_fields:
            continue
        found = bool(entry.get("found")) and entry.get("value") is not None
        rows.append({
            "参数": label,
            "数值": _format_value(entry.get("value")) if found else "未提供",
            "单位": entry.get("unit") or fallback_unit or "-",
            "来源": SOURCE_LABELS.get(source, source),
            "状态": _task_status(entry, found),
            "需确认": "是" if entry.get("requires_confirmation") else "否",
        })
    # Also add orbital elements that were inferred
    for row in (orbit_metadata or {}).get("element_table", []):
        source = row.get("source", "not_found")
        if source in PARAM_SOURCE_CATEGORIES.get("inferred", set()):
            rows.append({
                "参数": _element_label(row.get("element")),
                "数值": _format_value(row.get("value")),
                "单位": row.get("unit") or "-",
                "来源": SOURCE_LABELS.get(source, source),
                "状态": "已推断" if row.get("value") is not None else "缺失",
                "需确认": "是" if row.get("requires_confirmation") else "否",
            })
    return rows


def _default_param_rows(
    params: dict[str, Any],
    orbit_metadata: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Build rows for default-assumption parameters."""
    rows = []
    for key, label, fallback_unit in TASK_PARAM_DISPLAY:
        entry = params.get(key, {})
        source = entry.get("source", "not_found")
        if source not in PARAM_SOURCE_CATEGORIES.get("default", set()):
            continue
        rows.append({
            "参数": label,
            "数值": _format_value(entry.get("value")),
            "单位": entry.get("unit") or fallback_unit or "-",
            "来源": SOURCE_LABELS.get(source, source),
            "状态": "默认假设",
            "需确认": "是",
        })
    # Also add defaulted orbital elements
    for row in (orbit_metadata or {}).get("element_table", []):
        source = row.get("source", "not_found")
        if source in PARAM_SOURCE_CATEGORIES.get("default", set()):
            rows.append({
                "参数": _element_label(row.get("element")),
                "数值": _format_value(row.get("value")),
                "单位": row.get("unit") or "-",
                "来源": SOURCE_LABELS.get(source, source),
                "状态": "默认假设",
                "需确认": "是",
            })
    return rows


def _missing_param_rows(
    params: dict[str, Any],
    missing_params: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Build rows for missing / to-be-confirmed parameters."""
    rows = []

    # From missing_params list
    for item in missing_params or []:
        severity = item.get("severity", "recommended")
        desc = item.get("description", item.get("parameter", ""))
        rows.append({
            "参数": desc,
            "数值": "未提供",
            "单位": "-",
            "来源": "缺失",
            "状态": "缺失",
            "需确认": "是",
            "必需性": "必需" if severity == "required" else "建议",
        })

    # From params dict (not_found sources)
    for key, label, fallback_unit in TASK_PARAM_DISPLAY:
        entry = params.get(key, {})
        source = entry.get("source", "not_found")
        if source not in PARAM_SOURCE_CATEGORIES.get("missing", set()):
            continue
        # Avoid duplicates with missing_params
        if any(desc == label for desc in [m.get("description", "") for m in (missing_params or [])]):
            continue
        rows.append({
            "参数": label,
            "数值": "未提供",
            "单位": entry.get("unit") or fallback_unit or "-",
            "来源": SOURCE_LABELS.get(source, source),
            "状态": "缺失",
            "需确认": "是",
            "必需性": "建议",
        })

    return rows


def _consistency_rows(
    validation_results: Iterable[Any] | None,
    orbit_conflicts: Iterable[Any] | None,
) -> list[dict[str, Any]]:
    """Build rows for consistency check results."""
    rows = []

    for item in validation_results or []:
        data = item.to_dict() if hasattr(item, "to_dict") else item
        level = data.get("level", "pass")
        level_icon = {"severe": "🚫", "warning": "⚠️", "pass": "✅"}.get(level, "ℹ️")
        rows.append({
            "类型": "参数校验",
            "参数": data.get("display_name", data.get("param_key", "")),
            "级别": f"{level_icon} {level}",
            "信息": data.get("message", ""),
        })

    for item in orbit_conflicts or []:
        data = item.to_dict() if hasattr(item, "to_dict") else item
        level = data.get("level", "warning")
        level_icon = {"severe": "🚫", "warning": "⚠️"}.get(level, "ℹ️")
        rows.append({
            "类型": "轨道一致性",
            "参数": data.get("field", ""),
            "级别": f"{level_icon} {level}",
            "信息": data.get("message", ""),
        })

    return rows

