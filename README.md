# 🛰️ 航天器总体设计 AI Agent Demo

**Spacecraft Conceptual Design AI Agent Demo**

一个轻量级的航天器概念级/初步设计 AI Agent 演示项目。系统面向低地球轨道遥感小卫星的早期设计阶段，通过自然语言输入任务需求或设计参数，自动完成参数提取、轨道推断、物理一致性检查、确定性工程计算，并生成结构化概念设计报告。

> ⚠️ **本系统仅用于概念设计辅助，所有输出均为初步估算，不构成最终工程设计或飞行合格结论。**

---

## ✨ 功能特性

### 双模式架构

| 模式 | 目标用户 | 输入形式 | 核心能力 |
|------|----------|----------|----------|
| **参数级设计模式** | 专业用户/学生 | 结构化设计参数（如 `LEO，圆轨道，500km，倾角51.6度，载荷20kg，功率200W`） | 完整参数级设计流程：提取→归一化→两遍校验→轨道推断→Core Gate→确定性工具→报告→RAG 建议 |
| **任务级需求模式** | 非专业用户 | 自然语言任务目标（如"设计一颗 6 小时重访马来西亚的遥感卫星"） | 任务意图理解、缺失设计驱动识别、候选参数草案生成（2–3 组概念级选项） |

### 参数级设计核心能力

- ✅ **LLM-first + 规则 fallback 参数提取** — 支持中英文混合输入、单位缩写、同义词、typo 容错
- ✅ **确定性字段/单位归一化** — 纯规则驱动，支持 10+ 种单位制转换（km/m、kg/g/t、W/kW、deg 等）
- ✅ **轨道参数智能推断** — 圆轨道→e=0、高度→半长轴、半长轴→轨道周期、SSO+高度→J2 概念倾角
- ✅ **两遍物理一致性检查** — 显式参数预检查 + 轨道补全后全量检查（8 项检查）
- ✅ **Core Orbit Gate 门控** — 确保核心轨道参数齐全后才执行工具计算
- ✅ **硬阈值守卫** — 高度/寿命/质量/功率的 pass/warning/severe 三级校验
- ✅ **确定性工程计算** — 轨道周期/速度、质量预算、太阳能电池阵面积、电池容量
- ✅ **结构化 Markdown 概念设计报告** — 参数表、任务上下文、轨道推断、工具结果、RAG 建议
- ✅ **参数确认报告** — 严重矛盾时阻断正常流程，生成确认报告
- ✅ **RAG-enhanced 设计评审** — 本地 Markdown 检索 + 可选 LLM 综合，输出只读 `advisor_report` / `next_actions`，不参与门控或参数回写
- ✅ **Agent Actions / 下一步建议** — 状态感知的下一步行动建议
- ✅ **多轮参数补充与方案更新** — 会话内保留设计状态，支持增量修改
- ✅ **Patch View 差异视图** — 多轮修改的 old→new 对比，含来源/状态/类别元数据
- ✅ **结构化参数确认表单** — 对缺失/默认轨道参数提供确认补丁，不绕过校验
- ✅ **执行日志事件流** — 结构化会话事件，中文描述
- ✅ **参数来源可追溯** — 每个参数携带 `source` 字段贯穿全流程

### 任务级需求模式能力

- ✅ 任务意图理解（目标、区域、重访需求、载荷提示）
- ✅ 缺失设计驱动识别（9 项约束项）
- ✅ 候选参数草案生成（SSO 基线、倾斜 LEO、小星座 SSO）
- ✅ 用户确认后进入参数级流程

---

## 🏗️ 系统架构

### 核心设计原则

1. **LLM 与确定性工具严格分离** — LLM 负责自然语言理解/参数提取，确定性工具负责所有工程计算
2. **显式参数优先** — 用户提供的参数永远不会被推断值或默认值覆盖
3. **两遍一致性检查** — 显式参数预检查 + 轨道补全后全量检查
4. **参数来源可追溯** — 每个参数携带 `source` 字段（`user_provided` → `llm_extracted` → `inferred_from_*` → `tool_computed` 等）
5. **RAG-enhanced advisor 只读** — 设计评审层不修改参数、不参与门控、不替代 deterministic tools

### 模块依赖关系

```
app.py（Streamlit 主入口）
  │
  ├─ ui_helpers.py（UI 渲染：参数卡片、状态卡、确认表单、Patch View、执行日志）
  │
  ├─ agents/llm_extractor.py     ← LLM 参数提取（OpenAI-compatible）
  ├─ agents/parser.py             ← 规则 fallback 提取（正则）
  ├─ agents/normalizer.py         ← 字段/单位归一化（纯规则）
  ├─ agents/validator.py          ← 硬阈值守卫（纯规则）
  ├─ agents/orbit_interpreter.py  ← 轨道参数推断（纯公式）
  ├─ agents/orbit_consistency.py  ← 轨道物理一致性检查（纯公式）
  ├─ agents/parameter_inference.py ← 缺失参数 LLM/规则推断
  ├─ agents/planner.py            ← 任务分解与工具调度
  │   ├─ tools/orbit.py           ← 轨道周期、速度
  │   ├─ tools/mass.py            ← 质量预算
  │   ├─ tools/power.py           ← 太阳能阵、电池
  │   └─ agents/llm_estimator.py  ← 概念级估算 fallback
  ├─ agents/report_generator.py   ← Markdown 报告生成
  ├─ agents/design_advisor.py     ← RAG-enhanced LLM 设计评审助手
  │   └─ agents/rag_retriever.py  ← 本地 Markdown 关键词检索
  ├─ agents/mission_context_extractor.py ← 任务上下文提取
  ├─ agents/mission_interpreter.py       ← 任务级需求理解
  └─ agents/design_draft_generator.py    ← 候选草案生成
```

