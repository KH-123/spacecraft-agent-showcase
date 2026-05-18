# Change Log Archive

> Historical change record archive. This file is not read by default; consult it only when tracing past changes.
> For the current active change log, see [`docs/change_log.md`](../change_log.md).

---

## 2026-05-18 - State-Aware Advisor Actions and Patch View

### Changed

- `agents/design_advisor.py`
  - Added state-aware advisor input compatibility for `report_status`, input history, current round input, explicit parameters, normalized parameters, mission context, inferred/default values, missing parameters, consistency issues, tool results, and `core_gate_passed`.
  - Added `next_actions` to `advisor_report`.
  - Added rule-based next-action generation for missing inclination, circular/eccentricity conflicts, default orbit-angle assumptions, remote-sensing payload gaps, revisit constraints, data/downlink gaps, and task-goal inputs that should use mission-level mode.
  - Improved RAG query construction from current design state, including low LEO drag, inclination/revisit, payload resolution/swath/data, SAR power/data/thermal, downlink, and default orbit-angle confirmation.
- `app.py`
  - Passes design-state fields into `generate_design_advice()`.
  - Adds best-effort multi-turn Patch View data for added, modified, retained, and non-merged inferred/default parameters.
- `ui_helpers.py`
  - Adds an Agent Actions / 下一步建议 panel in the RAG advisor area.
  - Adds targeted clarification display using high-priority actions.
  - Adds Patch View UI for multi-turn supplement / modification runs.
  - Removes the parameter text-area default-value/session-state warning by initializing `mission_input` before widget creation.

### Verification

```bash
python -m py_compile app.py agents/*.py
python -m py_compile app.py (Get-ChildItem -LiteralPath agents -Filter *.py).FullName
```

Result:

- Literal `agents/*.py` compile command fails on Windows because Python does not expand the wildcard.
- PowerShell-expanded compile check passed.

---

## 2026-05-18 - Parameter-Level Design State and Demo Stabilization

### Changed

- `app.py`
  - Added a minimal session-local `current_design_state` for parameter-level multi-round supplement / modification.
  - Added explicit-parameter merge logic: latest user explicit inputs override previous user explicit inputs; inferred/default values do not become merge bases.
  - Moved `design_advisor` generation after deterministic tool execution so advisor input can include tool results.
  - Kept `mission_context` as a read-only side branch for UI/advisor only.
  - Stopped mixing advisor output into the main deterministic Markdown report; the UI renders it as a separate section.
- `ui_helpers.py`
  - Added fixed parameter-input guidance, 3 example-fill buttons, and visible design-state status.
  - Added Start New Scheme and Supplement / Modify Current Scheme controls.
  - Added explicit orbital-element rows to the parameter-understanding UI.
- `agents/orbit_interpreter.py`
  - Updated core orbit gate to require `semi_major_axis_km`, `eccentricity`, and `orbit_inclination_deg`.
- `agents/orbit_consistency.py`
  - Added raw-text circular semantics support so explicit `LEO + circular + eccentricity=0.10` conflicts can be detected in the explicit/pre-inference pass.
- `agents/design_advisor.py`
  - Fixed default-assumption handling, dict/list robustness, short RAG snippet previews, and optional LLM synthesis using a supplied OpenAI-compatible client.
- `agents/mission_context_extractor.py`
  - Added simple explicit patterns for target region, downlink rate, and pointing accuracy.
- `agents/planner.py`
  - Keeps mass-budget tool inputs deterministic by mapping unsupported orbit-shape labels such as `circular orbit` to a supported LEO mass-budget assumption when altitude is in LEO range, without modifying parameters.
- Tests were updated to match the stricter eccentricity core-gate and severe circular/eccentricity conflict behavior.

### Verification

