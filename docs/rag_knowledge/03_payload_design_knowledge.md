# Payload Design Knowledge for Conceptual Spacecraft Design

## 1. Purpose

This document provides payload-related conceptual design knowledge for the RAG-based design advisor.

The default scenario is a low Earth orbit remote sensing small satellite.

This document helps the advisor explain:

- why payload type matters
- why payload mass and payload power alone are not enough
- how different payload types affect spacecraft design
- what mission performance parameters are usually needed
- what missing information should be confirmed by the user

This document is not a payload design handbook, not an instrument specification, and not a substitute for detailed optical, radar, thermal, structural, or communication design.

## 2. Scope and Assumptions

The document mainly applies to conceptual review of:

- optical remote sensing payloads
- multispectral or hyperspectral payloads
- infrared payloads
- SAR payloads
- simple non-remote-sensing payload references, such as communication or science payloads

The advisor should use this document to generate design review comments, not to calculate payload performance.

Payload-related numerical values should not be fabricated by the advisor.

If deterministic payload tools are not available, payload comments should remain conceptual.

## 3. Representative Payload Mission Examples

The following examples are representative public mission references for conceptual comparison only.

They should not be treated as strict design templates.

| Mission / System | Payload Type | Conceptual Design Implication |
|---|---|---|
| Landsat 8 | Operational Land Imager and Thermal Infrared Sensor | A land observation mission may combine visible, near-infrared, short-wave infrared, and thermal infrared observations. Payload selection is tied to long-term calibrated Earth observation. |
| Sentinel-2 | High-resolution multispectral imaging payload | Multispectral remote sensing requires spectral band definition, swath, spatial resolution, calibration, and systematic data acquisition planning. |
| PlanetScope / Dove-like smallsat imaging | Small optical imaging payloads in a constellation | High revisit may rely on constellation scale and operational tasking, not only one satellite payload. |
| ICEYE / Capella-like SAR systems | Synthetic aperture radar payload | SAR can provide day-night and all-weather imaging capability, but usually introduces stronger power, data, pointing, and processing demands than simple optical imaging. |

Key lesson:

> Payload type is a first-order driver of spacecraft mass, power, data volume, attitude control, thermal design, and mission operations.

The advisor should not judge mission feasibility from `payload_mass_kg` and `payload_power_W` alone.

## 4. Why Payload Type Matters

Payload type determines what the spacecraft is actually designed to do.

For remote sensing missions, the payload directly affects:

- mission performance
- spacecraft pointing requirement
- data volume
- power demand
- thermal control
- orbit selection
- onboard storage
- downlink requirement
- calibration need
- task planning and operations

If the user only provides payload mass or payload power, the system may estimate rough platform impact, but it cannot assess whether the mission objective is satisfied.

Advisor statement:

> 当前用户已提供载荷质量或载荷功率，但尚未说明载荷类型。对于遥感任务，载荷类型会直接影响分辨率、幅宽、数据量、姿态指向、热控和通信链路，因此当前还不能判断任务能力是否闭合。

## 5. Main Payload Types

### 5.1 Optical Imaging Payload

Optical imaging payloads observe reflected sunlight in visible or near-visible bands.

Conceptual characteristics:

- usually suitable for daytime Earth observation
- affected by cloud cover and lighting conditions
- often coupled with sun-synchronous orbit for stable illumination
- performance depends on aperture, detector, focal length, altitude, pointing stability, and image processing
- data volume depends on resolution, swath, imaging frequency, compression, and number of bands

Important missing parameters:

- ground resolution or GSD
- swath width
- imaging frequency
- target region
- spectral bands
- pointing accuracy
- local time or lighting requirement
- daily data volume

Advisor statement:

> 若任务为光学遥感，应进一步确认空间分辨率、幅宽、成像频次、目标区域和光照条件。仅给出载荷质量和功率不足以判断成像任务是否满足需求。

### 5.2 Multispectral or Hyperspectral Payload

