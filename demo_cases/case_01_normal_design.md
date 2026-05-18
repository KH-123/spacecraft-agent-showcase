# Case 1：正常概念设计流程

## 1. 用户输入

```text
LEO，圆轨道，500km，倾角51.6度，光学遥感，目标马来西亚，6小时重访，载荷20kg，功率200W
```

## 2. 展示目标

展示参数级设计模式的完整正向链路：从自然语言输入到参数抽取、轨道补全、Core Orbit Gate、deterministic tools、概念报告、RAG-enhanced LLM advisor 和 `current_design_state` 写入。

## 3. 预期工作流

1. LLM-first 提取显式工程参数和任务上下文。
2. 将工程参数与 `mission_context` 分离。
3. `normalizer.py` 进行字段、单位、来源、状态归一化。
4. 显式参数校验和显式轨道一致性检查通过。
5. `orbit_interpreter.py` 根据圆轨道推断 `eccentricity = 0`，根据高度推断 `semi_major_axis_km`。
6. Core Orbit Gate 检查 `semi_major_axis_km`、`eccentricity`、`orbit_inclination_deg`。
7. Gate 通过后调用 deterministic tools：orbit / mass / power。
8. `report_generator.py` 生成概念级报告。
9. RAG-enhanced LLM advisor 检索本地 Markdown 知识库，结合当前方案摘要生成只读设计评审建议。
10. 有效结果写入 `current_design_state`。

## 4. 应观察到的关键现象

- `mission_context` 中可看到光学遥感、目标区域、重访时间等上下文。
- 工程参数中可看到高度、倾角、载荷质量、功率等归一化字段。
- 圆轨道语义只在没有用户冲突时推断 `eccentricity = 0`。
- Core Orbit Gate 通过后才出现工具计算结果。
- 设计建议区域与 deterministic report 分离展示。
- `advisor_report` 和 `next_actions` 只作为建议显示，不修改参数。

## 5. 面试讲解要点

- LLM 负责理解和抽取显式信息，工程计算由 deterministic modules 负责。
- `mission_context` 提升评审建议质量，但不参与 gate 或工具计算。
- RAG 的价值在于减少建议层空泛和幻觉，不保证工程计算正确。
- `current_design_state` 让后续多轮修改可以基于已有有效方案继续。

## 6. 不能误解的边界

- 这不是最终工程设计或飞行认证结果。
- RAG-enhanced advisor 不能覆盖用户参数或工具输出。
- RAG 建议不能替代轨道一致性检查、Core Orbit Gate 或专业仿真。
- 不应把展示输入 hard-code 到业务逻辑中。
