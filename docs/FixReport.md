# 修复记录

## 背景
- 问题：在 admin debug 调用课程型智能体查询“自动化专业有哪些专业选修课？”时返回 500，浏览器侧表现为 CORS 报错。
- 目标：定位并修复后端异常，同时记录修复路径，避免重复走弯路。

## 修复 1：前端端口与 CORS 对齐
- 现象：浏览器从 `http://localhost:5174` 发起请求时缺少 CORS 响应头。
- 变更：
  - `backend/.env` 与 `backend/.env.example`：将 `CORS_ORIGINS` 指向 5174。
  - `scripts/start.sh`：前端端口固定为 5174，并在占用时清理进程。
- 结论：前后端端口一致，CORS 允许本地访问。

## 修复 2：会话上下文 SQL 语法错误
- 现象：执行 `SET LOCAL app.student_no = :student_no` 时 psycopg 报语法错误。
- 变更：
  - `backend/app/services/tool_executor.py`
  - `backend/app/routers/dm.py`
  - `backend/app/sync/runner.py`
  - 统一改为 `SELECT set_config(..., true)` 设置 session 变量。
- 结论：会话上下文设置恢复正常。

## 修复 3：课程检索关键词参数类型错误（本次修复）
- 现象：使用 `:kw IS NULL OR ... ILIKE :kw` 时出现 “could not determine data type of parameter $2”。
- 失败尝试：使用 `:kw::text`，SQLAlchemy 绑定失败（语法错误）。
- 最终修复：
  - `backend/app/services/tool_executor.py`：对 `:kw` 显式使用 `bindparam(type_=String)`。
- 结论：debug run 返回 200，课程查询正常输出。