### 参数级设计完整流程

```
用户输入（自然语言）
  │
  ├─ 工程参数提取
  │   ├─ LLM 提取（llm_extractor.py）— 仅提取显式参数，不推断、不修正
  │   └─ 规则 fallback（parser.py）— 正则匹配
  │
  ├─ 归一化（normalizer.py）— 字段名映射、单位转换
  │
  ├─ 第一遍校验（仅检查显式参数）
  │   ├─ validate_parameters()         ← 硬阈值守卫
  │   └─ validate_orbit_consistency()  ← 轨道一致性
  │   → 严重矛盾？生成参数确认报告，停止
  │
  ├─ 轨道推断（orbit_interpreter.py）
  │   允许：圆轨道→e=0、高度→SMA、SMA→周期、SSO+高度→J2倾角
  │   禁止：LEO+高度→自动推断倾角、推断非轨道参数、覆盖用户值
  │
  ├─ 第二遍校验（补全后全量检查）
  │
  ├─ Core Orbit Gate
  │   要求：semi_major_axis_km + eccentricity + orbit_inclination_deg
  │   → 门控未通过？生成参数确认报告
  │
  ├─ 确定性工具计算（planner.py → tools/）
  │   ├─ orbit_analysis → solar_array / battery
  │   └─ mass_budget
  │
  ├─ 报告生成（report_generator.py）
  │
  └─ RAG-enhanced 只读设计评审（design_advisor.py + rag_retriever.py）
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动应用（无需 API key）

```bash
streamlit run app.py
```

没有 API key 时，系统会自动使用规则解析器（rules-based parser）提取参数，所有功能正常运行。

### 3. 配置 LLM API（可选，推荐）

复制 `.env.example` 为 `.env`，然后配置你的 API key：

```bash
# DeepSeek 官方 API（推荐）
LLM_API_KEY=sk-your-deepseek-api-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
LLM_TIMEOUT_SECONDS=30
```

也支持任何 OpenAI-compatible API：

| 平台 | LLM_BASE_URL | LLM_MODEL |
|------|-------------|-----------|
| DeepSeek | https://api.deepseek.com | deepseek-chat |
| OpenAI | https://api.openai.com/v1 | gpt-4o-mini |
| ModelScope | https://api.modelscope.cn/v1 | Qwen/Qwen2.5-7B-Instruct |

配置后，系统将使用 LLM 进行参数提取，支持中文单位（吨、千瓦）、轨道类型（极地轨道、太阳同步轨道）、typo 容错等高级功能。

---

## 📖 使用示例

### 参数级模式（推荐展示）

**输入：**
```
LEO，圆轨道，500km，倾角51.6度，光学遥感，目标马来西亚，6小时重访，载荷20kg，功率200W
```

**系统执行流程：**
1. LLM 提取显式参数（轨道类型、高度、倾角、载荷质量、功率）
2. `mission_context_extractor` 提取任务上下文（光学遥感、马来西亚、6小时重访）
3. `orbit_interpreter` 推断 `eccentricity=0`（圆轨道）、`semi_major_axis_km=6878.137`、`orbit_period_min`（两体公式）
4. Core Gate 通过 → 执行确定性工具计算
5. 生成 Markdown 概念设计报告
6. `design_advisor` 作为 RAG-enhanced LLM advisor 给出只读设计评审建议

### 任务级模式

**输入：**
```
设计一颗 6 小时重访马来西亚的遥感卫星
```

**系统执行流程：**
1. 任务意图理解（遥感、马来西亚、6小时重访）
2. 识别缺失设计驱动（分辨率、幅宽、传感器类型、轨道偏好等）
3. 生成 2–3 组候选参数草案
4. 用户确认草案后，参数标记为 `user_confirmed_llm_inferred` 并进入参数级流程

---

## Demo Cases

用于 GitHub / 面试展示的参数级流程案例已整理到 [`demo_cases/README.md`](demo_cases/README.md)，覆盖正常流程、严重矛盾阻断、缺核心参数和多轮参数修改。

---

## 🔧 工程计算工具

| 工具模块 | 功能 | 输入参数 | 方法 |
|---------|------|---------|------|
| `tools/orbit.py` | 轨道周期估算 | 轨道高度 (km) | 开普勒第三定律（两体公式） |
| `tools/orbit.py` | 轨道速度计算 | 轨道高度 (km) | 圆轨道速度公式 v = sqrt(mu/r) |
| `tools/power.py` | 太阳能电池板面积估算 | 功率需求 (W) | A = P / (G·η·Kd·F_sun) |
| `tools/power.py` | 电池容量估算 | 功率需求 (W)、地影时间 (h) | C_Wh = P·T / (DoD·η) |
| `tools/mass.py` | 质量预算估算 | 有效载荷质量 (kg)、轨道类型 | 基于历史小卫星质量分数 |

---

## ⚠️ 局限性

- 所有计算结果均为概念设计阶段初步估算
- 质量预算基于历史小卫星统计比例
- 电源系统估算未考虑季节性变化和寿命末期衰减
- 未考虑轨道摄动、空间环境效应等二阶影响
- 无覆盖/重访/星座相位仿真
- 无详细通信链路预算
- 无热控、姿控、推进详细分析
- 无用户登录、云部署、容器化

---

## 📄 许可证

MIT License

---

## 🙏 致谢

本项目探索 LLM 在工程设计流程中的可控使用方式，核心关注：
- 如何让 LLM 处理自然语言理解，但不让它编造工程数值？
- 如何让确定性工具始终拥有最终计算权？
- 如何让参数来源可追溯、可审计？
- 如何让 AI 建议层（RAG）只提建议、不篡改数据？