Multispectral and hyperspectral payloads observe multiple spectral bands.

Conceptual characteristics:

- useful for vegetation, land use, water, mineral, agriculture, and environmental monitoring
- spectral band configuration is mission-specific
- data volume may increase with band number and resolution
- calibration and radiometric consistency are important
- stable illumination can be important for comparable observations

Important missing parameters:

- number of spectral bands
- wavelength range
- ground resolution
- swath width
- radiometric requirement
- calibration requirement
- data volume
- revisit requirement

Advisor statement:

> 多光谱/高光谱载荷不仅需要质量和功率参数，还需要明确谱段数量、波段范围、分辨率、幅宽和定标需求，否则难以判断载荷是否支撑任务目标。

### 5.3 Infrared Payload

Infrared payloads observe thermal or infrared radiation.

Conceptual characteristics:

- may be used for temperature, fire, night observation, or thermal anomaly monitoring
- detector temperature and thermal stability can be important
- thermal control may be more demanding than simple visible imaging
- background radiation and calibration can affect measurement quality
- data volume and pointing requirements remain mission-dependent

Important missing parameters:

- infrared band
- temperature sensitivity
- spatial resolution
- calibration requirement
- detector cooling or thermal control assumption
- duty cycle
- target type

Advisor statement:

> 若载荷为红外探测，应进一步确认探测波段、灵敏度、热控或制冷需求、定标方式和工作模式。当前 demo 不进行详细红外载荷设计，只能给出概念级风险提示。

### 5.4 SAR Payload

Synthetic aperture radar payloads actively transmit and receive microwave signals.

Conceptual characteristics:

- can support day-night imaging
- can work through cloud cover and many weather conditions
- usually has higher peak power demand than passive optical imaging
- often generates significant data volume
- requires careful attitude, timing, antenna, thermal, and processing considerations
- imaging mode strongly affects resolution, swath, power, and data volume

Important missing parameters:

- radar band
- imaging mode
- resolution
- swath
- duty cycle
- peak power
- average power
- data volume
- pointing and attitude control needs

Advisor statement:

> 若任务采用 SAR 载荷，应重点确认峰值功率、平均功率、成像模式、数据量、姿态指向和热控约束。SAR 的平台压力通常不能仅用一个载荷质量参数概括。

### 5.5 Communication Payload

Communication payloads are not the default focus of the current LEO remote sensing demo.

If the user describes a communication mission, the advisor should note that the current review logic is mainly optimized for remote sensing small satellites.

Communication payload review usually requires:

- frequency band
- coverage area
- user terminal assumptions
- link budget
- antenna gain
- EIRP
- bandwidth
- service availability
- constellation or coverage architecture

Advisor statement:

> 当前 demo 主要面向低轨遥感小卫星。如果任务为通信卫星，需要进一步引入频段、链路预算、覆盖区域和服务容量等参数；当前系统只能提供概念级提醒。

### 5.6 Science Payload

Science payloads are mission-specific.

They may require:

- measurement target
- sensitivity
- noise budget
- pointing stability
- calibration plan
- thermal stability
- orbit environment
- data acquisition strategy

Advisor statement:

> 若任务为科学探测载荷，需要根据具体测量目标定义灵敏度、噪声、定标、热稳定性和观测几何。当前 demo 不应自动套用遥感载荷规则。

## 6. Payload Mass and Payload Power

### 6.1 Payload Mass

`payload_mass_kg` is an important input for platform sizing.

It affects:

- total spacecraft mass
- structural support
- center of mass
- launch compatibility
- attitude control torque
- integration complexity
- mass margin

However, payload mass alone does not define payload capability.

A 20 kg optical camera, a 20 kg SAR payload, and a 20 kg science payload can impose very different requirements.

Advisor statement:

> `payload_mass_kg` 可用于初步质量估算，但不能单独说明载荷能力。建议补充载荷类型、性能指标和工作模式。

### 6.2 Payload Power

`payload_power_W` affects the spacecraft power system.

It drives:

- solar array sizing
- battery sizing
- duty cycle planning
- thermal load
- peak vs average power review
- payload operation schedule

Payload power should be distinguished from:

- platform bus power
- total spacecraft power
- peak power
- average power
- standby power
- payload duty cycle

Advisor statement:

> `payload_power_W` 不等于整星功耗。当前功率参数需要结合平台功耗、载荷工作占空比、日照/阴影周期、电池容量和功率裕度进一步确认。

## 7. Payload Performance Parameters

For remote sensing payloads, the following parameters are often more important than mass and power alone.

### 7.1 Ground Resolution or GSD

Ground resolution describes the size of ground features that can be distinguished.

It depends on:

- orbit altitude
- aperture
- focal length
- detector
- motion compensation
- pointing stability
- image processing

The advisor should not infer resolution from altitude alone.

### 7.2 Swath Width

Swath width affects coverage and revisit.

A wider swath may improve coverage, but can affect resolution, optics, sensor design, data volume, and calibration.

### 7.3 Spectral Bands

Spectral bands define what physical information the payload can observe.

For example:

- visible bands may support general imaging
- near-infrared bands may support vegetation analysis
- short-wave infrared bands may support land and material studies
- thermal infrared bands may support temperature-related observation

### 7.4 Imaging Frequency and Duty Cycle

Imaging frequency affects:

- data volume
- power usage
- thermal load
- onboard storage
- downlink pressure
- task scheduling

High imaging frequency may require stronger power, data, and thermal support.

### 7.5 Pointing Requirement

Payload pointing affects image quality and target access.

High-resolution imaging usually requires more careful attitude pointing and stability.

If pointing requirement is missing, the advisor should ask for at least a conceptual-level requirement.

## 8. Payload and Platform Coupling

Payload design is tightly coupled with spacecraft platform design.

### 8.1 Coupling with Orbit

Payload and orbit must be evaluated together.

Examples:

- optical payloads may benefit from SSO for stable lighting
- high-resolution imaging may prefer lower altitude but must handle drag and lifetime
- regional monitoring needs inclination and revisit assessment
- wide-swath sensors can reduce revisit pressure
- SAR may have different orbit and operations constraints than optical imaging

### 8.2 Coupling with Power

Payload power affects:

- solar array
- battery
- power electronics
- thermal dissipation
- operation duty cycle
- payload scheduling

A high-power payload may be feasible only if the duty cycle is low or the platform power system is sized accordingly.

### 8.3 Coupling with Data

Payload data generation affects:

- onboard storage
- compression strategy
- downlink rate
- ground station use
- latency
- mission operations

Remote sensing missions cannot be considered closed if data generation and data downlink are not addressed.

### 8.4 Coupling with Attitude Control

Payload pointing drives attitude control requirements.

High-resolution imaging, target tracking, off-nadir pointing, and agile revisit all increase attitude control complexity.

### 8.5 Coupling with Thermal Design

Payload power and detector requirements affect thermal design.

Infrared and high-power radar payloads may require stronger thermal attention.

The current demo should only flag this as a conceptual risk unless thermal tools are implemented.

## 9. Common Payload Risk Patterns

### 9.1 Payload Type Missing

Risk:

- mission capability cannot be assessed
- mass and power estimates lack context
- data and pointing requirements unknown

Advisor comment:

> 当前尚未提供载荷类型。建议至少说明是光学、多光谱/高光谱、红外、SAR、通信或科学探测载荷。

### 9.2 Only Payload Mass Provided

Risk:

- platform impact can be roughly estimated
- mission performance cannot be evaluated
- power, data, and pointing are unknown

Advisor comment:

> 当前仅提供了载荷质量，可用于初步质量估算，但还不足以判断任务能力。建议补充载荷类型、功率、分辨率、幅宽和工作模式。

### 9.3 Only Payload Power Provided

Risk:

- power load is partially defined
- mass, data, and performance are unknown
- peak and average power may be confused

Advisor comment:

