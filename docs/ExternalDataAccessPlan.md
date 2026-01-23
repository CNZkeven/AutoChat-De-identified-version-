以下为“方案 A（Autochat 侧建立教育数据读库 Data Mart + 定时/增量同步 Achieve）”的**面向 Codex 的技术备忘录**。内容按“可直接在你的 React + FastAPI + Postgres 代码库中执行”的方式组织，包含任务拆解、目录与文件建议、DDL、同步作业、权限控制（RLS）、审计与验收标准。

---

## 技术备忘录：Achieve → Autochat 教育数据读库（Data Mart）同步方案（方案 A）

### 0. 背景与目标

**目标**：将 Achieve 中与学生个体与课程/教学班层面相关的数据（课程清单、大纲、教学班成绩分布、均分、课程目标达成度、学生个人成绩等）同步到 Autochat 的本地 Postgres 中，供 Autochat 的 6 个智能体统一、安全、高性能读取。
**约束**：非强实时；大纲/课程信息低频变更；成绩与达成度增量低频（学期末为主）；需要严格的学生数据隔离。

---

## 1. 总体架构与原则

### 1.1 架构

* **Achieve**：主数据源（SoR）。仅提供只读数据库连接（优先）或只读视图（view/schema）。
* **Autochat**：新增 Postgres schema：`dm`（data mart 读模型）与 `ops`（同步/审计/运行日志）。
* **同步方式**：Autochat 侧周期性任务（ETL/ELT）从 Achieve 抽取 → 落地到 `staging` → merge/upsert 到 `dm` → 生成聚合表 → 更新同步水位。

### 1.2 关键原则

1. **最小可用域**先落地（MVP），再扩展字段与表。
2. **数据隔离**优先：用 Postgres Row Level Security（RLS）+ 服务层二次校验。
3. **口径统一**：聚合统计（成绩分布、均分、达成度汇总）在 Autochat 侧生成，保证智能体读到的口径一致。
4. **可追溯**：同步作业必须有水位（watermark）、运行日志、行数统计与错误记录。
5. **可回滚**：同步过程 staging 与 dm 分离；dm 更新采用事务；避免半成品数据对外可见。

### 1.3 当前实现约定（Autochat）

- dm 表采用复数命名：`dm.students`、`dm.courses`、`dm.course_offerings`、`dm.enrollments`、`dm.student_scores`、`dm.section_grade_summary`。
- 达成度相关表：`dm.course_objectives`、`dm.student_objective_achievements`、`dm.section_objective_summary`。
- 同步入口脚本：`scripts/sync_dm.py`；管理员触发：`POST /api/admin/dm-sync`。

### 1.4 六类智能体数据域映射（本地表）

- 思政型：`knowledge` / `knowledge_embeddings`（内部思政案例库）
- 任务型：`user_profiles`（执行习惯占位），后续扩展 `agent_task_*` 表
- 竞赛型：`knowledge`（竞赛案例占位），后续扩展 `competition_*` 表
- 课程型：`dm.programs`、`dm.program_versions`、`dm.program_version_courses`、`dm.courses`、`dm.syllabus_versions`
- 评价型：`dm.student_scores`、`dm.student_objective_achievements`、`dm.section_grade_summary`、`dm.section_objective_summary`
- 探究型：`knowledge`（概念库/案例库）

---

## 2. 计划与里程碑（建议 3 个迭代）

> Codex 需按迭代逐步提交 PR，每个迭代可独立部署上线。

### Iteration 1（MVP：2–3 天工作量的规模）

**范围**：

* 课程清单（course）
* 教学班（section）
* 选课关系（enrollment）
* 学生成绩（student_score：总评/等级/关键字段）
* 教学班成绩聚合（section_grade_summary：均分/分布基础版）
* 同步作业框架（staging + upsert + watermark + job log）
* 基础 RLS（学生只能读自己的成绩 + 自己选课的教学班汇总）

**验收**：

* 指定学生登录后只能读到本人 `student_score`。
* 指定学生只能读到其已选课教学班的 `section_grade_summary`。
* 同步作业可重复运行，幂等，不重复插入/不丢失更新。

