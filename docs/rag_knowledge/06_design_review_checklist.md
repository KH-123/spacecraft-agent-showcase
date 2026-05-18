# Design Review Checklist

## Purpose

This document provides a checklist for the RAG-based design advisor.

The advisor should use this checklist to review the current spacecraft parameter set, identify missing information, comment on conceptual risks, and suggest the next design refinements.

The default review scenario is a low Earth orbit remote sensing small satellite.

## Review Principle

The advisor should not simply say whether the design is good or bad.

It should answer:

- What is already defined?
- What is still missing?
- Which parameters may be weak or risky?
- Which assumptions require user confirmation?
- What should the user refine next?

All comments should remain at the conceptual or preliminary design level.

## 1. Mission Objective

Check whether the mission objective is clear.

Key questions:

- Is the mission type specified?
- Is it remote sensing, communication, science, navigation, or another mission?
- Is the main mission output clear?
- Is the target user or application clear?

For the default MVP, remote sensing is the primary supported mission type.

If the mission is not remote sensing, the advisor should state that current review rules are mainly optimized for LEO remote sensing small satellites and that other missions are only assessed conceptually.

## 2. Target Region and Coverage

Check whether the target region and coverage requirement are defined.

Key questions:

- Is the target region specified?
- Is the coverage global, regional, or point-target based?
- Is revisit time specified?
- Is the required observation frequency clear?

Missing target region or revisit requirement should be treated as an important mission definition gap.

Advisor comment example:

> The current input provides orbit and platform parameters, but the target region and revisit requirement are not yet defined. These are important for judging whether the selected orbit inclination and altitude are suitable.

## 3. Orbit Parameter Completeness

Check whether the core orbit parameters are available.

Core orbit parameters:

- semi-major axis or altitude
- eccentricity
- inclination

Additional orbit parameters:

- RAAN
- argument of perigee
- true anomaly
- orbit type
- orbit period

If RAAN, argument of perigee, or true anomaly are defaulted to 0 deg, the advisor should remind the user that these are default assumptions requiring confirmation.

## 4. Orbit Design Reasonableness

Check whether the orbit design is conceptually reasonable.

Review points:

- LEO altitude should be consistent with the intended mission.
- Very low LEO may increase atmospheric drag and orbit lifetime risk.
- SSO is commonly used for remote sensing missions requiring stable lighting conditions.
- Inclination affects target coverage, revisit behavior, and launch constraints.
- Circular orbits are commonly used for stable observation geometry.
- Eccentric orbits require additional attention to perigee altitude and varying observation geometry.
- GEO or geostationary descriptions should not be mixed with low Earth orbit altitudes.

Physical contradictions should be handled by `orbit_consistency.py`, not by RAG alone.

## 5. Payload Definition

Check whether the payload is sufficiently defined.

Key questions:

- Is the payload type specified?
- Is it optical, multispectral, infrared, SAR, communication, or scientific payload?
- Is payload mass given?
- Is payload power given?
- Is the required resolution, swath, sensitivity, or measurement target given?

For remote sensing missions, payload type is especially important because it strongly affects:

- power demand
- data volume
- pointing requirement
- thermal control
- platform mass
- communication design

If only payload mass and power are given, the advisor should note that mission performance cannot be assessed without payload type and performance requirements.

## 6. Mass Budget

Check whether mass information is complete.

Key questions:

- Is payload mass provided?
- Is platform mass provided?
- Is total satellite mass provided?
- Is mass margin considered?
- Are subsystem masses estimated or missing?

Important distinction:

- payload mass is not equal to total satellite mass
- total satellite mass cannot be fully determined from payload mass alone

If only payload mass is provided, the advisor should suggest confirming platform mass or allowing a conceptual mass estimate.

## 7. Power Budget

Check whether power information is complete.

Key questions:

- Is payload power provided?
- Is platform bus power provided?
- Is peak power or average power specified?
- Is solar array power considered?
- Is battery capacity considered?
- Is eclipse operation considered?
- Is power margin included?

If only payload power is provided, the advisor should state that full spacecraft power closure is not yet confirmed.

Advisor comment example:

> The provided payload power helps estimate the load level, but the full power budget also depends on platform consumption, duty cycle, eclipse duration, solar array sizing, battery capacity, and design margin.

