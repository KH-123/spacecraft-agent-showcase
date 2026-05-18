# Interview Demo Cases

These cases are for manual interview demonstration and acceptance checks only. They must not be hard-coded into business logic.

## Latest UI Acceptance Points

- After clicking Start New Scheme, the page should continue to show the saved current scheme and the Supplement / Modify Current Scheme entry should be available.
- After applying the structured parameter confirmation form, the Current Scheme Summary should update immediately from `current_design_state`.
- `raw_input_history` must not be overwritten by confirmation-form patches; it remains an audit trail of original natural-language inputs.
- `current_design_state` is the current effective design and should be visually distinguished from raw input.
- The Current Equivalent Design Description / auto summary should describe the latest effective orbit, payload, and mission context.
- The execution log should record Start New Scheme, Supplement / Modify, confirmation patch creation/application, severe blocking, core gate status, deterministic tools, advisor generation, and saved-state rendering.
- Natural-language same-field updates should be visible as explicit overrides: Patch View shows `old -> new`, the current summary shows the new value, and the execution log records `parameter_overwritten`.
- Parameter input guidance should state that `mission_context` is an optional bonus input for better advisor review, not a required core-gate input.
- RAG advisor should show concise local references such as `docs/rag_knowledge/02_orbit_design_knowledge.md:L120-L138`.
- Multi-turn Patch View should show added, modified, retained, non-merged inferred/default values, and current missing items.
- Patch View should show patch source, action, confirmed round, old/new values, old/new sources, category, and whether the update came from natural language or the confirmation form.
- The structured parameter confirmation form should show missing core parameters, default assumptions requiring confirmation, and severe issues when present.
- The form should generate `confirmation_patch` only; it must not directly mutate `normalized_parameters`.
- For circular orbit + nonzero `eccentricity`, the severe repair guide should offer two explicit choices and must not auto-apply either one.
- Confirmation inputs should reject invalid orbit ranges: inclination outside 0-180 deg, eccentricity outside 0 <= e < 1, and RAAN / argument of perigee / true anomaly outside 0 <= angle < 360 deg.
- Users should be able to batch-confirm default angle parameters and edit recommended values before applying.
- Smoke tests:

```powershell
python scripts/test_design_state_confirmation_smoke.py
```

## Case A: 正常概念设计

Input:

```text
LEO，圆轨道，500km，倾角51.6度，光学遥感，目标马来西亚，6小时重访，载荷20kg，功率200W
```

Expected display:

- Parameter extraction shows explicit altitude, inclination, payload mass, payload power, and orbit wording.
- `mission_context` shows optical remote sensing, Malaysia target region, and 6 h revisit requirement.
- Orbit interpreter infers `eccentricity=0`, `semi_major_axis_km=6878.137`, and deterministic `orbit_period_min`.
- Core gate passes and deterministic orbit / mass / power tools run.
- RAG advisor reminds that resolution, swath width, daily data volume, downlink rate, lifetime, and pointing constraints are still missing for a stronger design review.
- Agent Actions shows 2-4 next-step suggestions, especially payload performance, revisit constraints, and data/downlink closure.
- RAG advisor includes short references to local Markdown knowledge snippets.
- The confirmation panel may show default orbit-angle assumptions that require user confirmation.

## Case 1: 确认表单更新后摘要刷新

First input:

```text
LEO，圆轨道，300km，载荷20kg，功率200W
```

Form action:

```text
勾选 orbit_inclination_deg，user value 填 51.6，unit 选 deg，点击“应用所选确认”。
```

Expected display:

- 当前方案摘要显示 `orbit_inclination_deg = 51.6 deg`，来源为 `user_confirmed`。
- 当前等效方案描述包含倾角。
- `raw_input_history` 仍保留第一轮原始输入，不被 confirmation_patch 覆盖。
- Patch View 显示 `orbit_inclination_deg: missing -> 51.6 deg`，patch_source 为 `parameter_confirmation_form`。
- 执行日志包含 `confirmation_patch_created`、`confirmation_patch_applied`、`pipeline_rerun_started`、validation/core gate/tools/advisor 相关事件。

## Case 2: 第二轮修改高度

First input:

```text
LEO，圆轨道，300km，倾角51.6度，载荷20kg，功率200W
```

Second input:

```text
高度改为500km
```

Expected display:

- 当前方案摘要显示 `orbit_altitude_km = 500 km`，不再把 300 km 作为当前有效高度。
- `semi_major_axis_km` 和 `orbit_period_min` 重新计算。
- Patch View 显示 `orbit_altitude_km: 300 km -> 500 km`，action 为 `modified`，new source 为 `user_updated` 或等价显式更新标记。
- RAG advisor / next_actions 重新生成。
- 执行日志包含 `design_updated_from_natural_language`、`parameter_overwritten`、`pipeline_rerun_started`、tools/advisor 相关事件。

## Case 3: 第二轮修改 RAAN

First action:

```text
先确认 RAAN=0 deg。
```

Second input:

```text
RAAN改为30度
```