### Iteration 2（达成度与大纲）

**范围**：

* 大纲（syllabus 版本化）
* 课程目标（course_outcome）
* 学生课程目标达成度（student_co_attainment）
* 教学班课程目标汇总（section_co_summary）

**验收**：

* 学生可读到本人课程目标达成度（仅其选课范围）。
* 大纲按版本号可追溯；变更触发更新而非盲目覆盖。

### Iteration 3（增强与治理）

**范围**：

* 字段脱敏策略、访问审计完善（who/when/what）
* 性能优化：索引、分区（按学期 term）、物化视图（可选）
* 管理员控制台（可选）：查看同步状态、手动触发同步、查看差异统计

---

## 3. 代码库改造清单（Codex 执行项）

### 3.1 新增目录与模块建议

在 FastAPI 项目中新增：

* `app/dm/`：data mart 读 API（给智能体或后端服务内部使用）
* `app/sync/`：同步作业代码（extract/load/transform）
* `app/db/migrations/`：Alembic migrations（或你现用迁移方案）
* `app/security/rls.py`：RLS session 变量设置与连接封装
* `app/ops/`：同步日志/审计查询

新增 CLI：

* `scripts/sync_dm.py`：可由 crontab/systemd/容器定时触发的同步入口
* 或使用 FastAPI background job + APScheduler（建议先 CLI + cron，更简单可靠）

### 3.2 配置项（环境变量）

在 Autochat `.env` 增加：

* `ACHIEVE_DB_DSN=postgresql://readonly:***@host:5432/achieve`
* `AUTOCHAT_DB_DSN=postgresql://.../autochat`
* `SYNC_TERM_WINDOW=2025FA,2026SP`（可选：限制同步学期窗口）
* `SYNC_BATCH_SIZE=5000`
* `SYNC_SCHEDULE_CRON=0 3 * * *`（每日 3:00）

---

## 4. 数据模型（DDL 草案，Codex 需用迁移实现）

> 说明：表名/字段需根据 Achieve 实际字段映射调整；此处给出推荐读库结构与最小字段集合。
> 约定：`term` 用字符串（如 `2025FA`），`student_id` 建议用 Achieve 的内部主键或学号，但要一致且稳定。

### 4.1 Schema

* `stg`：staging 落地（可选；也可用临时表）
* `dm`：data mart 读模型
* `ops`：运行日志/水位/审计

### 4.2 `ops`：水位与日志

```sql
CREATE SCHEMA IF NOT EXISTS ops;

CREATE TABLE IF NOT EXISTS ops.sync_watermark (
  source_name      text NOT NULL,          -- e.g. 'achieve'
  entity_name      text NOT NULL,          -- e.g. 'student_score'
  last_updated_at  timestamptz,            -- watermark by updated_at
  last_pk          text,                   -- optional fallback
  updated_at       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (source_name, entity_name)
);

CREATE TABLE IF NOT EXISTS ops.sync_job_log (
  job_id           uuid PRIMARY KEY,
  job_name         text NOT NULL,          -- e.g. 'dm_sync_daily'
  started_at       timestamptz NOT NULL,
  finished_at      timestamptz,
  status           text NOT NULL,          -- 'RUNNING'|'SUCCESS'|'FAILED'
  detail           jsonb NOT NULL DEFAULT '{}'::jsonb
);
```

### 4.3 `dm`：MVP 表

