# 面向 Codex 的开发备忘录：六类智能体的工具调用框架与工程落地（平衡可实现性/速度/成本）

## 0. 目标与约束

**目标**：在在线平台内构建六个可演进的智能体（思政型、任务型、竞赛型、课程型、评价型、探究型），实现“能用、稳定、可扩展、可评测”，并在**响应速度**与**运行成本**之间取得可控平衡。

**关键约束**：

* LLM 通过 API 调用（stateless），工具执行在本地/内网（数据库、检索、进度、竞赛库等）。
* 智能体功能后续会扩展，要求框架“工具可插拔、策略可迭代、模型可替换”。

---

## 1. 总体架构：一套编排框架 + 六个领域 Agent（共享基础设施）

### 1.1 建议采用“统一编排内核（Orchestrator）+ Agent Profile”模式

不要为每个 Agent 单独造一套链路；而是统一使用同一套状态机/有向图编排：

**统一链路（推荐默认）**

1. **Router/Planner（LLM#1）**：任务识别 + 工具计划（结构化输出）
2. **Tool Executor（本地）**：执行工具、标准化结果、脱敏/截断
3. **Synth/Responder（LLM#2）**：融合工具结果生成最终自然语言输出
4. （可选）**Guard/Policy（规则或轻量 LLM）**：合规审查、越权拦截、输出规范化

> 这样每次完整响应通常是 **2 次 LLM 调用**；只有在高风险/复杂多步任务时才升级为 3~4 次。

### 1.2 六个智能体的差异体现：Profile（配置而非分叉代码）

每个智能体通过 Profile 定义：

* 可用工具集（tool allowlist）
* 数据域与权限（scope）
* 输出风格与格式（response template）
* 典型意图与路由规则（routing hints）
* 评测指标（agent KPIs）

---

## 2. 六个智能体：能力拆解与工具依赖（从“功能”映射到“数据/工具”）

下表是工程落地所需的最小工具集（可逐步扩展）：

### 2.1 思政型（校本案例）

**核心**：用本校案例库/思政案例库检索 → 结合课程知识点进行情境化回答。

* 必要工具

  * `kb_search_case(query, top_k, filters)`：案例库检索（标签/课程/主题/年份）
  * `kb_get_case(case_id)`：拉取完整案例（用于引用与准确复述）
* 可选工具

  * `policy_check(text)`：输出合规审查（避免不当表述）

### 2.2 任务型（学生进度→待办）

**核心**：读学生进度、课程要求、截止日期 → 更新待办并提醒。

* 必要工具

  * `progress_get(student_id, course_id)`
  * `todo_list(student_id)` / `todo_upsert(student_id, items[])`
  * `course_plan_get(course_id)`（教学进度、作业节点、考核项）
* 可选工具

  * `calendar_read(student_id)`（若未来接入日历）

### 2.3 竞赛型（历史竞赛与校内获奖→建议）

**核心**：竞赛库检索、校内获奖经验与资源 → 输出个性化路线图。

* 必要工具

  * `contest_search(query, level, domain, season)`
  * `contest_history_get(school_id, contest_id)`（校内成绩、队伍构成、指导教师等）
  * `resource_search(topic)`（训练资源、课程、实验、项目库）
* 可选工具

  * `mentor_match(student_profile)`（指导老师/学长资源匹配）

### 2.4 课程型（偏好+能力→推荐专选课）

**核心**：学生画像 + 课程库 + 先修关系 + 难度/负担 → 推荐与解释。

* 必要工具

  * `student_profile_get(student_id)`（偏好、目标、已修）
  * `course_catalog_search(filters)`
  * `prereq_graph_query(course_ids)`
  * `course_eval_stats(course_id)`（历史通过率/学习负担/评价）
* 可选工具

  * `schedule_fit(student_id, term)`（课表冲突、容量、时间段）

### 2.5 评价型（达成情况→评价与改进）

**核心**：毕业要求/课程目标达成数据 → 诊断短板 → 给出可操作改进建议。

