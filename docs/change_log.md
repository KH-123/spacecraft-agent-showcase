# Change Log

> This file keeps only recent important changes. The full history has been archived to [`docs/archive/change_log_archive.md`](archive/change_log_archive.md).
> See [`AGENTS.md`](../AGENTS.md#documentation-rules) for document governance rules.

---

## 2026-05-19 - Lightweight Interaction Polish

### Changed

- Supplement / modify submissions now queue a clear for the active input box on the next Streamlit render, without clearing `current_design_state`, Patch View, raw input history, or execution logs.
- Expanded `mission_context` revisit/access-cycle extraction for expressions such as `访问周期为12小时`, `每12小时访问一次`, `12小时重访`, `revisits every 12 hours`, and `revisit time 12 h`.
- Parameter confirmation now appends confirmation and rerun audit events as separate rounds, preserving prior execution-log history.
- Added smoke coverage for input clearing, revisit/access-cycle extraction, and confirmation audit-round append behavior.

### Files Affected

- `app.py`
- `agents/mission_context_extractor.py`
- `scripts/test_design_state_confirmation_smoke.py`
- `docs/project_status.md`
- `docs/change_log.md`

### Verification

```powershell
python -m py_compile app.py agents/*.py
python -m py_compile app.py ui_helpers.py scripts/test_design_state_confirmation_smoke.py (Get-ChildItem -LiteralPath agents -Filter *.py).FullName
python scripts/test_design_state_confirmation_smoke.py
```

Result: the literal wildcard command failed on Windows because Python received `agents/*.py` as a filename; the PowerShell-expanded compile check passed; smoke tests passed 18/18.

---

## 2026-05-19 - Multi-turn Patch Merge State Preservation

### Changed

- Fixed supplement / modify flow so the previous valid `current_design_state` is the baseline and latest user input is treated as a patch, not a complete replacement.
- Added `apply_user_patch_to_design_state()` to preserve fields not present in the latest extraction, keep user explicit / confirmed values ahead of inferred/default values, mark same-field user changes as `user_updated`, and mark affected derived values as `stale`.
- Height changes now stale only dependent derived fields such as `semi_major_axis_km` and `orbit_period_min`; unrelated orbit type, eccentricity, inclination, payload mass, and power are preserved.
- Severe update candidates are stored as `pending_design_state` for confirmation and do not overwrite the current valid design state.
- Mission context now merges incrementally for target region, revisit time, and resolution without feeding Core Orbit Gate or deterministic tools.
- Tightened parser/context extraction for common Chinese update forms and prevented `分辨率0.1m` from being interpreted as orbit altitude.
- Expanded `scripts/test_design_state_confirmation_smoke.py` with regression coverage for context-only updates, altitude updates, new resolution, inclination updates, and severe eccentricity conflicts.

### Files Affected

- `app.py`
- `agents/parser.py`
- `agents/mission_context_extractor.py`
- `agents/orbit_interpreter.py`
- `agents/orbit_consistency.py`
- `scripts/test_design_state_confirmation_smoke.py`
- `docs/project_status.md`
- `docs/change_log.md`

### Verification

```powershell
python -m py_compile app.py agents/*.py
python -m py_compile app.py ui_helpers.py (Get-ChildItem -LiteralPath agents -Filter *.py).FullName scripts/test_design_state_confirmation_smoke.py
python scripts/test_design_state_confirmation_smoke.py
```

Result: the literal wildcard command failed on Windows because Python received `agents/*.py` as a filename; the PowerShell-expanded compile check passed; smoke tests passed 15/15.

---

## 2026-05-18 - RAG Advisor Positioning and Demo Cases

### Changed

- Unified RAG positioning as a **RAG-enhanced LLM advisor / 知识增强的 LLM 设计评审助手**.
- Kept advisor output read-only: no parameter write-back, no Core Orbit Gate participation, no deterministic tool triggering, and no override of user parameters or tool outputs.
- `agents/design_advisor.py` now auto-uses the existing OpenAI-compatible LLM configuration for optional synthesis when `LLM_API_KEY` is available, with graceful fallback to retrieval-only / rule-based advice.
- Updated UI and documentation wording from generic RAG advisor wording to RAG-enhanced design review wording.
- Added `demo_cases/` GitHub / interview demo documents for normal flow, severe conflict blocking, missing core parameter, and multi-turn update behavior.

### Files Affected

- `agents/design_advisor.py`
- `agents/rag_retriever.py`
- `app.py`
- `ui_helpers.py`
- `AGENTS.md`
- `README.md`
- `docs/project_status.md`
- `demo_cases/*.md`

### Verification

```powershell
python -m py_compile app.py agents/*.py
python -m py_compile app.py ui_helpers.py (Get-ChildItem -LiteralPath agents -Filter *.py).FullName
```

Result: the literal wildcard command failed on Windows because Python received `agents/*.py` as a filename; the PowerShell-expanded compile check passed.

---
