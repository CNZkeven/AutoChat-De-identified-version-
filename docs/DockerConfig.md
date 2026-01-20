你是一个工程实施代理。请在我当前本地仓库中，实现“Docker Compose 一键起全栈（跨平台最稳）”方案，使 Mac 与 Windows 开发者都能用同一套命令启动 React + FastAPI + Postgres，并补齐可复现的开发文档与脚本。

### 0. 目标与验收标准（必须满足）

1. 新成员在仓库根目录执行以下步骤即可启动：

   * `cp .env.example .env`（Windows 也提供等价方式）
   * `docker compose up --build`
2. 启动后满足：

   * Postgres 可用并持久化（volume）
   * FastAPI 服务可访问（含健康检查端点）
   * React 开发服务可访问（支持热更新；如项目已有 Vite/CRA/Next，按现状处理）
3. 仓库新增/修改的所有文件需结构清晰，并在 README 中写清楚“首次启动”“日常开发”“常见故障（Windows 重点）”。
4. 不破坏现有本机开发方式（npm/uvicorn 直跑等），Docker 作为新增的标准协作入口。
5. 所有敏感信息不入库：只提供 `.env.example`，真实 `.env` 加入 `.gitignore`。

---

## 1. 先做仓库探测与现状梳理（先读后改）

请先自动扫描并记录以下信息（写入你生成的实施说明或注释中即可，不要输出到终端以外的地方也行）：

1. 仓库顶层目录结构：是否存在 `frontend-react/`、`backend/`、`apps/`、`api/`、`server/` 等。
2. 前端技术与启动命令：

   * `package.json` 中的 `scripts`（dev/build/test）
   * 使用 Vite / CRA / Next.js 之一或其他
   * 默认开发端口（常见 5173/3000）
3. 后端技术与启动命令：

   * 是否有 `pyproject.toml`/`requirements.txt`
   * 应用入口（`main.py`、`app/main.py` 等）
   * uvicorn 启动命令与端口（常见 8000）
4. 数据库接入方式：

   * 是否使用 SQLAlchemy / asyncpg
   * 是否有 Alembic migrations（`alembic.ini`、`migrations/`）
   * 当前 DB URL 环境变量名（例如 `DATABASE_URL`）

在此基础上再生成配置，避免硬编码错误路径或错误端口。

---

## 2. 生成/修改 Docker 相关文件（核心交付）

在仓库根目录落地以下文件（如已存在则按最佳实践改造）：

### 2.1 `docker-compose.yml`（或 `compose.yml`）

要求：

1. 定义至少 3 个服务：`db`（postgres）、`backend`（fastapi）、`frontend`（react）。
2. `db`：

   * 使用官方 `postgres` 镜像（选择稳定版本，例如 15 或 16；以项目兼容为准）
   * 暴露端口到宿主（默认 5432，可配置）
   * 使用命名 volume 持久化，例如 `pgdata:/var/lib/postgresql/data`
   * 设置 `POSTGRES_DB/USER/PASSWORD` 读取自 `.env`
   * 健康检查（`pg_isready`）
3. `backend`：

   * 通过 Dockerfile 构建（见下）
   * 以环境变量获取 DB 连接（优先使用 `DATABASE_URL`；如项目现用不同变量名，请兼容）
   * `depends_on` 要包含 `db` 且具备健康检查条件（Compose v2 语法允许时使用）
   * 暴露后端端口到宿主（默认 8000）
   * 挂载代码目录实现热更新（uvicorn `--reload`）
4. `frontend`：

   * 通过 Dockerfile 构建（见下）
   * 挂载前端源码目录以支持热更新
   * 暴露端口到宿主（Vite 5173 / CRA 3000，按项目实际）
   * 确保容器内 dev server 监听 `0.0.0.0`
5. 网络：

   * 使用默认网络即可；保证服务间能用服务名访问（`db`、`backend`）。
6. 兼容 Mac/Windows：

   * 避免依赖 host.docker.internal 的必需性
   * 尽量不使用仅 Linux 可用的路径/权限技巧

### 2.2 后端 `backend/Dockerfile`（路径按实际探测）

要求：

1. 选择合适 Python 基础镜像（例如 `python:3.11-slim`，以项目版本为准）
2. 分层缓存：先拷贝依赖文件（`pyproject.toml`/`poetry.lock` 或 `requirements.txt`）再安装依赖
3. 再拷贝源码
4. 默认启动命令使用 uvicorn（带 `--reload`，host=0.0.0.0，端口按配置）
5. 若项目使用 Poetry：

   * 在镜像内安装 poetry
   * 使用 `poetry install --no-interaction --no-ansi`
6. 若使用 requirements：

   * `pip install -r requirements.txt`
7. 生成一个简易健康检查端点（例如 `/health`），如项目已存在则复用；如没有，请在后端增加一个最小实现（不影响业务）。

### 2.3 前端 `frontend-react/Dockerfile`（路径按实际探测）

要求：