## 8. Communication and Data Closure

Check whether the mission data loop is closed.

Key questions:

- Is daily data volume specified?
- Is imaging frequency specified?
- Is downlink rate specified?
- Is communication frequency band specified?
- Is ground station access considered?
- Is onboard storage capacity considered?

For remote sensing missions, data generation and data downlink are critical.

If no data volume or downlink information is provided, the advisor should identify this as a major missing item.

## 9. Mission Lifetime

Check whether mission lifetime is specified.

Key questions:

- Is the mission lifetime given?
- Is the lifetime consistent with orbit altitude?
- Is orbit decay or station keeping relevant?
- Are degradation effects considered at least conceptually?

Suggested conceptual lifetime choices:

- 6 months
- 1 year
- 3 years
- 5 years

For low-altitude LEO cases, mission lifetime and orbit maintenance should be highlighted.

## 10. Attitude and Pointing

Check whether attitude control requirements are defined.

Key questions:

- Is pointing accuracy required?
- Is pointing stability required?
- Is target tracking needed?
- Is imaging payload pointing direction defined?
- Is agile maneuvering required?

For remote sensing missions, pointing requirement is closely related to image quality and revisit performance.

If attitude requirements are missing, the advisor should suggest adding at least a conceptual pointing accuracy requirement.

## 11. Propulsion and Orbit Maintenance

Check whether propulsion or orbit maintenance is relevant.

Key questions:

- Is propulsion included?
- Is orbit maintenance required?
- Is drag compensation needed?
- Is end-of-life disposal considered?

This is especially important for low LEO or long-duration missions.

The advisor should not design the propulsion system, but may suggest confirming whether propulsion is required.

## 12. Thermal, Structure, and Reliability Follow-up

The first MVP does not perform detailed thermal, structural, vibration, or reliability analysis.

However, the advisor may suggest follow-up checks when relevant.

Examples:

- high payload power may require thermal review
- large payload mass may affect structure and attitude control
- long mission lifetime may require reliability and degradation review
- high data rate may affect thermal and power design

These should be framed as follow-up engineering work, not final conclusions.

## 13. Parameter Source and Assumption Traceability

Check whether the advisor can distinguish between:

- user-provided parameters
- inferred parameters
- default assumptions
- missing parameters
- tool-calculated results

Default or inferred parameters should be clearly identified.

The advisor should not treat inferred or default values as confirmed user requirements.

## 14. Recommended Next-step Priority

The advisor should recommend a small number of next steps.

Preferred priority order:

1. Fix severe consistency issues if any.
2. Confirm missing core orbit parameters.
3. Confirm mission objective, target region, and revisit requirement.
4. Confirm payload type and payload performance.
5. Confirm mission lifetime.
6. Confirm data volume and downlink assumptions.
7. Confirm power and mass margins.
8. Confirm attitude, propulsion, and follow-up subsystem constraints.

Avoid giving too many recommendations at once.

## Advisor Output Style

The advisor should use a warm but clear tone.

Preferred wording:

> The current parameter set is sufficient for a preliminary orbit and platform-level estimate, but several mission-level constraints remain to be confirmed.

Avoid wording such as:

> The design is complete.
> The mission is feasible.
> The satellite meets all requirements.

## Language Requirement

The final advisor report should be written in Chinese by default.

Use concise and professional engineering language.

Parameter names, units, and structured field names may remain in English where this improves clarity.

Preferred Chinese wording examples:

> 当前参数集已支持初步轨道与平台级估算，但仍有若干任务级约束需要进一步确认。

> 该轨道高度在概念设计阶段可能带来较明显的大气阻力和轨道寿命风险，建议结合任务寿命和轨道维持能力进一步检查。

> 当前尚未提供载荷类型、数据量和下行链路参数，因此还不能判断遥感任务的数据闭环是否成立。

## Suggested Advisor Sections

The final advisor report may use the following sections:

1. Current Design Summary
2. Main Conceptual Risks
3. Parameter Reasonableness Comments
4. Missing Parameters and Suggested Ranges
5. Recommended Next Steps
6. Conceptual Design Limitations

The report should be concise and should not repeat the full design report.