```bash
python -m py_compile app.py agents/*.py
python -m py_compile app.py (Get-ChildItem -LiteralPath agents -Filter *.py).FullName (Get-ChildItem -LiteralPath scripts -Filter *.py).FullName
python scripts/test_parameter_flow_refactor.py
python scripts/test_circular_orbit_semantics.py
python scripts/test_orbit_intelligence.py
python scripts/test_concept_agent_flow.py
python scripts/test_extraction.py
python scripts/test_ui_modes.py
python scripts/test_mission_phase2.py
```

Result:

- Literal `agents/*.py` compile command fails on Windows because Python does not expand the wildcard.
- PowerShell-expanded compile check passed.
- Listed regression scripts passed.

---

## 2026-05-17 - Parameter-Level Processing Order Refactor

### Diagnosed

- The parameter-level flow had explicit hard-guardrail validation before inference, but orbit consistency was only checked after orbit completion. That blurred the boundary between user-provided contradictions and inferred/default values.
- `normalizer.py` performed limited unit handling and did not clearly mark unknown/missing units as requiring confirmation.
- Rules fallback had been doing some unit conversion before normalization, which made parser/normalizer responsibilities less clear.
- Orbit period completion depended on `semi_major_axis_km` plus `eccentricity`, even though the deterministic two-body period only needs semi-major axis.

### Changed

- `app.py`
  - Added a pre-inference orbit consistency pass using only explicit sources.
  - Skips missing-parameter inference and orbit completion when explicit hard-guardrail or explicit orbit conflicts are severe.
  - Keeps the post-inference validation/consistency pass for completed orbit parameters.
- `agents/parser.py`
  - Rebuilt rules extraction to preserve explicit values, units, and raw text spans without doing unit conversion.
  - Added readable Chinese/English patterns for altitude, mass, power, inclination, period, lifetime, eccentricity, SMA, RAAN, argument of perigee, true anomaly, orbit type, and resolution.
- `agents/normalizer.py`
  - Centralized deterministic unit conversion and source/status normalization.
  - Added common English/Chinese unit variants for distance, mass, power, time, period, angle, and data-volume helpers.
  - Marks unknown or missing units as `invalid_unit` / `missing_unit` with `requires_confirmation = true`.
- `agents/parameter_inference.py`
  - Limited cautious missing-parameter inference to orbit-related candidates only.
- `agents/orbit_interpreter.py`
  - Computes `orbit_period_min` from `semi_major_axis_km` alone using the deterministic two-body helper.
  - Converts altitude to semi-major axis before period computation.
  - Preserves explicit eccentricity and only infers `eccentricity = 0` from circular/GEO semantics when eccentricity is absent.
  - Keeps generic LEO + altitude from inferring inclination or eccentricity.
  - Updates the MVP core gate to require `semi_major_axis_km` and `orbit_inclination_deg`; eccentricity is now recommended but not a period/tool blocker by itself.
- `agents/orbit_consistency.py`
  - Added `stage` and `source_filter` support for pre/post inference checks.
  - Compares user period against two-body period from `semi_major_axis_km` or altitude-derived SMA.
  - Keeps circular orbit + high eccentricity, GEO/LEO altitude range, polar/SSO inclination, SSO altitude, altitude-SMA, and period consistency checks.
- `agents/validator.py`
  - Adds validation warnings for `invalid_unit` / `missing_unit` normalized entries.
- `agents/report_generator.py`
  - Adds `tool_computed` source display in parameter confirmation reports.
- `scripts/test_parameter_flow_refactor.py`
  - Added focused checks for the seven requested parameter-level scenarios.
- `scripts/test_orbit_intelligence.py`
  - Updated orbit gate expectations to match the new core/recommended distinction.
- `docs/project_status.md`
  - Updated the parameter-level call chain, unit normalization status, orbit gate, and verification notes.

### Verification

```bash
python -m py_compile app.py agents/*.py
python scripts/test_parameter_flow_refactor.py
python scripts/test_orbit_intelligence.py
python scripts/test_concept_agent_flow.py
python scripts/test_extraction.py
```

