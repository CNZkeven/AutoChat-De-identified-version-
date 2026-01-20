# AutoChat

## 项目简介（给非计算机同学看的版本）
AutoChat 是一个“对话式智能体系统”。你可以在网页里和不同类型的智能体聊天，
例如：思政、任务、探究、竞赛、课程、评价等。系统会保存聊天记录，方便回看和评估。

## 系统都包含什么
- **前端网页**：你在浏览器里看到的聊天界面。
- **后端服务**：负责处理登录、对话、保存记录。
- **数据库**：保存账号、对话和运行记录。

## 一键启动（推荐：Docker）
> 适合团队协作，不需要你本机安装数据库。

1. 安装 Docker Desktop。
2. 在项目根目录创建 `.env` 文件：
   - macOS / Linux：`cp .env.example .env`
   - Windows PowerShell：`Copy-Item .env.example .env`
3. 启动：
   - macOS / Linux：`./scripts/start.sh`
   - Windows PowerShell：`\scripts\dev.ps1`
   - 也可以直接用：`docker compose up --build`

启动成功后访问：
- 前端：http://localhost:5173
- 后端：http://localhost:8000
- 健康检查：http://localhost:8000/health
- 数据库：默认 5433（脚本会在 5433-5499 内自动找可用端口）

**端口自动选择记录在：** `.logs/compose-ports.env`

## 如何停止
- `./scripts/stop.sh`
- 或 `docker compose down`

## 常见问题（简明版）
1. **页面打不开**：先确认 Docker Desktop 是否正在运行。
2. **端口被占用**：脚本会自动换端口；如仍失败，请关闭占用端口的程序后重试。
3. **Windows 无法执行脚本**：在 PowerShell 里运行：
   `Set-ExecutionPolicy -Scope Process Bypass`，然后再执行 `\scripts\dev.ps1`。

## 不使用 Docker 的情况
目前推荐统一使用 Docker；如需本机直跑，请自行配置 `backend/.env` 与依赖环境。

## 开发者脚本
- macOS / Linux：`./scripts/dev.sh`
- Windows PowerShell：`\scripts\dev.ps1`

## 代码检查与构建
- `./scripts/lint.sh`
- `./scripts/build.sh`
