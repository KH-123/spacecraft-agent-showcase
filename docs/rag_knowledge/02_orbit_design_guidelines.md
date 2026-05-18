# Orbit Design Knowledge for Conceptual Spacecraft Design

## 1. Purpose

This document provides orbit design knowledge for the RAG-based design advisor in the spacecraft conceptual design demo.

The default application scenario is a low Earth orbit remote sensing small satellite.

This document is intended to help the advisor explain:

- why certain orbit parameters matter
- what typical orbit choices exist in remote sensing missions
- what trade-offs are associated with altitude, inclination, eccentricity, and revisit
- which missing parameters should be confirmed by the user
- which parameter combinations may indicate conceptual design risk

This document is not a flight dynamics handbook, not a mission design standard, and not a substitute for deterministic orbit calculation.

The advisor must not use this document to overwrite user parameters, replace `orbit_consistency.py`, or claim that a design is final or flight-qualified.

## 2. Scope and Assumptions

The knowledge in this document is primarily applicable to:

- LEO remote sensing small satellites
- conceptual or preliminary orbit review
- early-stage mission parameter discussion
- design advisor comments after deterministic tools have run

The document may also provide rough background for other mission types, but non-remote-sensing missions should be treated only as conceptual references.

The advisor should always distinguish between:

- user-provided parameters
- inferred orbit parameters
- default assumptions
- deterministic tool results
- conceptual design advice

## 3. Representative Reference Missions

The following cases are representative public mission examples. They are used for conceptual comparison only and should not be treated as strict design templates.

| Mission / System | Mission Type | Orbit Feature | Conceptual Design Implication |
|---|---|---|---|
| Landsat 8 / Landsat series | Medium-resolution Earth observation | Sun-synchronous, near-polar LEO; about 705 km altitude; about 98 deg inclination; about 99 min orbital period; 16-day repeat cycle for one satellite | Long-term calibrated land observation missions often value stable illumination, repeatable ground tracks, and data continuity. |
| Sentinel-2 | Optical / multispectral Earth observation | Sun-synchronous LEO; about 786 km mean altitude; about 98.6 deg inclination; about 100 min orbital period; two-satellite constellation improves revisit | Wide-swath multispectral missions often combine SSO, constellation configuration, and systematic coverage planning. |
| PlanetScope / Dove-like smallsat constellation | High-revisit optical imaging | Sun-synchronous LEO; several-hundred-km altitude class; many small satellites; near-daily global land imaging concept | High revisit is often achieved by constellation scale rather than by one satellite alone. |
| Low-orbit remote sensing rapid-response concepts | Flexible tasking and responsive observation | LEO satellites may need frequent command uplink, telemetry feedback, ground contact, relay link, or onboard autonomy | Orbit design should be reviewed together with TT&C, ground station visibility, data downlink, and operations responsiveness. |

Key lesson:

> Historical Earth observation missions commonly use near-polar or sun-synchronous LEO orbits, but the exact altitude, inclination, repeat cycle, and constellation size are mission-dependent.

The advisor should use these examples to explain design logic, not to force the user into one fixed parameter set.

## 4. Common Orbit Classes

### 4.1 Low Earth Orbit

Low Earth orbit is commonly used for remote sensing, Earth observation, technology demonstration, some communication constellations, and small satellite missions.

Conceptual characteristics:

- close to Earth compared with MEO or GEO
- relatively short orbital period
- lower signal latency than higher orbits
- smaller instantaneous coverage footprint than higher orbits
- repeated ground passes over time
- stronger atmospheric drag influence at lower altitudes
- ground station contact is usually intermittent unless relay or constellation support is used

For remote sensing missions, LEO is attractive because lower altitude can improve observation geometry. However, LEO orbit design must also consider mission lifetime, drag, revisit, data downlink, and operations.

### 4.2 Sun-synchronous Orbit

Sun-synchronous orbit is widely used in optical and multispectral Earth observation missions.

The main design motivation is to keep the local solar time of observation approximately stable. This helps maintain comparable illumination conditions across repeated observations.