Expected display:

- 当前方案摘要显示 `raan_deg = 30 deg`。
- source 显示为最新 user explicit / `user_updated`。
- Patch View 显示 `raan_deg: 0 deg -> 30 deg`。
- 旧的 RAAN=0 不再作为当前有效值显示，只保留在 Patch View / raw audit 轨迹里。

## Case B: 严重矛盾阻断

Input:

```text
LEO，圆轨道，300km，偏心率0.10，倾角10度，载荷20kg，功率200W
```

Expected display:

- `eccentricity=0.10` is preserved as a user explicit value.
- The system does not overwrite eccentricity to `0`.
- Orbit consistency identifies the circular-orbit plus nonzero-eccentricity contradiction as severe.
- Formal deterministic calculation is blocked.
- The UI and report show a parameter confirmation request.
- Agent Actions first asks the user to confirm circular orbit vs nonzero `eccentricity`.
- The confirmation panel shows the severe issue and requires an explicit user reply before it can be applied.

## Case C: 缺核心参数但能给建议

Input:

```text
LEO，圆轨道，300km，载荷20kg，功率200W
```

Expected display:

- Orbit interpreter infers `eccentricity=0`, `semi_major_axis_km=6678.137`, and deterministic `orbit_period_min`.
- The system does not infer inclination from generic LEO + altitude.
- Core gate fails because `orbit_inclination_deg` is missing.
- The UI shows a parameter confirmation report.
- RAG advisor flags low-LEO drag / lifetime / orbit-maintenance risk and asks for mission lifetime or maintenance assumptions.
- Agent Actions first asks the user to supplement inclination or state whether the orbit should be SSO / polar / equatorial.
- The confirmation panel shows `orbit_inclination_deg` as blocking and provides a suggested reply format.
- In the structured confirmation form, users can check `orbit_inclination_deg`, enter or edit `51.6 deg`, apply it, and trigger a full rerun.

## Case D: 多轮补充参数

First input:

```text
LEO，圆轨道，300km，载荷20kg，功率200W
```

Second input:

```text
倾角用51.6度，光学遥感，目标马来西亚
```

Expected display:

- Second round preserves the first-round altitude, circular orbit wording, payload mass, and power.
- Second round merges the new explicit inclination and mission context.
- Validation, orbit completion, core gate, tools, report generation, and advisor generation all rerun from the merged explicit design state.
- UI shows the current scheme has accumulated 2 input rounds.
- Patch View shows newly added inclination, `payload_type`, and `target_region`; it also shows the first-round altitude, circular orbit wording, payload mass, and power as retained explicit inputs.
- Agent Actions updates away from core inclination asking and toward resolution, swath, data volume, downlink, and revisit-constraint suggestions.
- Patch View should show source/status/category metadata and should keep inferred/default values in the non-merged area instead of treating them as user explicit input.

## Case E: 结构化确认缺失倾角

First input:

```text
LEO，圆轨道，300km，载荷20kg，功率200W
```

Form action:

```text
勾选 orbit_inclination_deg，user value 填 51.6，unit 选 deg，点击“应用所选确认”。
```

Expected display:

- Core gate initially fails because inclination is missing.
- Confirmation form generates `confirmation_patch.engineering_parameters.orbit_inclination_deg`.
- Patch is normalized and stored as `source=user_confirmed`.
- The system keeps first-round altitude, circular orbit wording, payload mass, and power.
- Validation, orbit consistency, orbit completion, tools, report, and advisor all rerun.
- Patch View shows `source=parameter_confirmation_form`, action, field, and round label.

## Case F: 批量确认默认角参数

Input:

```text
LEO，圆轨道，500km，倾角51.6度，载荷20kg，功率200W
```

Form action:

```text
勾选 raan_deg、arg_perigee_deg、true_anomaly_deg，保留 user value=0，unit=deg，点击“应用所选确认”。
```

Expected display:

- RAAN / arg_perigee / true_anomaly initially appear as `default_assumption` with confirmation required.
- Batch confirmation creates one `confirmation_patch` containing all selected fields.
- After rerun, selected fields appear as `user_confirmed` and `requires_confirmation=false`.
- Patch View shows old source `default_assumption` -> new source `user_confirmed`.

## Case G: 圆轨道与偏心率冲突确认

Input:

```text
LEO，圆轨道，300km，偏心率0.10，倾角10度，载荷20kg，功率200W
```

Form action:

```text
勾选 eccentricity，将 user value 改为 0，点击“应用所选确认”。
```

Expected display:

- Severe conflict blocks normal deterministic report before confirmation.
- Confirmation form explains circular orbit + nonzero eccentricity conflict and offers two explicit choices:
  - set `eccentricity=0` and keep circular orbit semantics;
  - keep the current eccentricity and confirm `orbit_type=elliptical orbit`.
- User can edit the recommended value before applying; neither choice is auto-applied.
- Applying the selected patch reruns validation and orbit consistency; if the conflict is resolved, the flow can proceed to the core gate and tools.