```sql
CREATE SCHEMA IF NOT EXISTS dm;

CREATE TABLE IF NOT EXISTS dm.course (
  course_id     text PRIMARY KEY,
  course_name   text NOT NULL,
  credits       numeric(4,1),
  dept_name     text,
  updated_at    timestamptz
);

CREATE TABLE IF NOT EXISTS dm.section (
  section_id    text PRIMARY KEY,
  term          text NOT NULL,
  course_id     text NOT NULL REFERENCES dm.course(course_id),
  section_name  text,
  teacher_name  text,
  updated_at    timestamptz
);

CREATE TABLE IF NOT EXISTS dm.enrollment (
  term          text NOT NULL,
  section_id    text NOT NULL REFERENCES dm.section(section_id),
  student_id    text NOT NULL,
  enrolled_at   timestamptz,
  updated_at    timestamptz,
  PRIMARY KEY (term, section_id, student_id)
);

CREATE TABLE IF NOT EXISTS dm.student_score (
  term          text NOT NULL,
  section_id    text NOT NULL REFERENCES dm.section(section_id),
  student_id    text NOT NULL,
  total_score   numeric(5,2),
  grade_level   text,            -- e.g. 优良中及格 / A/B/C...
  updated_at    timestamptz,
  PRIMARY KEY (term, section_id, student_id)
);

-- 教学班聚合：均分、人数、分布（先基础版）
CREATE TABLE IF NOT EXISTS dm.section_grade_summary (
  term          text NOT NULL,
  section_id    text NOT NULL REFERENCES dm.section(section_id),
  n_students    int NOT NULL,
  avg_score     numeric(5,2),
  min_score     numeric(5,2),
  max_score     numeric(5,2),
  dist_json     jsonb NOT NULL DEFAULT '{}'::jsonb,  -- { "90-100": 12, ... }
  computed_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (term, section_id)
);
```

### 4.4 索引建议（Iteration 1）

```sql
CREATE INDEX IF NOT EXISTS idx_enrollment_student ON dm.enrollment(student_id, term);
CREATE INDEX IF NOT EXISTS idx_score_student ON dm.student_score(student_id, term);
CREATE INDEX IF NOT EXISTS idx_score_section ON dm.student_score(section_id, term);
```

---

## 5. 权限与隔离（RLS + 应用层）

### 5.1 应用侧：为每个请求设置 session 变量

Autochat 后端在打开 DB 连接后执行：

* `SET LOCAL app.student_id = '<current_student_id>';`
* 对管理员/教师服务账号可设置 `SET LOCAL app.role = 'admin'` 等

### 5.2 数据库侧：启用 RLS（MVP）

```sql
ALTER TABLE dm.student_score ENABLE ROW LEVEL SECURITY;
ALTER TABLE dm.enrollment ENABLE ROW LEVEL SECURITY;
ALTER TABLE dm.section_grade_summary ENABLE ROW LEVEL SECURITY;

-- 学生：只能看自己成绩
CREATE POLICY p_student_score_self
ON dm.student_score
FOR SELECT
USING (student_id = current_setting('app.student_id', true));

-- 学生：只能看自己的选课记录
CREATE POLICY p_enrollment_self
ON dm.enrollment
FOR SELECT
USING (student_id = current_setting('app.student_id', true));

-- 学生：只能看自己选课教学班的聚合数据
CREATE POLICY p_section_summary_enrolled
ON dm.section_grade_summary
FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM dm.enrollment e
    WHERE e.term = dm.section_grade_summary.term
      AND e.section_id = dm.section_grade_summary.section_id
      AND e.student_id = current_setting('app.student_id', true)
  )
);
```

> Codex 注意：RLS 会影响后台同步作业写入。同步作业的 DB 连接需使用 **专用服务账号**（dm_writer），并对该账号授予 `BYPASSRLS` 或用 `ALTER ROLE dm_writer BYPASSRLS;`（更推荐 BYPASSRLS），避免同步失败。

---

## 6. 同步作业设计（Codex 需实现）

### 6.1 同步作业步骤（每个 entity 通用）

1. **读取 watermark**（`ops.sync_watermark`）
2. **从 Achieve 抽取**：`WHERE updated_at > :watermark`（或按 term 窗口）
3. **落到 staging**：`stg.entity_*`（或直接在内存批处理后 upsert）
4. **Upsert 到 dm**：`INSERT ... ON CONFLICT ... DO UPDATE`
5. **更新 watermark**（最大 updated_at）
6. **重算聚合表**（本次受影响的 section 集合）
7. **写 job log**（行数、耗时、受影响 section 数、错误）

### 6.2 需要 Codex 实现的 Python 模块（建议）

* `app/sync/base.py`

  * DB 连接（achieve/autochat）
  * watermark 读写
  * 批量抽取、批量 upsert 工具函数
