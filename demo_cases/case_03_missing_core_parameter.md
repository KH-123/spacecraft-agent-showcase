# Case 3：缺核心参数

## 1. 用户输入

```text
LEO，圆轨道，300km，载荷20kg，功率200W
```

## 2. 展示目标

展示系统可以补全有限轨道参数，但不会自动推断核心倾角；Core Orbit Gate 会在核心参数不完整时阻断工具。

## 3. 预期工作流

1. LLM-first 提取 LEO、圆轨道、高度、载荷质量和功率。
2. `normalizer.py` 归一化显式参数。
3. `orbit_interpreter.py` 可由圆轨道推断 `eccentricity = 0`。
4. 可由 altitude 推断 `semi_major_axis_km`。
5. 可由 SMA 推断 `orbit_period_min`。
6. 不自动推断 `orbit_inclination_deg`。
7. Core Orbit Gate 因缺少倾角失败。
8. 阻断 deterministic tools，输出缺失参数说明、confirmation form 和 `next_actions`。

## 4. 应观察到的关键现象

- `eccentricity` 和 SMA 可作为推断参数出现。
- 倾角仍被标记为缺失核心轨道元素。
- 工具计算不会运行。
- UI 引导用户补充轨道倾角。
- `mission_context` 如果为空，不影响 Core Orbit Gate 的判定。

## 5. 面试讲解要点

- 系统只做受控、可解释的轨道推断。
- LEO + 高度不足以唯一确定倾角。
- Core Orbit Gate 是工具调用前的硬门控。
- advisor 的 `next_actions` 帮助用户补充参数，但不自动写回。

## 6. 不能误解的边界

- 不应把 SSO、ISS 倾角或任意默认倾角自动套用到 LEO。
- 缺倾角时不应调用 deterministic tools。
- RAG 建议不是工程批准。
- 输出仍是概念级辅助，不是高保真覆盖 / 重访仿真。
