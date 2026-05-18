# Handoff to Codex

## 1. Current Project Goal

Spacecraft Conceptual Design AI Agent Demo: a lightweight Streamlit app for LEO remote-sensing small-satellite conceptual design. It must keep LLM reasoning separate from deterministic engineering calculations in `tools/`.

## 2. Implemented Features

- Dual UI modes:
  - `任务级需求模式`: beginner-facing Phase 2 guidance with mission understanding, missing constraints, candidate parameter drafts, and adopt-draft handoff into parameter-level flow.
  - `参数级设计模式`: professional parameter workflow with extraction, inference, validation, orbit consistency checks, tools, and report generation.
- LLM-first extraction with rules fallback and folded debug metadata.
- Mission intent metadata: objective, target region, performance requirements such as revisit time.
- Cautious missing-parameter inference: `llm_inferred` or `rules_inferred`, always traceable and confirmable.
- Orbit element table and completeness gate: requires `semi_major_axis_km`, `orbit_inclination_deg`.
- Orbit consistency checks: orbit type contradictions plus generic altitude/SMA/period consistency.
- Severe validation or severe orbit conflict blocks `execute_all_tasks()` and generates confirmation report.
- UI uses white scientific-console style; raw JSON/debug data stays in `高级调试信息`.
- RAG advisor scaffold (`agents/rag_retriever.py` + `agents/design_advisor.py`).
  - `rag_retriever.retrieve()` — keyword-based Markdown snippet retrieval from `docs/rag_knowledge/*.md`.
  - `design_advisor.generate_design_advice()` — produces a structured `advisor_report` dict; supports optional LLM synthesis (scaffold only, not yet wired).
  - Both modules are read-only, never modify parameters, never override tools, never decide core gate.
- **NEW: Mission context explicit extraction** (`agents/mission_context_extractor.py`):
  - Extracts only explicitly stated mission context (11 fields).
  - LLM context priority + rules fill. No inference, no gate participation.
- **NEW: Parameter understanding UI** — 6-tab display (explicit params, mission context, inferred params, default assumptions, missing/confirmation, consistency).
- **NEW: Flow status card** — shows pipeline status at top of results area.
- **NEW: Design advisor UI** — RAG advisor display with tabs after deterministic report.
- **NEW: Enhanced design_advisor** — `_fill_rule_based_advice()` generates Chinese rule-based advice without LLM.
- **NEW: Enhanced report_generator** — supports `mission_context` and `advisor_report` parameters; parameter table shows status/confirmation columns.

## 3. Key Call Chains

Task-level mode:

```text
user_text -> extract_mission_context()
-> build_mission_guidance()
-> show mission understanding + missing constraints + candidate drafts
-> if user adopts a draft:
     build_params_from_confirmed_draft()
     continue through parameter-level flow
```

Parameter-level mode:

```text
user_text -> extract_mission_parameters()
-> extract_mission_context()                          # NEW
-> validate_parameters(source_filter=explicit)
-> infer_missing_parameters()
-> identify_missing_parameters()
-> interpret_orbit_parameters()
-> validate_parameters()
-> validate_orbit_consistency()
-> if severe or missing core orbit elements:
     generate_parameter_confirmation_report(..., mission_context, advisor_report)
   else:
     execute_all_tasks()
     generate_report(..., mission_context, advisor_report)
-> render_status_card()                               # NEW
-> render_parameter_cards()
-> render_parameter_understanding_panel()             # NEW
-> render_summary_panel()
-> render_advisor_panel()                             # NEW
-> render_execution_log()
-> render_debug_panel()
-> render_report_download()
```

## 4. Latest Changes

Latest round added mission context extraction, parameter understanding UI, flow status card, enhanced RAG advisor, and design advisor UI. Files changed:

| File | Change |
|------|--------|
| `agents/mission_context_extractor.py` | **NEW** — Explicit mission context extraction (11 fields, no inference, no gate) |
| `agents/design_advisor.py` | **MODIFIED** — Added `_fill_rule_based_advice()` for Chinese rule-based fallback; supports `mission_context` and `default_assumptions` |
| `agents/report_generator.py` | **MODIFIED** — Added `mission_context` and `advisor_report` params; enhanced parameter table with status/confirmation columns |
| `ui_helpers.py` | **MODIFIED** — Added `render_parameter_understanding_panel()`, `render_status_card()`, `render_advisor_panel()` |
| `app.py` | **MODIFIED** — Integrated mission_context extraction and design_advisor calls into pipeline; added new UI rendering calls |
| `docs/project_status.md` | Updated capabilities, call chain, known issues, verification |
| `docs/change_log.md` | Added entry for this round |
| `docs/handoff_to_codex.md` | This update |

## 5. Known Issues

- Task-level mode is Phase 2 guidance; candidate drafts are conceptual and not engineering-verified.
- LLM missing-parameter inference is cautious and limited.
- Live DeepSeek calls are not covered by automated tests.
- Some generated report text/source labels may still need polish.
- Orbital mechanics remain conceptual; no high-fidelity propagation.
- **RAG advisor is scaffold-only**: `design_advisor._synthesise_with_llm()` is a placeholder (returns `None`). Codex must wire the actual LLM call.
- **`docs/rag_knowledge/` has minimal content** — only a few files exist; more knowledge content needed.
- **Multi-turn parameter confirmation is not yet implemented** — only UI and data structure preparation.
- **`mission_context_extractor` regex patterns are basic** — LLM extraction is preferred for complex expressions.
- **No automated tests for new UI functions** — manual browser verification needed.

## 6. Suggested Next Steps (for Codex)

1. **Implement `_synthesise_with_llm()`** — replace the placeholder with a real `chat.completions.create()` call using the same env vars as `agents/llm_extractor.py`. Parse the LLM JSON response into the `advisor_report` schema.
2. **Populate `docs/rag_knowledge/`** — add more Markdown files with spacecraft design reference material (e.g., `power_subsystem.md`, `orbit_types.md`, `mass_budget.md`). Keep snippets concise and relevant to the MVP scope.
3. **Add unit tests** — `pytest`-based tests for:
   - `mission_context_extractor.extract_mission_context()` with various inputs.
   - `design_advisor.generate_design_advice()` with and without LLM client.
   - `ui_helpers` new rendering functions (at least smoke tests).
4. **Browser-check UI polish** — verify the parameter understanding panel, status card, and advisor report display in real Streamlit interaction.
5. **Consider multi-turn parameter confirmation** — implement a simple design_state and chat-style multi-turn agent for parameter confirmation.
6. **Add more RAG knowledge files** — create `docs/rag_knowledge/` content for orbit design, power subsystem, mass budget, and design review checklist.

## 7. Minimal Files To Read Next

- `AGENTS.md`
- `docs/project_status.md`
- `docs/change_log.md`
- `app.py`
- `ui_helpers.py`
- `agents/mission_context_extractor.py` — new
- `agents/design_advisor.py` — modified
- `agents/report_generator.py` — modified
- `agents/rag_retriever.py`
- `agents/extractor.py`
- `agents/orbit_interpreter.py`
- `agents/orbit_consistency.py`
- `agents/validator.py`
- `agents/planner.py`
