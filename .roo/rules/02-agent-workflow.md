# Agent Workflow Rules

Purpose: define stable workflow rules only. Do not put history, long explanations, logs, or source snippets here.

## Modes

The project has two modes:

1. Task-level requirement mode
2. Parameter-level design mode

## Task-level Requirement Mode

Use when the user gives a mission goal instead of complete parameters.

Workflow:

1. Understand mission objective, target region, revisit need, payload hints, and missing constraints.
2. Ask concise clarification questions when required.
3. In Phase 2, generate only conceptual candidate parameter drafts.
4. Require user confirmation before entering parameter-level design.

## Parameter-level Design Mode

Use when the user provides design parameters or modifies the current design.

Required workflow:

1. User input
2. LLM-first extraction
3. Rules fallback if needed
4. Separate engineering parameters from `mission_context`
5. Deterministic normalization: field, unit, source, status
6. Explicit-parameter validation
7. Explicit orbit consistency check
8. If severe: block tools, show confirmation report / form, accept `confirmation_patch`, merge as `user_confirmed`, rerun full workflow
9. Orbit-only inference by `orbit_interpreter.py`
10. Post-inference validation and orbit consistency check
11. Core Orbit Gate
12. If gate failed or severe: block tools, show missing / conflict explanation and `next_actions`
13. If gate passed: call deterministic tools: orbit / mass / power
14. Generate conceptual report
15. Generate read-only RAG advisor output
16. Write valid result into `current_design_state`
17. Show UI summary, confirmation form, Patch View, execution log, and audit history

## Core Orbit Gate

Do not call deterministic tools unless these are available:

- `semi_major_axis_km`
- `eccentricity`
- `orbit_inclination_deg`

`inclination_deg` may be normalized into `orbit_inclination_deg`.

RAAN, argument of perigee, and true anomaly may default to 0 deg only when marked as:

- `source=default_assumption`
- `requires_confirmation=true`

## Multi-turn Update

When the user supplements or modifies the current design:

1. Extract latest explicit parameters.
2. Merge with previous explicit parameters.
3. Latest user explicit values win.
4. Inferred / default values must not overwrite explicit values.
5. Mark changed fields as `user_updated`.
6. Patch View shows `old → new`.
7. Rerun the full parameter-level workflow.

## mission_context Bypass

`mission_context` is a read-only side channel.

It may be used for:

- UI display
- RAG advisor
- missing-context hints
- demo explanation

It must not:

- participate in Core Orbit Gate
- trigger deterministic tools
- overwrite engineering parameters
- write back into normalized parameters
- replace explicit user parameters

## Module Boundaries

- `llm_extractor.py`: extract explicit parameters and context only.
- `parser.py`: deterministic extraction fallback.
- `normalizer.py`: deterministic field / unit / source / status normalization only.
- `validator.py`: basic validity and missing-field checks.
- `orbit_interpreter.py`: orbit-related inference only.
- `orbit_consistency.py`: physical contradiction checks.
- `tools/`: deterministic numerical calculations only.
- `report_generator.py`: display and explain results only.
- `design_advisor.py`: read-only RAG advice only.

LLM must not infer, repair, overwrite, or replace deterministic results.