* 必要工具

  * `outcome_get(student_id, program_id, term_range)`
  * `rubric_get(course_id)` / `assessment_get(student_id, course_id)`
  * `intervention_library_search(weakness_tag)`（改进策略库）
* 可选工具

  * `trend_analyze(data)`（成长曲线、预警）

### 2.6 探究型（引导深入思考）

**核心**：较少依赖工具；主要依赖 Socratic 引导策略。

* 可选工具（视你的平台内容库）

  * `kb_search_concepts(query)`（概念/知识点检索）
  * `example_bank(query)`（例题/案例）
* 强约束：避免“直接给答案”，采用渐进式提示与反问。

---

## 3. 工具调用智能体框架：工程实现要点（Codex 实施指令）

### 3.1 核心对象模型（建议强制落地）

* `AgentProfile`：agent_id、allow_tools、scope、templates、routing_hints
* `Decision`：need_tools、tool_candidates、missing_slots、risk_level
* `Plan`：steps[]（tool + args + expected_output + retry）
* `ToolResult`：status、data（structured）、summary、latency、error
* `DraftAnswer`：findings[]、evidence[]、caveats[]、actions[]
* `FinalAnswer`：面向用户输出（含引用/口径）

**Codex 要实现**：所有 LLM 输出必须满足 JSON Schema；执行器做校验，不通过则自动重试一次（同模型或降级模板）。

### 3.2 统一编排状态机（建议实现为可配置 DAG）

默认链路（2-call）：

* Node A：`route_and_plan(profile, user_input, context)` → Plan(JSON)
* Node B：`execute_plan(plan)` → tool_results[]
* Node C：`synthesize(profile, user_input, tool_results, context)` → FinalAnswer

升级链路（3~4-call）触发条件：

* 多工具多步（>2 steps）
* 高风险写操作（todo_upsert 等）
* 数据异常（空/冲突/超时）
* 用户要求“严谨引用/格式化报告”

### 3.3 工具契约（Tool Contract）必须具备

* `name/description`
* `input_schema`（类型、必填、范围、枚举）
* `output_schema`（结构化字段）
* `auth_scope`（只读/可写；数据域）
* `rate_limit/cost_hint`
* `safety_filter`（脱敏字段列表）

> **特别强调**：DB 工具采用“只读 SELECT + 参数化 + LIMIT + 白名单表字段 + 超时”策略；写操作必须由业务层二次确认或策略审批。

### 3.4 结果净化与提示注入防护（必须在执行器层做）

* **脱敏**：学号、手机号、邮箱、身份证等
* **截断**：结果超过阈值则先做统计摘要 + sample rows
* **指令剥离**：工具输出仅作为“数据”，禁止被模型当成“指令”

---

## 4. 响应速度与成本：分层模型策略（强烈建议）

### 4.1 关键原则：小模型做路由，大模型做生成；复杂任务按需升级

建议在平台内部定义 3 个“模型档位”（不绑定具体厂商，便于替换）：

* **Tier-1 Router**：便宜、快、结构化输出稳定（用于 LLM#1）
* **Tier-2 General**：综合能力强（用于 LLM#2 默认）
* **Tier-3 Reasoner**：高推理、长上下文（仅在复杂/高价值任务启用）

### 4.2 缓存策略（显著降本提速）

* **模型列表/工具元数据缓存**：启动加载，定时刷新
* **案例库/课程库检索缓存**：query+filters 维度短 TTL（如 5~30 分钟）
* **学生进度/达成数据**：按 student_id 设 TTL（如 1~5 分钟）
* **LLM 结果缓存**：仅对“事实性/稳定模板输出”启用；探究型不建议缓存

### 4.3 “两次 LLM 调用”下的 token 控制

* LLM#1 只给必要上下文（Profile 摘要 + 用户输入 + 关键约束），不塞工具原始数据
* 工具结果先结构化摘要（summary + stats + sample），再喂给 LLM#2
* 长文档统一走 RAG，禁止全文塞 prompt

---

## 5. 六个智能体的默认路由与工具调用策略（可直接落地为规则 + LLM 混合）

为降低 Router 成本，可做“规则优先，LLM 兜底”：

### 5.1 规则优先示例