Result:

- `python -m py_compile app.py agents/*.py` was run with the PowerShell-expanded equivalent because Windows Python receives `agents/*.py` literally.
- Compile check passed for `app.py`, all `agents/*.py`, and the updated scripts.
- Parameter flow refactor tests passed: 7/7.
- Orbit intelligence tests passed: 9/9.
- Concept-agent flow tests passed: 8/8.
- Extraction tests passed: 6/6.

---

## 2026-05-17 - Orbit Period Completion and Circular Conflict Visibility

### Diagnosed

- The target parameter-level input already preserved the explicit `eccentricity = 0.10`, inferred `semi_major_axis_km = 6678.137`, and produced a circular/eccentricity warning when rules fallback recognized `orbit_type = circular orbit`.
- `orbit_period_min` remained missing because `orbit_interpreter` only inferred orbit elements and did not write deterministic period results back into `params`.
- If an upstream extractor preserved `orbit_type = LEO` while the raw text also said `circular orbit`, circular-shape consistency could be missed because consistency checks only keyed off the single `orbit_type` value.

### Changed

- `tools/orbit.py`
  - Added `orbit_period_from_semi_major_axis(semi_major_axis_km)` as a deterministic two-body helper.
- `agents/orbit_interpreter.py`
  - Records circular-shape semantics separately from the primary `orbit_type`.
  - Computes missing `orbit_period_min` once `semi_major_axis_km` and `eccentricity` are available.
  - Marks computed period values with `source = tool_computed`.
- `agents/orbit_consistency.py`
  - Uses retained circular-shape semantics to flag circular-orbit/eccentricity conflicts even when the primary `orbit_type` is an altitude class such as `LEO`.
  - Reuses the deterministic semi-major-axis period helper for consistency calculations.
- `ui_helpers.py`
  - Added a display status for computed parameters.
- `scripts/test_circular_orbit_semantics.py`
  - Added regression coverage for the target conflict input and for text-level circular semantics when `orbit_type = LEO`.
- `docs/project_status.md`
  - Updated orbit-period completion and verification notes.

### Verification

```bash
python -m py_compile app.py agents/*.py tools/orbit.py scripts/test_circular_orbit_semantics.py
python scripts/test_circular_orbit_semantics.py
python scripts/test_orbit_intelligence.py
python scripts/test_extraction.py
python scripts/test_concept_agent_flow.py
python scripts/test_ui_modes.py
python scripts/test_mission_phase2.py
```

Result:

- Compile check passed using the PowerShell-expanded equivalent of `agents/*.py`.
- Circular orbit semantic tests passed: 6/6.
- Orbit intelligence tests passed: 9/9.
- Extraction tests passed: 6/6.
- Concept-agent flow tests passed: 8/8.
- UI mode tests passed: 3/3.
- Mission Phase 2 tests passed: 6/6.

---

## 2026-05-17 - Circular Orbit Eccentricity Inference Fix

### Diagnosed

- The circular-orbit inference path in `agents/orbit_interpreter.py` already knew how to infer `eccentricity = 0.0` from `orbit_type = circular orbit`.
- The failure for `LEO，圆轨道，300km，载荷20kg，功率200W` came from rules extraction choosing the first matching orbit type, `LEO`, before the circular-orbit shape phrase.
- Because `orbit_type` was already set to `LEO`, the interpreter did not recover the circular-orbit shape from the text, and eccentricity remained missing.
- `ECCENTRICITY_PATTERN` also allowed bare `e` without `=`/`:` and could misread English text such as `altitude 500 km` as an eccentricity value.

### Changed

- `agents/llm_extractor.py`
  - Added prompt guidance to extract `圆轨道`, `近圆轨道`, `圆形轨道`, `circular orbit`, and `near-circular orbit` as `orbit_type = circular orbit`.
  - Did not add any raw `eccentricity = 0` extraction logic.