* `app/sync/entities/*.py`

  * `sync_course()`
  * `sync_section()`
  * `sync_enrollment()`
  * `sync_student_score()`
* `app/sync/aggregations.py`

  * `recompute_section_grade_summary(terms, section_ids)`

### 6.3 Upsert SQL 示例（student_score）

```sql
INSERT INTO dm.student_score(term, section_id, student_id, total_score, grade_level, updated_at)
VALUES (:term, :section_id, :student_id, :total_score, :grade_level, :updated_at)
ON CONFLICT (term, section_id, student_id)
DO UPDATE SET
  total_score = EXCLUDED.total_score,
  grade_level = EXCLUDED.grade_level,
  updated_at  = EXCLUDED.updated_at
WHERE dm.student_score.updated_at IS DISTINCT FROM EXCLUDED.updated_at;
```

### 6.4 聚合重算（基础版：分箱统计）

* 分箱建议：`0-59`, `60-69`, `70-79`, `80-89`, `90-100`
* 对每个受影响教学班（term, section_id）计算：

  * `n_students, avg, min, max`
  * `dist_json`：各分箱人数

SQL 思路（可在 Python 侧组装 dist_json 或用 SQL CASE 聚合）：

```sql
WITH s AS (
  SELECT term, section_id, total_score
  FROM dm.student_score
  WHERE term = :term AND section_id = :section_id AND total_score IS NOT NULL
),
agg AS (
  SELECT
    term, section_id,
    COUNT(*)::int AS n_students,
    AVG(total_score)::numeric(5,2) AS avg_score,
    MIN(total_score)::numeric(5,2) AS min_score,
    MAX(total_score)::numeric(5,2) AS max_score,
    jsonb_build_object(
      '0-59',  SUM(CASE WHEN total_score < 60 THEN 1 ELSE 0 END),
      '60-69', SUM(CASE WHEN total_score >=60 AND total_score < 70 THEN 1 ELSE 0 END),
      '70-79', SUM(CASE WHEN total_score >=70 AND total_score < 80 THEN 1 ELSE 0 END),
      '80-89', SUM(CASE WHEN total_score >=80 AND total_score < 90 THEN 1 ELSE 0 END),
      '90-100',SUM(CASE WHEN total_score >=90 THEN 1 ELSE 0 END)
    ) AS dist_json
  FROM s
  GROUP BY term, section_id
)
INSERT INTO dm.section_grade_summary(term, section_id, n_students, avg_score, min_score, max_score, dist_json, computed_at)
SELECT term, section_id, n_students, avg_score, min_score, max_score, dist_json, now()
FROM agg
ON CONFLICT (term, section_id)
DO UPDATE SET
  n_students = EXCLUDED.n_students,
  avg_score  = EXCLUDED.avg_score,
  min_score  = EXCLUDED.min_score,
  max_score  = EXCLUDED.max_score,
  dist_json  = EXCLUDED.dist_json,
  computed_at= now();
```

---

## 7. API 与智能体接入（最小接口）

> 智能体不要直接拼复杂 SQL；统一走后端内部 API（或 DB view）。MVP 先做 3 个 endpoint。

* `GET /dm/me/scores?term=2025FA`
  返回本人各教学班总评成绩（与课程名称 join）
* `GET /dm/me/sections?term=2025FA`
  返回本人选课教学班列表（含 teacher、course_name）
* `GET /dm/me/sections/{section_id}/summary?term=2025FA`
  返回本人已选教学班的成绩分布与均分（RLS 兜底）

---

## 8. 运行与调度

### 8.1 定时触发（推荐：cron + CLI）

* 新增 `scripts/sync_dm.py`：

  * 参数：`--job dm_sync_daily --terms 2025FA,2026SP --entities course,section,enrollment,student_score`
  * 输出：标准日志 + 写入 `ops.sync_job_log`
* cron：每日 03:00
  期末周可调整到每小时一次（由管理员改 cron）

### 8.2 失败策略

* 同步作业任何 entity 失败：

  * 本次 job 标记 FAILED
  * 已写入的 dm 变更必须保证事务一致性（每个 entity 一个事务，或全局大事务视数据量而定）
  * 不更新 watermark（避免数据空洞）
