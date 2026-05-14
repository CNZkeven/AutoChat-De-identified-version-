# AutoChat — 基于大模型的 AI 教育智能体平台

> **2025 年国家级大学生创新创业训练计划项目**
> 项目名称：**"基于大模型的AI教育智能体开发"**


<img width="1578" height="607" alt="QQ_1778727591095" src="https://github.com/user-attachments/assets/82d970cc-17c8-4942-ba55-bea4897b91cf" />


> 本仓库为项目**脱敏版本**，已移除所有 API 密钥、数据库凭证、内部服务器地址及学生个人信息。
> 如需完整运行，请自行配置大模型 API 密钥及相关服务。

---

## 项目简介

AutoChat 是一套面向高等教育场景的**多智能体对话系统**。系统围绕"AI + 教育"核心理念，构建了六个专业化教育智能体，覆盖思政教育、学业评价、任务规划、探究学习、竞赛辅导和课程学习六大教育场景，为学生提供个性化、沉浸式的 AI 辅学体验。

### 核心创新点

| 创新维度 | 说明 |
|---------|------|
| **多智能体协同架构** | 六大专业智能体各司其职，通过智能路由自动匹配用户意图，实现"千人千面"的教育服务 |
| **规则 + LLM 双层路由** | 关键词规则匹配保障响应速度，大模型语义路由兜底复杂意图，兼顾效率与准确率 |
| **长期记忆系统** | 基于对话摘要的长期记忆机制，智能体可跨会话"记住"学生特征与学习偏好 |
| **工具增强生成（TAG）** | 每个智能体配备专属工具集（用户画像查询、知识库检索、学业数据查询、策略引擎等），实现"工具增强"而非单纯的 RAG |
| **双层用户画像** | 系统侧画像（学业数据驱动）+ 公开侧画像（对话行为驱动），双向构建学生数字孪生 |
| **多风格对话模式** | 每个智能体支持 2-3 种对话风格（如"规范阐释 / 启发共情"、"量化评估 / 成长反馈"），适配不同教学场景 |
| **学业数据深度融合** | 与教务系统对接，自动同步课程成绩、达成度指标、毕业要求等数据，为评价与推荐提供数据支撑 |

---

## 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.11+ | 主语言 |
| **FastAPI** | 0.115 | Web 框架，提供 RESTful API |
| **SQLAlchemy** | 2.0 | ORM，数据模型定义与查询 |
| **PostgreSQL** | 16 | 主数据库，存储用户、对话、学业数据 |
| **Redis** | 5.0 | 缓存层，工具注册表缓存、会话状态 |
| **OpenAI SDK** | 1.3+ | 大模型调用（兼容 SiliconFlow 等第三方 API） |
| **Passlib + bcrypt** | — | 密码哈希与安全认证 |
| **python-jose** | — | JWT 令牌签发与验证 |
| **Uvicorn** | 0.30 | ASGI 服务器 |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | 19.2 | UI 框架 |
| **TypeScript** | 5.9 | 类型安全 |
| **Vite** | 7.2 | 构建工具，HMR 开发体验 |
| **Tailwind CSS** | 3.4 | 原子化样式 |
| **Zustand** | 5.0 | 轻量级状态管理 |
| **React Query** | 5.90 | 异步数据请求与缓存 |
| **Framer Motion** | 12.x | 动画与过渡效果 |
| **React Markdown** | 10.x | Markdown 渲染（支持 KaTeX 数学公式） |
| **Lucide React** | — | 图标库 |

### AI / 大模型

| 组件 | 说明 |
|------|------|
| **大语言模型** | 通义千问 Qwen 系列（通过 SiliconFlow API 调用，兼容 OpenAI 协议） |
| **模型选型** | Qwen3-Omni-30B-A3B-Instruct（通用对话）、Qwen3-Next-80B-A3B-Instruct（记忆摘要） |
| **Fine-tuning 支持** | 预留 LoRA 微调模型接入（注释中的 ft:LoRA 配置） |

### 基础设施