1. 选择 Node LTS（例如 `node:20-alpine` 或 `node:20-slim`）
2. 分层缓存：先拷贝 lock 文件（`package-lock.json`/`pnpm-lock.yaml`/`yarn.lock`）再安装
3. 再拷贝源码
4. 默认启动 dev server（`npm run dev` 或对应脚本）
5. 确保 dev server 监听 `0.0.0.0`，必要时为 Vite 添加 `--host 0.0.0.0` 或修改 `vite.config.*`

### 2.4 `.dockerignore`（根目录、前后端各自如果需要）

要求：

* 忽略 `node_modules/`、`dist/`、`build/`、`.venv/`、`__pycache__/`、`.pytest_cache/`、`.mypy_cache/`、`.git/` 等
* 降低构建上下文体积

---

## 3. 环境变量与忽略规则（必须交付）

### 3.1 `.env.example`

在根目录创建 `.env.example`，至少包含：

* `POSTGRES_DB=...`
* `POSTGRES_USER=...`
* `POSTGRES_PASSWORD=...`
* `POSTGRES_PORT=5432`（可选）
* `BACKEND_PORT=8000`
* `FRONTEND_PORT=5173`（或实际）
* `DATABASE_URL=postgresql://...`（按后端框架需要，若 async 使用 `postgresql+asyncpg://`）
* `VITE_API_BASE_URL=http://localhost:8000`（若前端需要；具体变量名按项目实际）

### 3.2 `.gitignore` 更新

确保 `.env`、`.env.*`（除 `.env.example`）不入库。

---

## 4. 数据库初始化/迁移（按项目情况选择最佳方案）

1. 如果仓库已有 Alembic：

   * 在 README 指导如何在容器内执行迁移（例如 `docker compose exec backend alembic upgrade head`）
   * 可选：在 backend 启动脚本中做“等待 db + 运行迁移”（谨慎，避免生产副作用；开发环境可行）
2. 如果没有迁移体系：

   * 至少提供一个最小初始化策略说明（例如手动建库/脚本）

---

## 5. 新增开发脚本（提升跨平台体验）

在根目录新增：

1. `scripts/dev.sh`（Mac/Linux）

   * 复制 env（若不存在）
   * `docker compose up --build`
2. `scripts/dev.ps1`（Windows PowerShell）

   * 等价行为
3. 在 README 中说明 Windows 使用 PowerShell 执行：`.\scripts\dev.ps1`

脚本需尽量幂等、可重复执行。

---

## 6. 文档（必须交付，写清楚 Windows 差异）

### 6.1 更新/创建 `README.md` 中的以下章节（如果已存在则补齐）

至少包含：

1. **项目概览**：React + FastAPI + Postgres
2. **快速开始（推荐：Docker）**

   * 前置：Docker Desktop 安装提示
   * `cp .env.example .env`（Windows 写 `Copy-Item .env.example .env` 或手动复制）
   * `docker compose up --build`
   * 访问地址（前端、后端、健康检查）
3. **日常开发**

   * 仅启动 db：`docker compose up -d db`
   * 重建某个服务：`docker compose build backend` 等
   * 查看日志：`docker compose logs -f backend`
4. **数据库迁移/初始化**

   * Alembic 的标准命令（如适用）
5. **常见问题（重点 Windows）**

   * 端口占用
   * 文件共享/性能（Docker Desktop）
   * 依赖安装差异（解释为什么用 Docker）
   * 换行符与脚本执行策略（PowerShell 执行策略提示：如需 `Set-ExecutionPolicy -Scope Process Bypass`，仅在 README 说明，不强制修改系统）

### 6.2 新增 `CONTRIBUTING.md`（可选但强烈建议）

简述：

* 分支策略
* PR 流程
* 本地启动统一用 Docker Compose
* 代码风格（若已有 lint/format 工具，写出命令）

---

## 7. 可选但建议：最小 CI 提示（不强制改 Actions）

如果仓库已有 GitHub Actions：

* 确认不会因新增文件而破坏现有流程
  如果没有 Actions：
* 不必创建完整 CI，但可在 README 给出建议（例如后端 pytest、前端 build/lint）

---

## 8. 实施输出要求（非常重要）

1. 所有新增/修改文件必须在最后以清单形式汇总：路径 + 目的。
2. 任何你做的“推断”（比如目录名、端口、环境变量名）都要基于仓库探测结果；如有不确定，选择最保守的兼容方式（例如同时支持 `DATABASE_URL` 和项目既有变量）。
3. 不要引入与项目无关的重型改造（例如强行更换包管理器）。
4. 若需要新增少量后端代码实现 `/health`，请以最小侵入方式实现，并写明文件路径与原因。

---

### 9. 最后请执行一次自检（在本地命令层面给出建议即可）

在你完成配置后，请提供一段“我应该如何验证”的命令列表，例如：

* `docker compose up --build`
* `curl http://localhost:8000/health`
* 打开前端地址并确认能请求后端 API（如有）

---

## 你可能需要 Codex 先问的问题（但尽量通过探测解决）

如果仓库结构或端口等确实无法从文件中判断，请在改动前向我提出最少量澄清问题；否则直接按探测结果实施。

---