SSO is especially relevant when the mission involves:

- optical imaging
- multispectral imaging
- vegetation, land, or environmental monitoring
- repeatable observation under similar lighting
- global or near-global Earth observation

However, SSO should not be automatically forced for all remote sensing tasks.

The advisor should say:

> 如果任务需要稳定光照条件下的对地成像，可以考虑太阳同步轨道；但是否采用 SSO 仍需结合目标区域、重访周期、载荷类型和发射约束确认。

### 4.3 Polar or Near-polar Orbit

Polar or near-polar orbit is useful when the mission needs broad latitude coverage or high-latitude access.

A polar orbit usually implies an inclination close to 90 deg.

If the user says "polar orbit" but gives an inclination far from 90 deg, this should be treated as a parameter consistency issue.

### 4.4 Geostationary or GEO-related Orbit

GEO or geostationary orbit belongs to a very different orbit regime from LEO.

If the user gives GEO or geostationary wording together with a low altitude such as 500 km, this is a strong conceptual and physical inconsistency.

The advisor should explain that the orbit type and altitude need to be confirmed, but the actual consistency flag should come from `orbit_consistency.py`.

## 5. Key Orbit Parameters and Design Meaning

### 5.1 Altitude

Orbit altitude affects many coupled design aspects:

- ground resolution potential
- sensor geometry
- field of regard
- atmospheric drag
- orbit lifetime
- orbital period
- revisit behavior
- ground station contact opportunities
- link distance
- required propulsion or orbit maintenance

Lower altitude may improve observation geometry, but it usually increases atmospheric drag and lifetime sensitivity.

Higher LEO altitude may reduce drag and increase coverage footprint, but it can affect spatial resolution, link budget, and sensor sizing.

For a LEO remote sensing small satellite demo, 500–800 km can be treated as a common conceptual reference region, not a hard rule.

A 300 km orbit should not be rejected automatically, but it should trigger lifetime and drag-related review.

Advisor example:

> 当前 300 km 低轨在概念设计阶段并非绝对不可用，但大气阻力、轨道寿命和轨道维持风险较高，建议进一步确认任务寿命、推进能力或轨道维持策略。

### 5.2 Semi-major Axis

Semi-major axis is the orbit size parameter used in deterministic orbit mechanics.

For a near-circular Earth orbit, the semi-major axis can be approximated as:

```text
semi_major_axis_km = Earth_radius_km + orbit_altitude_km
```

This conversion should be performed by `orbit_interpreter.py` or deterministic tools, not by RAG.

The advisor may explain the meaning of semi-major axis, but must not overwrite it.

### 5.3 Orbit Period

Orbit period is physically coupled to semi-major axis.

For LEO, the orbital period is often on the order of about 90–100 minutes, depending on altitude.

If the user provides both altitude and period, the system should use deterministic orbit calculation to check consistency.

Example:

- 500 km altitude and about 95 min period are conceptually consistent.
- 500 km altitude and 80 min period are suspicious and should be checked.

The advisor should not decide the inconsistency by itself. It should explain issues already detected by deterministic checks.

### 5.4 Inclination

Inclination strongly affects:

- target latitude access
- ground track
- revisit behavior
- launch site compatibility
- whether the orbit is near-polar or sun-synchronous
- regional vs global coverage

Important rule:

> LEO + altitude does not determine inclination.

For parameter-level design, generic LEO altitude should not be used to automatically infer inclination.

If inclination is missing, the advisor should ask for one of the following:

- target region
- desired latitude coverage
- revisit requirement
- whether SSO is intended
- direct `inclination_deg` input from the user

Advisor example:

> 当前输入给出了低轨高度，但尚未给出轨道倾角。倾角会直接影响目标区域覆盖、重访特性和发射约束，建议补充目标区域或直接给出 `inclination_deg`。

### 5.5 Eccentricity

Eccentricity describes how circular or elliptical the orbit is.