| 技术 | 用途 |
|------|------|
| **Docker + Docker Compose** | 容器化部署，一键启动 |
| **GitHub Actions** | CI/CD 流水线 |
| **Ruff** | Python 代码格式化与静态检查 |
| **ESLint** | TypeScript/React 代码检查 |
| **Vitest** | 前端单元测试 |

---

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (React + Vite)                    │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
│  │ 思政 │ │ 评价 │ │ 任务 │ │ 探究 │ │ 竞赛 │ │ 课程 │ │
│  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ │
│     └────────┴────────┴────┬───┴────────┴────────┘      │
│                            │ REST API                    │
└────────────────────────────┼────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────┐
│                    后端 (FastAPI)                         │
│  ┌─────────────────────────┴──────────────────────────┐ │
│  │              智能路由器 (Router)                      │ │
│  │         规则匹配 → LLM 语义路由 → Agent 选择          │ │
│  └─────────────────────────┬──────────────────────────┘ │
│                            │                             │
│  ┌──────┐ ┌──────┐ ┌──────┤ ┌──────┐ ┌──────┐ ┌──────┐│
│  │ 思政 │ │ 评价 │ │ 任务 │ │ 探究 │ │ 竞赛 │ │ 课程 ││
│  │Agent │ │Agent │ │Agent │ │Agent │ │Agent │ │Agent ││
│  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘│
│     └────────┴────────┴───┬────┴────────┴────────┘     │
│                           │                              │
│  ┌────────────────────────┴───────────────────────────┐ │
│  │              工具执行引擎 (Tool Executor)             │ │
│  │  · 用户画像查询    · 知识库检索 (RAG)                 │ │
│  │  · 学业数据查询    · 策略引擎                         │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  长期记忆系统  │  │  用户画像引擎  │  │  学业报告生成  │  │
│  │  (Memory)     │  │  (Profile)    │  │  (Report)     │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
└──────────────────────────┬───────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────┴────┐     ┌──────┴──────┐   ┌──────┴──────┐
    │PostgreSQL│     │    Redis    │   │  大模型 API  │
    │   16    │     │    5.x     │   │ (SiliconFlow)│
    └─────────┘     └─────────────┘   └─────────────┘
```

---

## 六大教育智能体

| 智能体 | 定位 | 专属工具 | 对话风格 |
|--------|------|---------|---------|
| 🔴 **思政智能体** | 思想政治教育引导 | 用户画像、知识库检索 | 规范阐释 / 启发共情 |
| 🔵 **评价智能体** | 学习效果评估与反馈 | 用户画像、学业数据、达成度查询、策略引擎 | 量化评估 / 成长反馈 |
| 🟢 **任务智能体** | 学习任务规划与管理 | 用户画像、达成度查询、策略引擎 | 执行清单 / 策略优化 |
| 🟡 **探究智能体** | 探究式学习引导 | 知识库检索、用户画像 | 研究路线 / 灵感拓展 |
| 🟣 **竞赛智能体** | 学科竞赛备赛辅导 | 用户画像、达成度查询、知识库检索、策略引擎 | 高压训练 / 赛题解析 |
| 🩷 **课程智能体** | 课程学习辅导 | 用户画像、达成度查询、知识库检索 | 体系梳理 / 通俗讲解 |

---

## 项目结构

```
autochat/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── main.py             # FastAPI 入口
│   │   ├── config.py           # 配置管理（环境变量）
│   │   ├── models.py           # SQLAlchemy 数据模型
│   │   ├── schemas.py          # Pydantic 请求/响应模型
│   │   ├── security.py         # JWT 认证与密码哈希
│   │   ├── routers/            # API 路由（auth/chat/admin/...）
│   │   ├── services/           # 核心业务逻辑
│   │   │   ├── orchestrator.py # 多智能体编排引擎
│   │   │   ├── agent_router.py # 智能路由（规则+LLM）
│   │   │   ├── agent_profiles.py # 智能体配置档案
│   │   │   ├── agent_prompts.py  # 智能体提示词
│   │   │   ├── ai.py           # 大模型调用封装
│   │   │   ├── memory.py       # 长期记忆系统
│   │   │   ├── user_profiles.py # 用户画像引擎
│   │   │   ├── user_reports.py  # 学业报告生成
│   │   │   ├── tool_registry.py # 工具注册中心
│   │   │   ├── tool_executor.py # 工具执行引擎
│   │   │   ├── cache.py        # Redis 缓存层
│   │   │   └── academics.py    # 学业数据服务
│   │   └── sync/               # 教务数据同步
│   ├── requirements.txt
│   └── Dockerfile
├── frontend-react/             # 前端应用
│   ├── src/
│   │   ├── components/         # React 组件
│   │   ├── hooks/              # 自定义 Hooks
│   │   ├── store/              # Zustand 状态管理
│   │   ├── utils/              # 工具函数与常量
│   │   └── types/              # TypeScript 类型定义
│   ├── package.json
│   └── Dockerfile
├── scripts/                    # 运维与初始化脚本
├── docs/                       # 项目文档
├── docker-compose.yml          # 容器编排
└── .env.example                # 环境变量模板
```

---

## 快速开始

### 环境要求

- **Docker Desktop**（推荐，一键启动所有服务）
- 或本地环境：Python 3.11+、Node.js 20+、PostgreSQL 16、Redis 5+

### 一键启动（Docker）

```bash
# 1. 克隆仓库
git clone <repo-url>
cd autochat