- `agents/normalizer.py`
  - Added circular/near-circular synonyms to orbit type normalization.
- `agents/parser.py`
  - Prioritizes circular/elliptical shape phrases before broad altitude-class phrases such as `LEO`.
  - Tightened eccentricity regex so English `e` only counts as eccentricity when written like `e=...` or `e:...`.
- `agents/orbit_interpreter.py`
  - Generalized circular orbit detection and still infers `eccentricity = 0.0` only when the user has not explicitly provided eccentricity.
  - Keeps the source as `inferred_from_orbit_type`.
- `scripts/test_circular_orbit_semantics.py`
  - Added regression tests for Chinese circular orbit, near/general circular semantics, English circular orbit, and explicit `e=0.5` conflict behavior.
- `docs/project_status.md`
  - Updated circular-orbit capability and verification notes.

### Verification

```bash
python -m py_compile app.py agents/*.py
python scripts/test_circular_orbit_semantics.py
python scripts/test_orbit_intelligence.py
python scripts/test_concept_agent_flow.py
python scripts/test_extraction.py
python scripts/test_ui_modes.py
```

Result:

- Compile check passed using the PowerShell-expanded equivalent of `agents/*.py`.
- Circular orbit semantic tests passed: 4/4.
- Orbit intelligence tests passed: 9/9.
- Concept-agent flow tests passed: 8/8.
- Extraction tests passed: 6/6.
- UI mode tests passed: 3/3.

---

## 2026-05-17 - Mission-Level Phase 2 Draft Handoff

### Added

- `agents/mission_interpreter.py`
  - Added mission-level interpretation separate from `llm_extractor.py`.
  - Extracts `input_type`, mission objective, target region, revisit requirement, payload hint, performance requirements, missing design drivers, and ambiguity notes.
  - Supports generalized revisit expressions such as `6小时一次`, `每12小时重访`, and `每天两次`.
- `agents/design_draft_generator.py`
  - Generates 2-3 conceptual candidate design drafts with assumptions, confidence, `requires_confirmation`, and `verification_status`.
  - Converts a user-adopted draft into parameter-flow params with `source = user_confirmed_llm_inferred`.
  - Adds `requires_external_simulation` placeholders for coverage/revisit/constellation validation needs.
- `scripts/test_mission_phase2.py`
  - Added Phase 2 acceptance checks for mission-level interpretation, generalized region/revisit parsing, missing design drivers, parameter-mode regression, and adopted draft source tracking.

### Changed

- `app.py`
  - Upgraded task-level mode from Phase 1 guidance to Phase 2 mission understanding + missing constraints + candidate drafts.
  - Added draft adoption flow that enters the existing parameter-level validation, orbit consistency, deterministic tools, and report path.
  - Keeps task-level draft generation free of deterministic tool calls and formal engineering reports.
- `ui_helpers.py`
  - Displays task interpretation, missing constraints, candidate drafts, assumptions, confidence, verification status, and adopt-draft buttons.
  - Added source labels for `user_confirmed_llm_inferred` and `requires_external_simulation`.
- `agents/report_generator.py`
  - Reports `user_confirmed_llm_inferred` separately from user-provided, inferred, default, tool-computed, and LLM-estimated values.
  - Adds a report section for not-verified items that require external coverage/revisit simulation.
- `agents/parser.py`
  - Improved Chinese inclination extraction for parameter-level inputs such as `倾角51.6度`.
- `scripts/test_ui_modes.py`
  - Updated mission-mode test expectations for Phase 2 candidate drafts.
- `docs/project_status.md`
  - Updated current phase, call chain, capabilities, known issues, and verification notes.

### Verification

```bash
python -m py_compile app.py ui_helpers.py agents/*.py scripts/*.py
python scripts/test_mission_phase2.py
python scripts/test_ui_modes.py
python scripts/test_extraction.py
python scripts/test_orbit_intelligence.py
python scripts/test_concept_agent_flow.py
```

Result:

- Compile check passed using PowerShell-expanded Python file lists on Windows.
- Mission Phase 2 tests passed: 6/6.
- UI mode tests passed: 3/3.
- Extraction tests passed: 6/6.
- Orbit intelligence tests passed: 9/9.
- Concept-agent flow tests passed: 8/8.

---

## 2026-05-17 - Dual-Mode UI Entry Phase 1

### Changed

- `app.py`
  - Added a top-level mode selector with `参数级设计模式` and `任务级需求模式`.
  - Preserved the existing parameter-level design flow unchanged behind the parameter mode.
  - Added Phase 1 mission-level guidance flow that builds mission understanding, missing-constraint guidance, logs, and a guidance note without running deterministic tools.
  - Added `build_mission_guidance()` as a lightweight helper for mission-level UI/test coverage.
- `ui_helpers.py`
  - Added mode selector, mission objective input panel, mission guidance panel, and mission debug panel.
  - Kept debug/metadata folded under `高级调试信息`.
- `agents/parameter_inference.py`
  - Improved rules for mission-level target-region and revisit-time recognition.
  - Supports phrasing like `6小时访问一次...遥感卫星` without hard-coding a specific region.
- `scripts/test_ui_modes.py`
  - Added tests for task-level guidance and parameter-level regression entries.
- `docs/project_status.md`
  - Updated current phase, dual-mode call chain, known issues, and verification notes.

### Verification

```bash
python -m py_compile app.py ui_helpers.py agents/*.py scripts/*.py
python scripts/test_ui_modes.py
python scripts/test_concept_agent_flow.py
python scripts/test_extraction.py
python scripts/test_orbit_intelligence.py
streamlit run app.py --server.headless true --server.port 8501
```

Result:

- Compile check passed.
- UI mode tests passed: 3/3.
- Concept-agent flow tests passed: 8/8.
- Extraction tests passed: 6/6.
- Orbit intelligence tests passed: 9/9.
- Streamlit started successfully at `http://localhost:8501`.

---

## 2026-05-17 - Concept-Agent Flow and Orbit Period Consistency

### Changed

- `agents/llm_extractor.py`
  - Extended the LLM extraction prompt to request explicit parameters plus mission intent metadata.
  - Added optional `orbit_period` extraction support while keeping the older `mission_parameters` schema compatible with existing tests.
- `agents/normalizer.py`
  - Added `orbit_period_min` to the internal parameter schema.
  - Normalizes LLM output from either `explicit_params` or the legacy `mission_parameters` key.
- `agents/parser.py`
  - Added rules extraction for user-provided orbital period in minutes/hours/seconds.
- `agents/parameter_inference.py`
  - Added cautious missing-parameter inference.
  - Supports LLM inference when configured and rules fallback when LLM is unavailable.
  - Preserves mission intent metadata, assumptions, confidence, and confirmation flags.
- `agents/validator.py`
  - Added optional `source_filter` and `include_missing` arguments so the app can validate explicit user-provided/extracted parameters before inferred candidates.
  - Writes `validation_status` back to parameter entries.
- `agents/orbit_consistency.py`
  - Added generic two-body orbital period consistency validation.
  - Checks user-provided `orbit_period_min` against period computed from altitude or semi-major axis.
  - Checks altitude and semi-major axis consistency when both are provided.
- `agents/planner.py`
  - Added one bounded concept-level feedback pass for deterministic tool failures without replacing tool results.
- `app.py`
  - Updated the call chain to explicit-parameter validation -> missing-parameter inference -> orbit interpretation -> final validation/consistency.
  - Logs mission intent, inferred parameters, tool execution, and skip reasons in Chinese.
- `ui_helpers.py`
  - Displays `orbit_period_min` and new parameter sources.
  - Keeps explicit params, mission context, and inference metadata in the folded debug panel.
- `scripts/test_concept_agent_flow.py`
  - Added 8 acceptance tests for intent understanding, orbit-period consistency, and generalized orbit contradictions.

