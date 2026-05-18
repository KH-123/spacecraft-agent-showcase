# Case 4：多轮参数修改

## 1. 用户输入

第一轮：

```text
LEO，圆轨道，300km，倾角51.6度，载荷20kg，功率200W
```

第二轮：

```text
高度改为500km
```

## 2. 展示目标

展示 `current_design_state` 如何支持多轮参数级更新：保留上一轮有效显式参数，并用最新用户显式输入覆盖同名旧参数。

## 3. 预期工作流

1. 第一轮按正常参数级流程运行，并写入 `current_design_state`。
2. 第二轮识别为对当前方案的修改意图。
3. 系统提取最新显式高度。
4. 最新用户显式高度覆盖上一轮高度。
5. 其他上一轮显式参数继续保留。
6. inferred / default 参数不参与覆盖，只在新一轮重新计算。
7. Patch View 显示高度 `300km -> 500km`。
8. 重新执行 validation、orbit_consistency、orbit_interpreter、Core Orbit Gate、deterministic tools、report 和 RAG-enhanced advisor。

## 4. 应观察到的关键现象

- `raw_input_history` 保留两轮原始输入。
- 高度字段来源应体现最新用户更新。
- Patch View 显示 old -> new，而不是把第二轮当成全新方案。
- SMA、轨道周期等推断 / 计算字段随新高度重新生成。
- `advisor_report` 基于更新后的当前方案重新生成。

## 5. 面试讲解要点

- 多轮更新的核心是“显式参数合并”，不是自由聊天记忆。
- 用户最新显式值优先。
- 推断值和默认值不能覆盖用户显式值。
- Patch View 和执行日志用于解释 Agent 如何更新状态。

## 6. 不能误解的边界

- 第二轮不是 hard-code 的 demo 句子，而是自然语言更新模式的一种示例。
- `current_design_state` 是 session-local，刷新页面后不会长期保存。
- RAG-enhanced advisor 只重新评审当前方案，不回写参数。
- Patch View 是演示级透明度工具，不是完整审计系统。
