# Engineering Reliability Rules

Purpose: define stable engineering guardrails only. Do not put long design notes, history, or examples here.

## Positioning

This is a spacecraft conceptual / preliminary design demo.

Allowed wording:

- conceptual estimate
- preliminary assessment
- rough sizing
- design suggestion
- parameter confirmation request

Forbidden wording:

- final design
- certified result
- flight-qualified result
- high-fidelity simulation
- validated mission conclusion

## Explicit Parameter Priority

User explicit parameters always have highest priority.

Inferred or default values must not overwrite:

- `user_explicit`
- `user_confirmed`
- `user_updated`

If user input conflicts with inferred logic, keep the user value and report the conflict.

## Source / Status

Important parameters should keep source and status when possible.

Common sources:

- `user_explicit`
- `user_confirmed`
- `user_updated`
- `inferred`
- `default_assumption`
- `tool_output`

Common status:

- `valid`
- `missing`
- `ambiguous`
- `requires_confirmation`
- `conflict`
- `severe`

## Two-pass Consistency

Pass 1 checks only explicit user inputs.

If severe contradiction exists:

- stop before inference
- do not call tools
- generate confirmation report / form

Pass 2 checks after allowed orbit inference.

If severe contradiction exists:

- do not call tools
- show conflict / missing explanation
- generate `next_actions`

## Orbit Inference Boundary

Allowed:

- circular orbit with no user eccentricity -> `eccentricity = 0`
- altitude -> `semi_major_axis_km`
- semi-major axis -> orbit period
- missing RAAN / argument of perigee / true anomaly -> 0 deg with confirmation required
- SSO + altitude -> conceptual inclination estimate

Forbidden:

- infer inclination from generic LEO + altitude
- overwrite user-provided eccentricity
- infer mass, payload type, power, data rate, lifetime, or subsystem sizing unless explicitly implemented and user-confirmed

## Physical Consistency

`orbit_consistency.py` should check at least:

- circular orbit vs non-zero eccentricity
- altitude vs orbit period
- altitude vs semi-major axis
- polar orbit vs inclination
- GEO / geostationary vs low altitude
- missing core orbit parameters before execution

Use deterministic formulas or deterministic tools. Do not rely on LLM judgment.

## Calculation Boundary

All engineering calculations must:

1. Be deterministic Python functions.
2. Have clear input / output units.
3. State key assumptions.
4. Avoid hidden constants unless documented.
5. Avoid pretending to be high-fidelity simulation.
6. Never be overwritten by LLM text.

## mission_context Boundary

`mission_context` is not an engineering parameter source.

It may support UI and RAG advice, but must not:

- join Core Orbit Gate
- trigger deterministic tools
- overwrite normalized parameters
- replace explicit user values
- be treated as confirmed design data

## RAG Boundary

RAG may provide conceptual advice only.

RAG must not:

- modify parameters
- replace validation
- replace orbit consistency
- replace tools
- approve or reject Core Orbit Gate
- present advice as final engineering truth