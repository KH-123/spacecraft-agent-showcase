# Project Status

Last updated: 2026-05-19

This is the compact current-state entry point for the Spacecraft Conceptual Design AI Agent demo. For stable rules, read `AGENTS.md`. Do not read archived changelogs or old handoff files by default.

## Positioning

- Lightweight Python + Streamlit demo for conceptual / preliminary spacecraft design assistance.
- Must not claim final engineering design, certified result, launch-ready result, flight-qualified result, high-fidelity simulation, or model development conclusion.
- Main interview demo path is parameter-level mode. Mission-level mode exists for beginner-facing requirement understanding and draft handoff.

## Current Parameter Flow

1. User natural-language input.
2. LLM-first explicit parameter extraction; rules fallback if needed.
3. Separate engineering parameters from `mission_context`.
4. Normalize field / unit / source / status only.
5. Run explicit validation and explicit orbit consistency.
6. If severe: block deterministic tools and show confirmation / next actions.
7. Run cautious inference and `orbit_interpreter.py` orbit completion.
8. Run post-inference validation and orbit consistency.
9. Core Orbit Gate requires `semi_major_axis_km`, `eccentricity`, and `orbit_inclination_deg`.
10. If gate passes: call deterministic tools: orbit / mass / power.
11. Generate conceptual report.
12. Generate read-only `advisor_report` and `next_actions`.
13. Store valid result in `current_design_state`.

## Hard Boundaries

- LLM extraction extracts explicit user parameters and context only.
- LLM / RAG must not infer engineering values, overwrite explicit parameters, repair user values, or override tool outputs.
- `mission_context` is a read-only side channel for UI, RAG advisor, and missing-context hints only. It does not participate in Core Orbit Gate and does not trigger deterministic tools.
- RAG is a **RAG-enhanced LLM advisor / 知识增强设计评审模块**, not an engineering calculation layer. It retrieves local Markdown knowledge, may synthesize with an OpenAI-compatible LLM, and falls back gracefully to retrieval-only / rule-based advice.
- Engineering trust comes from validation, `orbit_consistency`, Core Orbit Gate, and deterministic tools, not from RAG.
- Do not hard-code demo cases into business logic. Do not change `tools/` interfaces unless explicitly requested.

## Current State

- `current_design_state` is session-local. Start-new resets the active design; supplement / modify uses the previous state as baseline and treats the latest input as a patch.
- `apply_user_patch_to_design_state()` in `app.py` preserves fields not present in the latest extraction. Latest explicit user values win; changed fields become `source=user_updated`; inferred/default values never overwrite explicit values.
- Derived values affected by changed dependencies are marked `stale` and recomputed by the normal pipeline. Example: altitude change stales SMA and period, but preserves inclination, orbit type, eccentricity, payload mass, and power.
- Severe supplement candidates are stored as `pending_design_state` for confirmation and do not overwrite the current valid design.
- `mission_context` merges incrementally for target region, revisit/access cycle, resolution, and related context. Recent rules cover expressions like `访问周期为12小时`, `每12小时访问一次`, `12小时重访`, and `revisits every 12 hours`.
- Patch View shows added / modified / retained / stale / missing fields with old -> new values and source/status metadata.
- Confirmation form emits a `confirmation_patch` only; confirmed parameters become `user_confirmed`, then the full parameter-level pipeline reruns.
- Execution logs append session events. Confirmation uses separate audit rounds for confirmation and rerun. Supplement / modify submit clears only the active input box, not state, logs, Patch View, or raw input history.
- Demo documents live in `demo_cases/`.

## Key Files

- `app.py`: main orchestration, state merge, current/pending design state, pipeline branches.
- `ui_helpers.py`: Streamlit UI, Patch View, confirmation form, execution log rendering.
- `agents/parser.py`: rules fallback extraction.
- `agents/llm_extractor.py`: LLM-first extraction support.
- `agents/normalizer.py`: deterministic normalization.
- `agents/mission_context_extractor.py`: explicit mission-context extraction.
- `agents/orbit_interpreter.py`: orbit-only inference/completion.
- `agents/orbit_consistency.py`: orbit contradiction checks.
- `agents/design_advisor.py` and `agents/rag_retriever.py`: read-only RAG-enhanced advisor.
- `scripts/test_design_state_confirmation_smoke.py`: minimal non-Streamlit smoke/regression coverage.

## Verification Snapshot

Latest verified checks:

```powershell
python -m py_compile app.py agents/*.py
python -m py_compile app.py ui_helpers.py scripts/test_design_state_confirmation_smoke.py (Get-ChildItem -LiteralPath agents -Filter *.py).FullName
python scripts/test_design_state_confirmation_smoke.py
```

Result:

- Literal `python -m py_compile app.py agents/*.py` fails on Windows because Python receives `agents/*.py` as a filename.
- PowerShell-expanded compile passed for `app.py`, `ui_helpers.py`, all `agents/*.py`, and the smoke script.
- Smoke tests passed: 18/18.

## Known Limitations

- State is session-local only; browser refresh clears it.
- The app is not a free chat agent and has no long-term memory.
- RAG retrieval is keyword-based local Markdown search, not vector retrieval.
- Patch View is demo/audit transparency, not a complete compliance audit log.
- Structured confirmation mainly covers core orbit and orbit-angle fields; mission-context structured confirmation is limited.
- Detailed coverage, revisit simulation, constellation phasing, link budget, thermal, ADCS, propulsion, and lifetime propagation are not implemented.

## Next-Agent Checklist

- Default read set: `AGENTS.md` and this file.
- For workflow/state bugs, read only relevant parts of `app.py` and specific `agents/`.
- For RAG changes, read `agents/design_advisor.py`, `agents/rag_retriever.py`, and only necessary `docs/rag_knowledge/` files.
- Do not read `docs/archive/change_log_archive.md` by default.
- After code changes, run the compile check and update both `docs/project_status.md` and `docs/change_log.md`.