For conceptual LEO remote sensing design, circular or near-circular orbits are common because they provide more stable observation geometry and altitude.

If the user says "circular orbit" and does not provide eccentricity, the system may infer:

```text
eccentricity = 0
```

If the user explicitly provides eccentricity, the user value must be preserved.

If the user says "circular orbit" but also gives `eccentricity=0.10`, this should be treated as a contradiction rather than silently corrected.

Advisor example:

> 用户同时给出了圆轨道语义和非零偏心率。系统应保留用户显式输入的 eccentricity，并提示该参数组合需要确认。

### 5.6 RAAN, Argument of Perigee, and True Anomaly

RAAN, argument of perigee, and true anomaly define the detailed orbit orientation and satellite position.

In early conceptual design, these parameters are often not specified by beginner users.

They may be defaulted to 0 deg only if the system clearly marks them as:

```text
source=default_assumption
requires_confirmation=true
```

The advisor should not treat defaulted values as confirmed mission requirements.

## 6. Orbit Design Trade-offs for Remote Sensing

### 6.1 Altitude vs Ground Resolution

Lower altitude can improve ground sampling geometry for a given sensor, but actual resolution also depends on aperture, detector, optics, motion compensation, atmosphere, pointing stability, and processing.

The advisor should avoid saying that altitude alone determines resolution.

Better wording:

> 较低轨道高度可能有利于观测几何，但实际空间分辨率还取决于载荷口径、探测器、姿态稳定度和成像处理等因素。

### 6.2 Altitude vs Drag and Lifetime

Lower LEO altitude usually increases atmospheric drag sensitivity.

Mission lifetime then depends on:

- altitude
- spacecraft area-to-mass ratio
- solar activity
- drag model uncertainty
- propulsion capability
- orbit maintenance strategy
- end-of-life disposal plan

The advisor should flag low altitude without claiming exact lifetime unless a deterministic lifetime tool exists.

### 6.3 Altitude vs Coverage and Revisit

Higher altitude generally increases the visible ground footprint for a sensor, but revisit depends on many coupled factors:

- altitude
- inclination
- target latitude
- sensor swath
- pointing capability
- repeat ground track
- number of satellites
- tasking strategy

The advisor must not infer revisit from altitude alone.

### 6.4 Inclination vs Target Region

Inclination should be chosen according to target region and coverage need.

Examples:

- equatorial or low-inclination orbits may be relevant for low-latitude regional missions
- near-polar orbits may support broad latitude coverage
- SSO may support repeated imaging under similar local solar time

If the user says "Malaysia revisit every 6 hours", the advisor should ask whether a single satellite is sufficient and whether constellation design should be considered.

### 6.5 Single Satellite vs Constellation

High revisit requirements often cannot be satisfied by orbit selection alone.

They may require:

- wider swath
- off-nadir pointing
- multiple satellites
- data relay
- ground station network
- onboard scheduling capability

The advisor may suggest constellation-level consideration, but should not automatically create a constellation design in parameter-level mode unless the user explicitly asks.

## 7. Orbit and Operations Coupling

Orbit design is not only geometry. It also affects operations.

For LEO remote sensing satellites, ground station contact is usually intermittent. This affects:

- command uplink
- telemetry return
- payload tasking
- data downlink
- rapid response
- onboard storage
- anomaly handling
- user-facing data delivery delay

For missions requiring near-real-time response or all-time online service, the system may need additional support such as:

- relay satellite links
- multiple ground stations
- inter-satellite links
- onboard autonomy
- task planning automation
- compressed or prioritized data products

The advisor should not design the TT&C system in detail, but it should remind the user that orbit selection and communication/operation architecture are coupled.

Advisor example:

> 低轨卫星与地面站的可见时间通常呈间断窗口。若任务要求快速响应或接近实时的数据服务，应进一步确认测控链路、地面站资源、星间/中继链路或数据下行方案。

## 8. Common Risk Patterns

The advisor should raise conceptual risk comments when the current design contains one or more of the following patterns.