* 任务型：若包含“待办/截止/进度/完成了吗/提醒我” → 直接进入 Task Profile
* 课程型：若包含“选修/推荐课/适合我/学期安排/难度” → Course Profile
* 评价型：若包含“达成/指标点/毕业要求/改进建议/评价” → Assessment Profile
* 竞赛型：若包含“竞赛/比赛/备赛/获奖/队伍/指导” → Contest Profile
* 思政型：若包含“思政/案例/船魂精神/大国智造/校史/行业特色” → Ideology Profile
* 探究型：若包含“为什么/如何证明/你怎么看/深入分析/反例” → Inquiry Profile

### 5.2 LLM Router 兜底

当规则不命中或多意图冲突时，再调用 Tier-1 Router 输出：

* agent_id
* need_tools
* tool_candidates
* missing_slots（需要追问的信息）

---

## 6. 评测与可维护性：必须提前设计的工程机制

### 6.1 关键指标（每个 Agent 都要定义 KPI）

* **Tool Accuracy**：工具选择正确率、参数正确率
* **Answer Groundedness**：回答是否基于工具证据（可用 evidence id 检查）
* **Latency**：P50/P95 响应时间（拆分 LLM 与工具耗时）
* **Cost**：每请求 token、每功能成本
* **User Success**：任务完成率（任务型尤为关键）

### 6.2 回放机制（Debug 必备）

保存每次请求的：

* user_input（脱敏）
* profile 版本
* plan JSON
* tool_results 摘要
* final answer
  用于：回归测试、线上问题定位、Prompt 迭代对比。

---

## 7. 迭代路线：先跑通“可用闭环”，再增强能力

### 7.1 MVP（2~4 周内可落地）

* 统一 Orchestrator（2-call）
* 工具：案例检索、学生进度读写、课程库检索、竞赛库检索、达成数据读取
* Agent Profile：六个 Profile 最小配置
* 日志与回放：必须上线

### 7.2 V2（增强可靠性与体验）

* 多步计划与回退（Planner 支持 2~4 step）
* 写操作审批（任务型待办更新、评价型生成改进计划入库）
* 引用与证据（思政/评价/竞赛类输出带 evidence）
* 轻量 Guard（规则/敏感词/越权）

### 7.3 V3（深度个性化与智能优化）

* 学生画像完善（偏好、负担、能力曲线）
* 推荐系统与 LLM 协同（课程/竞赛更有效）
* 探究型引导策略库（不同学段/能力档的 Socratic 模板）

---

## 8. 给 Codex 的具体实施清单（建议按顺序执行）

1. 建立 `agents/` 目录：6 个 `profile.yaml`（工具白名单、模板、路由提示）
2. 建立 `tools/`：统一 Tool Registry（schema、auth_scope、rate_limit）
3. 实现 `orchestrator/graph.py`：2-call 默认链路 + 升级链路触发器
4. 实现 `executor/`：参数校验、脱敏、截断、错误分类、重试
5. 实现 `schemas/`：Decision/Plan/ToolResult/DraftAnswer 的 JSON Schema
6. 实现 `eval/`：离线回放器 + 基准用例（每 Agent 20~50 条）
7. 实现 `observability/`：日志、trace_id、耗时分解、token 计数、成本统计

---

## 9. 默认策略建议（便于你直接定“平衡点”）

* 默认每次请求：**2 次 LLM**（Router/Plan + Responder）
* 默认工具步数：≤2（超过则升级链路）
* 探究型：默认不调用工具；只有当需要“概念/例题/数据”时才调用
* 写操作：默认需要“明确意图 + scope 校验 + 低风险”才执行；否则转为建议而不写入

---

如果你希望我把这份备忘录进一步“可直接贴进仓库执行”，我可以在下一条消息中输出：

* 6 份 `profile.yaml` 的建议内容（含 tool allowlist 与输出模板）
* `Plan/Decision` 的 JSON Schema（可直接用于校验）
* 一套 Router 提示词与 Responder 提示词（可换模型、可版本化）
* 任务型/课程型/评价型各 10 条离线评测用例（便于你做回归）
