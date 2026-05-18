# Case 2：严重矛盾阻断

## 1. 用户输入

```text
LEO，圆轨道，300km，偏心率0.10，倾角10度，载荷20kg，功率200W
```

## 2. 展示目标

展示系统如何保护用户显式参数优先级，并在圆轨道语义与非零偏心率冲突时阻断 deterministic tools。

## 3. 预期工作流

1. LLM-first 提取显式参数：LEO、圆轨道、高度、`eccentricity = 0.10`、倾角、载荷、功率。
2. `normalizer.py` 保留用户显式 `eccentricity = 0.10`。
3. 显式轨道一致性检查识别圆轨道与非零偏心率矛盾。
4. severe issue 出现后阻断工具调用。
5. 生成参数确认 / 冲突说明。
6. RAG-enhanced LLM advisor 只读生成下一步建议，例如让用户确认改为圆轨道 `e=0`，或保留偏心率并改为椭圆轨道。

## 4. 应观察到的关键现象

- 系统不会因为“圆轨道”自动覆盖用户显式 `eccentricity = 0.10`。
- severe conflict 出现后，不调用 orbit / mass / power deterministic tools。
- UI 应显示冲突解释、确认建议和可修复方向。
- `next_actions` 是建议，不会自动应用。

## 5. 面试讲解要点

- 用户显式参数优先级高于推断值和默认值。
- 轨道一致性检查是 deterministic guardrail，不由 LLM 判定。
- severe issue 的处理目标是阻断错误计算，而不是猜测用户真实意图。
- confirmation form / patch 机制让用户显式修正冲突。

## 6. 不能误解的边界

- LLM 不负责修复偏心率或修改轨道类型。
- RAG-enhanced advisor 不能批准继续计算。
- 工具被阻断是预期安全行为，不是系统失败。
- 不应展示伪造的工具数值结果。