### 8.1 Very Low LEO without Lifetime or Propulsion Information

Risk:

- stronger drag influence
- possible short lifetime
- possible need for orbit maintenance
- uncertainty in end-of-life disposal

Advisor comment:

> 当前轨道高度较低，但尚未提供任务寿命和推进/轨道维持能力，因此还不能判断该轨道是否能够支撑预期任务周期。

### 8.2 LEO Orbit without Inclination

Risk:

- coverage cannot be assessed
- target latitude access unknown
- revisit behavior unknown
- SSO or polar intent unclear

Advisor comment:

> 当前缺少轨道倾角，无法判断目标区域覆盖和重访特性。建议补充 `inclination_deg`、目标区域，或说明是否希望采用 SSO。

### 8.3 Circular Orbit with Nonzero Eccentricity

Risk:

- semantic contradiction
- user may have typed an inconsistent value
- orbit interpreter must not overwrite user input

Advisor comment:

> 当前输入同时包含圆轨道语义和非零偏心率，建议确认到底采用圆轨道还是椭圆轨道。

### 8.4 Altitude and Period Inconsistency

Risk:

- orbit mechanics inconsistency
- possible unit error
- possible misunderstanding between altitude and semi-major axis
- possible wrong period input

Advisor comment:

> 当前轨道高度与轨道周期之间存在物理一致性疑点，建议优先确认高度、半长轴和周期的单位及数值。

### 8.5 GEO Wording with LEO Altitude

Risk:

- orbit regime contradiction
- severe user input ambiguity

Advisor comment:

> 当前输入同时包含 GEO/geostationary 语义和低轨高度，这在轨道类型上存在明显不一致，建议优先确认轨道类型或高度参数。

### 8.6 Remote Sensing Mission without Target or Revisit Requirement

Risk:

- orbit cannot be judged against mission objective
- inclination and altitude may not be meaningful without coverage need
- single satellite vs constellation cannot be assessed

Advisor comment:

> 当前轨道参数可以支持初步轨道估算，但尚未提供目标区域和重访周期，因此还不能判断该轨道是否满足遥感任务目标。

## 9. Missing Orbit-related Parameters to Ask

When orbit information is incomplete, the advisor should recommend a small number of high-priority follow-up items.

Priority order:

1. orbit altitude or semi-major axis
2. eccentricity or circular/eccentric orbit assumption
3. inclination
4. orbit type, such as LEO / SSO / polar / GEO
5. target region
6. revisit requirement
7. mission lifetime
8. whether propulsion or orbit maintenance is available
9. RAAN, argument of perigee, and true anomaly if detailed orbit state is required

The advisor should not ask all questions at once if only a few are critical.

## 10. Parameter Selection Rationale

### 10.1 Why Altitude Matters

Altitude is not only a geometric parameter.

It affects:

- sensor-to-ground distance
- spatial resolution potential
- orbit period
- drag environment
- mission lifetime
- coverage footprint
- link distance
- eclipse and illumination geometry
- ground station access windows

Therefore, altitude should be selected with mission performance and operations in mind.

### 10.2 Why Inclination Matters

Inclination determines which latitudes the satellite can access and strongly influences ground track and revisit.

A LEO satellite with an unspecified inclination is not enough for mission-level assessment.

For regional remote sensing, target latitude and revisit requirement should guide inclination selection.

### 10.3 Why SSO Is Common in Remote Sensing

SSO supports repeated observations at similar local solar time.

This is useful for optical and multispectral missions because lighting conditions matter for image interpretation.

However, SSO is not always optimal. Some missions may prefer other inclinations due to target region, launch constraints, revisit needs, or payload characteristics.

### 10.4 Why Circular Orbit Is Often Used

Circular or near-circular orbits simplify remote sensing operations because altitude and observation geometry remain more stable.

This can simplify:

- imaging planning
- ground sampling interpretation
- power and thermal cycles
- attitude planning
- communication planning

Eccentric orbits may be useful for some specialized missions, but they require more careful review of perigee, apogee, speed variation, and observation geometry.