# 2. 创建环境配置
cp .env.example .env
# 编辑 .env，填入你的大模型 API Key 和数据库密码

# 3. 启动
docker compose up --build
```

启动后访问：
- 前端：http://localhost:5174
- 后端 API：http://localhost:8000
- 健康检查：http://localhost:8000/health

### 环境变量配置

在 `.env` 文件中需要配置以下关键项：

```bash
# 数据库
POSTGRES_PASSWORD=<your-password>
DATABASE_URL=postgresql+psycopg://autochat:<your-password>@db:5432/autochat

# JWT 认证
JWT_SECRET_KEY=<random-secret-string>

# 大模型 API（以 SiliconFlow 为例）
IDEOLOGICAL_API_KEY=<your-api-key>
IDEOLOGICAL_BASE_URL=https://api.siliconflow.cn/v1
IDEOLOGICAL_MODEL=Qwen/Qwen3-Omni-30B-A3B-Instruct
# ... 其他智能体同理
```

> **安全提示**：请勿将 `.env` 文件提交到 Git 仓库。`.env.example` 仅作为模板参考。

---

## 开发指南

### 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend-react
npm install
npm run dev
```

### 代码检查与测试

```bash
# Python 代码检查
ruff check backend/

# 前端代码检查
npm --prefix frontend-react run lint

# 前端测试
npm --prefix frontend-react run test

# 前端构建
npm --prefix frontend-react run build
```

---

## 关键特性详解

### 智能路由机制

系统采用**双层路由策略**：

1. **规则匹配层**：基于关键词快速匹配（如"课程"→课程智能体、"竞赛"→竞赛智能体），响应延迟极低
2. **LLM 语义路由层**：当规则匹配不确定时，调用大模型进行语义理解，输出 JSON 格式的路由决策

### 长期记忆系统

- 每 20 条新消息自动触发记忆摘要生成
- 按用户 × 智能体维度独立存储记忆
- 新会话开始时注入历史记忆，实现跨会话的连续性

### 工具增强生成（TAG）

每个智能体拥有独立的工具注册表，支持：
- `get_user_comprehensive_profile` — 获取用户综合画像
- `search_knowledge_repository` — 知识库语义检索
- `query_institutional_database` — 教务数据查询
- `execute_strategy_engine` — 策略引擎执行

工具调用遵循"先工具、后总结"的编排策略，确保回复基于真实数据。

---

## 许可证

本项目为 2025 年国家级大学生创新创业训练计划项目成果，仅供学术研究与教育用途。

---

## 致谢

- **通义千问（Qwen）** 提供大语言模型能力
- **SiliconFlow** 提供模型推理服务
- **FastAPI / React / PostgreSQL** 开源社区
