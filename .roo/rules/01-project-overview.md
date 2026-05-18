# Project Overview

This project is a lightweight demo for a Spacecraft Conceptual Design AI Agent.

The system is for conceptual / preliminary design assistance only. It must not claim to produce final, certified, flight-qualified, or high-fidelity engineering results.

## Product Positioning

The project demonstrates how to place LLM capability inside a controlled engineering workflow.

The Agent should not directly design a spacecraft. Instead:

- LLM understands natural language, extracts explicit parameters, recognizes context, and explains results.
- Deterministic modules normalize, validate, check consistency, and calculate.
- RAG provides read-only design advice.
- `current_design_state` manages the active design across multiple turns.

The main product value is controlled, explainable, and iterative conceptual design assistance.

## Modes

### 1. Task-level Requirement Mode

For beginner users who describe mission goals in natural language, for example:

> Design a remote sensing satellite that revisits Malaysia every 6 hours.

This mode should identify:

- mission objective
- target region
- revisit requirement
- payload hints
- missing design constraints

It may generate 2–3 conceptual candidate parameter drafts in Phase 2, but user confirmation is required before entering parameter-level design.

### 2. Parameter-level Design Mode

For professional users or students who already provide design parameters, for example:

> LEO, circular orbit, 500 km, inclination 51.6 deg, payload 20 kg, power 200 W.

This mode behaves like an engineering validation and calculation workflow:

- extract explicit user parameters
- normalize fields, units, sources, and status
- check explicit input consistency
- infer only allowed orbit-related parameters
- check orbit physical consistency
- block execution when severe issues exist
- gate execution by core orbit parameters
- call deterministic tools
- generate a conceptual report
- generate read-only RAG advice
- maintain `current_design_state`
- support multi-turn parameter update and confirmation

The current interview demo focuses on parameter-level design mode.

## Current MVP Capabilities

The MVP supports:

- natural language parameter input
- LLM-first extraction plus rules fallback
- separation between engineering parameters and `mission_context`
- deterministic field and unit normalization
- source tracking
- explicit parameter priority
- two-pass validation / orbit consistency
- orbit semantic inference
- Core Orbit Gate
- severe issue blocking
- deterministic orbit / mass / power tools
- conceptual report generation
- local Markdown-based RAG advisor
- advisor `next_actions`
- session-level `current_design_state`
- multi-turn supplement / modification
- parameter confirmation form
- `confirmation_patch`
- Patch View showing `old → new`
- execution log
- `raw_input_history` audit record
- concise RAG source display

## RAG Position

RAG is only a read-only design advisor layer after the deterministic design chain.

RAG may provide:

- conceptual design risks
- missing parameter suggestions
- suspicious parameter combinations
- reasonable conceptual ranges
- improvement directions
- explanation of trade-offs

RAG must not:

- overwrite user parameters
- replace deterministic tools
- replace validation or orbit consistency
- decide whether execution is allowed
- write back into normalized parameters
- present advice as final engineering truth

## Current Limitation

The current demo focuses on controlled Agent workflow, not a full spacecraft design toolchain.

The deterministic tools currently support conceptual orbit, mass, and power calculations. Mission context such as target region, revisit requirement, payload type, and task mode is mainly used for UI display, RAG advisor, and missing-context hints.

The tools layer does not yet deeply use mission context for:

- coverage analysis
- payload sizing
- communication link budget
- constellation design
- high-fidelity orbit propagation
- subsystem-level design

This limitation is intentional for the MVP. Future work may enhance the tools layer to better consume mission context and plan task-specific analyses.

## Demo Cases

GitHub / interview demo cases should be placed under `demo_cases/`.

Recommended cases:

1. Normal conceptual design flow.
2. Severe contradiction blocking.
3. Missing core orbit parameter.
4. Multi-turn parameter update.

Demo cases are documentation and showcase assets only. They must not be hard-coded into business logic.

## Do Not Implement in MVP

Do not implement unless explicitly requested:

- STK
- GMAT
- Orekit
- OpenMDAO
- cloud deployment
- user login
- Docker
- React / Vue frontend
- FastAPI backend
- complex databases
- high-fidelity subsystem simulation