### Verification

```bash
python -m py_compile app.py ui_helpers.py agents/*.py scripts/*.py
python scripts/test_extraction.py
python scripts/test_orbit_intelligence.py
python scripts/test_concept_agent_flow.py
streamlit run app.py --server.headless true --server.port 8501
```

Result:

- Compile check passed.
- Extraction tests passed: 6/6.
- Orbit intelligence tests passed: 9/9.
- Concept-agent flow tests passed: 8/8.
- Streamlit started successfully at `http://localhost:8501`.

---

## 2026-05-17 - Streamlit UI Console Cleanup

### Changed

- `app.py`
  - Reorganized the Streamlit page into four main modules: task input, parameter display, recommendations/summary, and execution log.
  - Kept the existing LLM-first extraction, rules fallback, orbit inference, validation, tool execution, and report-generation call chain.
  - Replaced main-page JSON/debug blocks with a default-collapsed `高级调试信息` expander.
  - Added concise Chinese execution logs showing extraction mode, inferred/defaulted orbit parameters, validation outcome, and whether `execute_all_tasks()` ran or was skipped.
- `ui_helpers.py`
  - Added reusable Streamlit rendering helpers and CSS for a white scientific-console style.
  - Added inactive pre-run parameter tables and normalized display labels for parameter source/status.
- `docs/project_status.md`
  - Updated the current phase and verification notes.
- `docs/test_report_ui_refactor.md`
  - Added UI refactor verification notes and test checklist.

### Verification

```bash
python -m py_compile app.py ui_helpers.py agents/*.py
streamlit run app.py --server.headless true --server.port 8501
python scripts/test_orbit_intelligence.py
```

Notes:

- On Windows, the compile check was run with a PowerShell-expanded `agents/*.py` file list.
- Streamlit started successfully at `http://localhost:8501`.
- Orbit intelligence tests passed: 9/9.

---

## 2026-05-16 - Orbit Element Completeness Gate

### Changed

- `agents/orbit_interpreter.py`
  - Added orbital-elements table generation for `semi_major_axis_km`, `eccentricity`, `inclination_deg`, `raan_deg`, `arg_perigee_deg`, and `true_anomaly_deg`.
  - Added completeness gate requiring `semi_major_axis_km`, `eccentricity`, and `orbit_inclination_deg` before downstream task execution.
  - Infers `semi_major_axis_km` from altitude using Earth radius + altitude.
  - Defaults RAAN, argument of perigee, and true anomaly to `0 deg` with `source="default_assumption"` and `requires_confirmation=True`.
  - Keeps LEO altitude-only cases from inventing inclination or eccentricity.
  - Adds low-LEO atmospheric drag risk warning.
- `agents/parser.py`
  - Rebuilt rules parser text patterns with readable Chinese/English support.
  - Added extraction for `semi_major_axis_km`, `eccentricity`, `raan_deg`, `arg_perigee_deg`, and `true_anomaly_deg`.
- `agents/normalizer.py`
  - Added orbital element keys to the internal schema.
  - Preserves status and confirmation flags for rules and LLM outputs.
- `app.py`
  - Displays an orbital-elements table after orbit inference.
  - Displays orbit inference status, missing core elements, reasons, and next-step suggestions.
  - Blocks `execute_all_tasks()` when core orbital elements are missing, even if hard guardrails are not severe.
  - Shows skip reason in the Debug / Transparency panel.
- `agents/report_generator.py`
  - Parameter confirmation reports now include orbital elements, missing core orbit elements, next-step suggestions, orbit warnings, and orbit conflicts.
- `scripts/test_orbit_intelligence.py`
  - Added LEO300km completeness-gate regression tests.

### Verification

```bash
python -m py_compile app.py agents/*.py
python scripts/test_orbit_intelligence.py
```

Notes:

- On Windows, Python does not expand `agents/*.py` by itself, so the compile check was run with a PowerShell-expanded file list.
- Orbit intelligence tests passed: 9/9.

---

## 2026-05-16 — Orbit Intelligence + LLM Concept-Level Estimation

### New Files
- `agents/orbit_interpreter.py` — Orbit type recognition (polar, SSO, LEO, GEO, MEO, HEO, circular, elliptical) and parameter inference (inclination from SSO altitude via J2 precession, inclination ~90 for polar, altitude ~35786 km for GEO, eccentricity ~0 for circular)
- `agents/orbit_consistency.py` — 7 consistency checks with warning/severe levels; `OrbitConflict` class with `to_dict()`; `has_severe_orbit_conflicts()` function
- `agents/llm_estimator.py` — LLM concept-level estimation for unsupported requests; reuses OpenAI-compatible client from `llm_extractor.py`; returns structured results with `source="llm_estimated"`, assumptions, uncertainty notes, confidence, `requires_confirmation` flag; safe fallback when LLM unavailable
- `scripts/test_orbit_intelligence.py` — 7 integration tests covering all handoff requirements

### Modified Files
- `agents/normalizer.py` — Extended `ORBIT_TYPE_MAP` with MEO, HEO, circular, elliptical orbit mappings
- `agents/parser.py` — Extended `ORBIT_TYPE_RULES` with MEO, HEO, circular, elliptical orbit regex patterns
- `agents/planner.py` — `execute_all_tasks()` now accepts `extra_requests` parameter; runs LLM estimator for unsupported tasks in dependency order
- `agents/report_generator.py` — Added Section 1a (Orbit Parameter Inference), Section 1b (Orbit Consistency Validation), Section 3a (Concept-Level Estimates); source tracking display for all parameters
- `app.py` — Integrated orbit_interpreter and orbit_consistency into main pipeline; added `_detect_unsupported_requests()` helper; expanded Debug panel with orbit metadata and conflicts; severe orbit conflicts block normal report generation

### Verification
- `python -m py_compile` passed for all 6 modified/new Python files
- `python scripts/test_orbit_intelligence.py` — 7/7 passed

---

## 2026-05-17 — RAG Advisor Scaffold (Read-Only, Post-Tools)

### New Files
- `agents/rag_retriever.py` — Minimal local Markdown retrieval function.
  - `retrieve(query)` — keyword-based snippet search across `docs/rag_knowledge/*.md`.
  - `retrieve_combined(query)` — convenience wrapper returning a single string.
  - Graceful fallback: empty list / empty string when no knowledge files exist.
- `agents/design_advisor.py` — Read-only RAG design advisor.
  - `generate_design_advice(advisor_input, llm_client=None)` — produces a structured `advisor_report` dict with 8 keys.
  - Accepts normalized params, missing params, consistency issues, validation results, task results, and orbit metadata as read-only input.
  - When `llm_client` is provided, attempts LLM synthesis (scaffold only — `_synthesise_with_llm()` returns `None`).
  - When `llm_client` is `None`, falls back to raw retrieved snippets as advice.
  - Never modifies parameters, never overrides tools, never decides core gate.

### Changed
- `docs/rag_knowledge/` — Created directory with `.gitkeep` placeholder (empty knowledge base).
- `docs/project_status.md` — Added RAG advisor scaffold to capabilities, known issues, and verification.
- `docs/change_log.md` — This entry.

### Verification
```bash
python -m py_compile app.py agents/rag_retriever.py agents/design_advisor.py agents/extractor.py agents/planner.py agents/report_generator.py agents/validator.py agents/orbit_consistency.py agents/orbit_interpreter.py agents/llm_extractor.py agents/llm_estimator.py agents/normalizer.py agents/parser.py agents/parameter_inference.py agents/mission_interpreter.py agents/design_draft_generator.py
python -c "from agents.rag_retriever import retrieve, retrieve_combined; print('rag_retriever OK')"
python -c "from agents.design_advisor import generate_design_advice; r = generate_design_advice({'normalized_params': {}, 'missing_params': [], 'consistency_issues': [], 'validation_results': [], 'task_results': [], 'orbit_metadata': {}}); print('design_advisor OK')"
```