* 支持重跑：同水位幂等 upsert

---

## 9. 安全与合规检查项（Codex 必须落实）

1. Achieve 连接账号必须只读；只允许访问抽取所需表/视图。
2. Autochat dm_writer 账号仅用于写 dm/ops/stg；对外 API 使用只读账号 dm_reader。
3. 学生身份映射：`autochat_user.student_id` 必须与 Achieve 的 `student_id` 一致（或建立映射表 `dm.student_identity_map`）。
4. 禁止学生访问“全课程/全教学班”汇总：默认限制为本人选课范围（已在 RLS 中实现）。
5. 审计：对 `/dm/*` 接口写访问日志（至少记录 user_id、student_id、endpoint、term、section_id、timestamp）。

---

## 10. 测试与验收（Codex 需提供自动化测试）

### 10.1 单元/集成测试

* 同步幂等：重复运行 `sync_student_score` 不产生重复行，更新能覆盖旧值。
* RLS 越权：A 学生 token 读取 B 学生成绩必须返回 0 行或 403。
* 聚合正确：给定固定输入成绩集合，`section_grade_summary` 分箱与均分正确。

### 10.2 端到端验收清单

* 选一个真实学生账号：

  * `/dm/me/scores` 返回与 Achieve 一致（允许延迟，但数值一致）
  * `/dm/me/sections/{id}/summary` 返回正确分布与均分
* 切换另一个学生：

  * 绝不能读到前一个学生的成绩行（RLS + session 变量生效）

---

## 11. Codex 具体执行指令（可直接复制给 Codex）

请 Codex 在你的代码库中完成以下工作并提交 PR（按 Iteration 1 优先）：

1. 新增数据库迁移：

   * 创建 schema：`ops`, `dm`
   * 创建表：`ops.sync_watermark`, `ops.sync_job_log`
   * 创建表：`dm.course`, `dm.section`, `dm.enrollment`, `dm.student_score`, `dm.section_grade_summary`
   * 创建索引：见第 4.4
   * 启用 RLS 并创建 policy：见第 5.2
2. 新增同步作业框架与 CLI：

   * `app/sync/base.py`（连接、watermark、批处理工具）
   * `app/sync/entities/course.py|section.py|enrollment.py|student_score.py`
   * `app/sync/aggregations.py`（重算 section_grade_summary）
   * `scripts/sync_dm.py`（命令行入口）
3. 新增最小读 API（FastAPI）：

   * `GET /dm/me/scores`
   * `GET /dm/me/sections`
   * `GET /dm/me/sections/{section_id}/summary`
   * 并在 DB 连接中设置 `SET LOCAL app.student_id = ...`
4. 新增测试：

   * RLS 越权测试（至少 1 条）
   * 同步幂等测试（至少 1 条）
   * 聚合分箱正确性测试（至少 1 条）
5. 新增文档：

   * `docs/dm_sync.md`：如何配置 DSN、如何运行一次同步、如何配置 cron、如何排错（查看 ops 表）

PR 中必须包含：

* 迁移脚本
* 同步代码
* API 与鉴权/设置 session 变量的实现
* 测试与文档

---

## 12. 需要你提供/确认的信息（但 Codex 可先按占位实现）

为避免与 Achieve 实际表结构不匹配，最终需要你给 Codex（或你自己）补齐以下映射信息：

* Achieve 中课程、教学班、选课、成绩表的真实表名与字段名
* 是否存在 `updated_at` 字段（若无，需要替代增量策略：按 term 全量或按导入批次号）
* student_id 在两个系统是否一致（不一致则要 identity_map）

> 如果你暂时不想补充这些信息，Codex 可以先把“抽取 SQL”写成可配置映射（YAML/JSON）+ 占位 SQL，迁移与框架先落地。

---

### 自检清单（交付前必须通过）

* 同步作业可执行、可重跑（幂等）
* RLS 生效，学生无法越权
* 聚合表可正确重算且有索引
* ops 表可追踪运行状态与水位
* 文档可指导管理员完成配置与运行
