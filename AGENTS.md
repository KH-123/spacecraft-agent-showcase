# AGENTS.md

Purpose: stable project rules for Codex / Roo Code. Keep this file short. Do not put history, long explanations, logs, or full source snippets here.

## Project Positioning

This is a lightweight Spacecraft Conceptual Design AI Agent demo for conceptual / preliminary design assistance only.

It must not claim to produce:

- final engineering design
- certified result
- flight-qualified result
- high-fidelity simulation
- model development conclusion

The project demonstrates a controlled engineering Agent workflow:

- LLM understands natural language, extracts explicit parameters, recognizes context, and explains results.
- Deterministic modules normalize, validate, check consistency, and calculate.
- RAG-enhanced LLM advisor provides read-only design review advice.
- `current_design_state` manages the active design across multiple turns.

## Modes

### 1. Mission-level Mode

For non-expert users who describe mission goals.

It may identify:

- mission objective
- target region
- revisit requirement
- payload hints
- missing design constraints

It may generate conceptual candidate parameter drafts only after clarification. User confirmation is required before entering parameter-level design.

### 2. Parameter-level Mode

For technical users who provide parameters or modify an existing design.

Current interview demo focuses on this mode.

Required workflow:

1. User natural language input.
2. LLM-first explicit parameter extraction.
3. Rules fallback if needed.
4. Separate engineering parameters from `mission_context`.
5. Deterministic normalization: field, unit, source, status.
6. Explicit-parameter validation.
7. Explicit orbit consistency check.
8. If severe: block tools, show confirmation report / form, accept `confirmation_patch`, merge as `user_confirmed`, rerun full workflow.
9. Orbit-only inference by `orbit_interpreter.py`.
10. Post-inference validation and orbit consistency check.
11. Core Orbit Gate.
12. If gate failed or severe: block tools, show missing / conflict explanation and advisor `next_actions`.
13. If gate passed: call deterministic tools: orbit / mass / power.
14. Generate conceptual report.
15. Generate read-only RAG-enhanced LLM advisor output (`advisor_report` / `next_actions`).
16. Write valid result into `current_design_state`.
17. Show UI summary, confirmation form, Patch View, execution log, and audit history.

## Core Boundaries

- LLM extraction must extract explicit user parameters and context only.
- LLM must not infer engineering values, repair user values, overwrite explicit values, or override tool outputs.
- `normalizer.py` performs deterministic field / unit / source / status normalization only.
- `orbit_interpreter.py` performs orbit-related inference only.
- `orbit_consistency.py` checks physical contradictions.
- `tools/` provides deterministic numerical calculations.
- `report_generator.py` displays and explains results only.
- RAG-enhanced LLM advisor is read-only and must not write back into parameters.

## Explicit Parameter Priority

User explicit parameters always have highest priority.

Do not overwrite:

- `user_explicit`
- `user_confirmed`
- `user_updated`

with:

- `inferred`
- `default_assumption`
- RAG advice
- LLM text

If user input conflicts with inferred logic, keep the user value and report the conflict.

## Core Orbit Gate

Do not call deterministic tools unless these are available:

- `semi_major_axis_km`
- `eccentricity`
- `orbit_inclination_deg`

`inclination_deg` may be normalized into `orbit_inclination_deg`.

RAAN, argument of perigee, and true anomaly may default to 0 deg only when marked as:

- `source=default_assumption`
- `requires_confirmation=true`

## mission_context Boundary

`mission_context` is a read-only side channel.

It may be used for:

- UI display
- RAG-enhanced design advisor
- missing-context hints
- demo explanation

It must not:

- participate in Core Orbit Gate
- trigger deterministic tools
- overwrite engineering parameters
- write back into normalized parameters
- replace explicit user parameters
- be treated as confirmed design data

## Multi-turn Update Rules

When the user supplements or modifies the current design:

1. Extract latest explicit parameters.
2. Merge them with previous explicit parameters.
3. Latest user explicit values win.
4. Inferred / default values must not overwrite explicit values.
5. Mark changed fields as `user_updated`.
6. Patch View shows `old -> new`.
7. Rerun the full parameter-level workflow.

## RAG Boundary

RAG is a RAG-enhanced LLM advisor / knowledge-enhanced design review layer, not an engineering calculation layer.

RAG may:

- retrieve local Markdown knowledge
- provide retrieved snippets and a current design-state summary to the LLM
- provide conceptual risks
- suggest missing parameters
- explain trade-offs
- generate `next_actions`
- gracefully fall back to retrieval-only / rule-based advisor output when LLM synthesis fails

RAG must not:

- modify parameters
- replace validation
- replace orbit consistency
- replace deterministic tools
- approve or reject Core Orbit Gate
- present advice as final engineering truth

RAG advice can reduce vague or hallucinated advisor text, but it cannot guarantee engineering correctness. The main engineering chain remains governed by validation, `orbit_consistency.py`, Core Orbit Gate, and deterministic `tools/`.

## Coding Rules

- Keep the project lightweight and runnable.
- Use Python + Streamlit.
- Do not introduce Docker, React, Vue, FastAPI, STK, GMAT, Orekit, OpenMDAO, cloud deployment, user login, or complex databases unless explicitly requested.
- Do not hard-code API keys.
- Do not hard-code demo cases into business logic.
- Prefer minimal targeted changes.
- Do not modify unrelated files.
- Do not change existing `tools/` interfaces unless explicitly requested.
- Keep UI, agent logic, RAG, and tools separated.
- Before editing, state which files will be changed.
- After editing, explain how to run and test.

## Documentation and Token-saving Rules

Default read set before most tasks:

- `AGENTS.md`
- `docs/project_status.md`
- current handoff file only if relevant

Do not read by default:

- full repository
- full `docs/change_log.md`
- `docs/archive/change_log_archive.md`
- old handoff files
- interview documents
- unrelated source files

Use task-specific minimal reads:

- workflow change: `app.py` and relevant `agents/`
- RAG change: `agents/rag_retriever.py`, `agents/design_advisor.py`, `docs/rag_knowledge/`
- tools change: specific `tools/` file and its caller
- UI change: `app.py` and related display helpers
- docs change: relevant docs only

Document ownership:

- `docs/project_status.md`: current-state entry point; update after every code-changing round.
- `docs/change_log.md`: recent-only changelog; keep only 5-10 recent key changes.
- `docs/archive/change_log_archive.md`: historical changelog; do not read by default.
- `docs/handoff_to_roo.md`: mainly generated by Codex for Roo Code.
- `docs/handoff_to_codex.md`: mainly generated by Roo Code for Codex.
- `docs/bug_summary.md`: update only when a bug cannot be fixed within two attempts.

Do not copy full source files into handoff documents.
Do not duplicate rules already written here.
Do not use changelog as project context.

## Required Checks

After code changes, run:

`python -m py_compile app.py agents/*.py`

Then update:

- `docs/project_status.md`
- `docs/change_log.md`

If only docs changed, compilation is optional.

Run app with:

`streamlit run app.py`