Result:
- Compile check passed for all 16 Python files.
- `rag_retriever.retrieve()` returns empty list gracefully when no knowledge files exist.
- `design_advisor.generate_design_advice()` returns a complete `advisor_report` dict with all 8 keys, even without LLM client.
- No existing functionality was modified.

---

## 2026-05-17 — Mission Context Extraction + Parameter Understanding UI + Enhanced RAG Advisor

### New Files
- `agents/mission_context_extractor.py` — Explicit mission context extraction (no inference, no gate participation).
  - `extract_mission_context(user_text, llm_parsed_json=None)` — LLM context priority + rules fill.
  - `build_mission_context_display_rows(context)` — UI display helper.
  - 11 fields: mission_type, target_region, revisit_time_h, payload_type, ground_resolution_m, swath_width_km, imaging_frequency, daily_data_volume_GB, downlink_rate_Mbps, mission_lifetime_year, pointing_accuracy_deg.
  - No engineering inference, no auto-completion, no core orbit gate participation.

### Changed
- `agents/design_advisor.py` — Enhanced with `_fill_rule_based_advice()` for Chinese rule-based fallback.
  - Supports `mission_context` and `default_assumptions` in advisor_input.
  - Rule-based analysis covers: design summary, main risks (8 categories), parameter comments, missing parameter suggestions, recommended next steps, limitations.
  - All user-visible output in Chinese.
- `agents/report_generator.py` — Added `mission_context` and `advisor_report` parameters to `generate_report()` and `generate_parameter_confirmation_report()`.
  - Added `_append_advisor_report()` for rendering advisor sections.
  - Enhanced `_append_parameter_table()` with 状态 (Status) and 需确认 columns.
  - Enhanced `_append_mission_context()` for new-style 11-field mission_context.
- `ui_helpers.py` — Added 3 new UI functions:
  - `render_parameter_understanding_panel()` — 6-tab parameter detail view.
  - `render_status_card()` — Flow status card with expander and status badge.
  - `render_advisor_panel()` — RAG advisor display with tabs.
  - Added `PARAM_SOURCE_CATEGORIES` for categorizing params by source.
  - Updated execution log section title from "4." to "5.".
- `app.py` — Integrated mission_context extraction and design_advisor calls into pipeline.
  - Added imports for `extract_mission_context`, `generate_design_advice`, `render_parameter_understanding_panel`, `render_status_card`, `render_advisor_panel`.
  - `_run_pipeline()` now calls `extract_mission_context()` after parameter extraction.
  - `_run_pipeline_with_params()` builds `advisor_input` and calls `generate_design_advice()`.
  - Passes `mission_context` and `advisor_report` to report generators and UI.
  - Calls new UI rendering functions in pipeline.
  - Updated log step numbers from "4/5"/"5/5" to "4/6"/"5/6"/"6/6".
  - `_render_initial_state()` now shows all new panels in inactive state.

### Verification
```bash
python -m py_compile app.py agents/__init__.py agents/design_advisor.py agents/design_draft_generator.py agents/extractor.py agents/llm_estimator.py agents/llm_extractor.py agents/mission_context_extractor.py agents/mission_interpreter.py agents/normalizer.py agents/orbit_consistency.py agents/orbit_interpreter.py agents/parameter_inference.py agents/parser.py agents/planner.py agents/rag_retriever.py agents/report_generator.py agents/validator.py
```

Result:
- Compile check passed for all 18 Python files.
- No existing functionality was modified.
- New file: `agents/mission_context_extractor.py`.
- Modified files: `agents/design_advisor.py`, `agents/report_generator.py`, `ui_helpers.py`, `app.py`.