## 11. Conceptual Reference Ranges

These ranges are for advisor comments only.

They are not validation thresholds and must not replace `validator.py` or `orbit_consistency.py`.

| Parameter | Conceptual Reference | Advisor Interpretation |
|---|---|---|
| LEO altitude | several hundred km to about 2000 km | Useful for identifying LEO-scale orbit, not for approving design |
| LEO remote sensing altitude | often several hundred km | Must be checked with resolution, coverage, lifetime, and operations |
| Very low LEO | around a few hundred km | May require lifetime and drag review |
| Orbit period in LEO | roughly around 90–100 min | Must be computed from semi-major axis by deterministic tools |
| Circular orbit eccentricity | close to 0 | Nonzero eccentricity conflicts with circular orbit wording |
| Polar orbit inclination | close to 90 deg | Far-off inclination should be confirmed |
| SSO inclination | retrograde near-polar, altitude-dependent | Should be computed by `orbit_interpreter.py` when applicable |

## 12. Advisor-use Knowledge Statements

The following short statements are useful for RAG synthesis.

- LEO remote sensing orbit design should be evaluated together with target region, revisit requirement, payload type, mission lifetime, and data downlink.
- A low altitude may improve observation geometry but increases drag and lifetime sensitivity.
- A high altitude may reduce drag and increase coverage footprint but can affect spatial resolution and link distance.
- Inclination cannot be inferred from LEO altitude alone.
- SSO is common for optical and multispectral Earth observation, but it should not be forced without mission context.
- High revisit usually depends on swath, pointing ability, target latitude, and constellation size, not altitude alone.
- LEO ground contact is intermittent unless relay, constellation, or multiple ground stations are used.
- Circular orbit should be associated with eccentricity close to zero.
- GEO/geostationary wording should not be mixed with low Earth orbit altitude.
- Default RAAN, argument of perigee, and true anomaly values should be treated as assumptions requiring confirmation.

## 13. Recommended Advisor Output Examples

### Example 1: LEO circular orbit, 300 km, missing inclination

> 当前方案给出了 LEO、圆轨道和 300 km 高度，已可支持初步轨道尺度估算。由于用户未提供倾角，系统不应仅根据 LEO 和高度自动推断 `inclination_deg`。建议补充目标区域、重访需求，或直接给出倾角。另需注意，300 km 低轨在概念设计阶段可能带来更明显的大气阻力和轨道寿命风险，建议确认任务寿命和是否具备轨道维持能力。

### Example 2: SSO, 500 km, circular orbit

> 当前输入包含 SSO 和轨道高度，适合进行概念级太阳同步轨道倾角估算。若倾角由系统推断，应标记为 inferred，并要求用户确认。SSO 对光学或多光谱遥感任务具有稳定光照条件方面的优势，但仍需结合目标区域、重访周期和载荷类型确认是否合适。

### Example 3: 500 km altitude and 80 min period

> 当前用户同时提供了轨道高度和轨道周期。对于 500 km 级近地圆轨道，80 min 周期可能与两体轨道计算结果不一致。该问题应由 `orbit_consistency.py` 或 `tools/orbit.py` 给出确定性检查结果，advisor 只负责解释该矛盾可能来自单位错误、周期输入错误或高度/半长轴混淆。

### Example 4: Remote sensing mission without target region

> 当前轨道参数可支持初步轨道计算，但尚未提供目标区域和重访周期，因此还不能判断该轨道是否满足遥感任务目标。建议优先补充目标区域、期望重访时间、载荷幅宽或是否允许侧摆成像。

## 14. Boundary Reminder

The advisor provides conceptual orbit design knowledge only.

It must not:

- modify orbit parameters
- overwrite user-provided values
- replace deterministic orbit calculations
- replace `orbit_consistency.py`
- decide whether the core orbit gate passes
- claim that the orbit is flight-ready
- claim that the mission requirement is satisfied without target and payload constraints

All orbit-related numerical consistency checks should be handled by deterministic code.