> 当前仅提供了载荷功率，尚不能判断整星功率闭合。建议区分载荷峰值功率、平均功率和工作占空比，并补充平台功耗或功率裕度。

### 9.4 Remote Sensing Mission without Resolution or Swath

Risk:

- orbit suitability cannot be assessed
- revisit and coverage cannot be evaluated
- payload capability unknown

Advisor comment:

> 对遥感任务而言，分辨率和幅宽是判断任务能力的重要输入。当前缺少这些参数，因此还不能判断轨道和载荷组合是否满足观测需求。

### 9.5 High Revisit Requirement without Payload Swath

Risk:

- revisit cannot be judged
- constellation need unknown
- off-nadir pointing may be required

Advisor comment:

> 重访能力不仅取决于轨道，也取决于载荷幅宽、侧摆能力和星座规模。建议补充幅宽或成像视场参数。

### 9.6 SAR-like Payload without Power and Data Detail

Risk:

- power system may be underestimated
- data volume may be underestimated
- thermal and attitude impact may be underestimated

Advisor comment:

> 如果任务采用 SAR 类载荷，应进一步确认峰值功率、平均功率、成像模式、数据量和热控约束，否则平台设计风险较高。

## 10. Missing Payload Parameters to Ask

When payload information is incomplete, the advisor should prioritize a small number of follow-up questions.

Priority order for remote sensing missions:

1. payload type
2. ground resolution or GSD
3. swath width
4. imaging frequency or duty cycle
5. spectral bands or sensing mode
6. payload mass
7. payload power
8. daily data volume
9. pointing accuracy or stability
10. calibration requirement
11. thermal or cooling requirement if relevant

The advisor should not ask all questions at once unless the input is extremely incomplete.

## 11. Advisor-use Knowledge Statements

The following short statements are useful for RAG synthesis.

- Payload type is a first-order driver of spacecraft design.
- Payload mass and payload power are useful but not sufficient to judge mission capability.
- Optical payloads depend on lighting, cloud condition, resolution, swath, and pointing stability.
- Multispectral and hyperspectral payloads require spectral band and calibration information.
- Infrared payloads may require additional thermal control consideration.
- SAR payloads can support day-night and all-weather imaging but often create stronger power and data pressure.
- Remote sensing missions need resolution, swath, imaging frequency, target region, and data volume for meaningful review.
- Payload data generation must be checked with onboard storage and downlink capability.
- High-resolution or agile imaging increases attitude control requirements.
- RAG advisor should flag missing payload information but must not invent payload specifications.

## 12. Recommended Advisor Output Examples

### Example 1: Payload mass and power only

> 当前用户已提供 `payload_mass_kg` 和 `payload_power_W`，这有助于进行初步质量和功率估算。但由于尚未提供载荷类型、分辨率、幅宽和成像频次，当前还不能判断遥感任务能力是否闭合。建议优先补充载荷类型，例如光学、多光谱、红外或 SAR。

### Example 2: Optical remote sensing task

> 若任务为光学遥感，建议进一步确认空间分辨率、幅宽、目标区域、成像频次和光照条件。轨道高度和 SSO 选择应与这些载荷需求共同评估。

### Example 3: SAR payload task

> 如果任务采用 SAR 载荷，应重点关注峰值功率、平均功率、成像模式、数据量和热控压力。当前 demo 可给出概念级风险提示，但不应替代详细雷达载荷设计。

### Example 4: High revisit mission

> 当前任务若要求较高重访频次，仅靠轨道参数还不足以判断是否满足需求。建议补充载荷幅宽、侧摆能力、成像频次以及是否考虑星座方案。

## 13. Boundary Reminder

The advisor provides conceptual payload design comments only.

It must not:

- design the payload instrument
- invent payload resolution
- invent swath width
- invent data volume
- overwrite user-provided payload mass or power
- replace deterministic mass or power tools
- claim that payload performance satisfies the mission
- claim that the payload is flight-ready

Payload-related comments should be treated as design review guidance.