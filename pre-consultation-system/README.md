# 智能预问诊系统 (Pre-consultation System)

患者在线描述症状 → AI 追问鉴别 → 推荐科室/疾病/医生 → 一键挂号。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | **FastAPI** (Python 3.11+) |
| 数据库 | **MySQL 8.0** + SQLAlchemy ORM |
| 认证 | JWT (HS256) + bcrypt |
| AI 引擎 | **DeepSeek API**（疾病排序/追问决策）+ 规则引擎融合 |
| NER 症状提取 | BERT (`shibing624/bert4ner-base-chinese`) + 关键词模糊匹配双引擎 |
| 前端 | **Vue 3** + Element Plus + Pinia + Vue Router |
| 部署 | Docker Compose (MySQL + Backend + Frontend Nginx) |

---

## 核心流程

```
患者描述症状
    ↓
症状提取 (NER BERT + 关键词 + 同义词表)
    ↓
初始化问诊会话 → 候选疾病评分
    ↓
追问循环 (最多5轮):
  1. 规则引擎计算疾病评分（symptom_disease 权重）
  2. 鉴别规则调整（differential_rule）
  3. DeepSeek 融合排序（可选，不可用时降级）
  4. 选择下一个追问症状（鉴别力算法）
  5. 用户回答 YES / NO / UNKNOWN
    ↓
达到停止条件 → 生成推荐（科室 + 疾病 + 紧急性）
    ↓
患者选择科室/医生/时段 → 挂号
    ↓
医生查看报告 → 反馈诊断结果
```

---

## 知识库规模

| 实体 | 数量 |
|---|---|
| 科室 | **14** |
| 疾病 | **81**（含中文基础疾病 34 + DDX 国际疾病 47） |
| 症状 | **159**（含别名共 427 个口语化表达） |
| 症状-疾病关联 | **749** |
| 鉴别规则 | 数据库驱动 |

> 可通过 `python -m seed.import_ddx --translate` 从 DDX 医疗知识图谱追加导入。

---

## 快速开始

### 前置条件

- **Docker**（推荐，一键部署，无需安装 Python/MySQL/Node）
- 或手动安装：
  - Python 3.11+
  - MySQL 8.0
  - Node.js 18+（前端）

### 方式一：本地开发

```bash
# 1. 启动 MySQL（确保运行在 3307 端口，密码 20061006）
#    或用 Docker: docker-compose up db

# 2. 后端
cd pre-consultation-system/backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（复制模板并修改）
cp .env.example .env
# 编辑 .env：至少设置 DB_PASSWORD 和 JWT_SECRET

# 初始化种子数据
python -m seed.seed_data

# （可选）导入 DDX 国际疾病知识库
python -m seed.import_ddx --translate

# 生产就绪检查
python startup_check.py

# 启动后端 → http://localhost:8000
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

```bash
# 3. 前端（新终端）
cd pre-consultation-system/frontend
npm install
npm run dev          # → http://localhost:5173
```

### 方式二：一键启动

```bash
# 在项目根目录
python start.py backend    # 启动后端（自动检查依赖、初始化种子）
python start.py frontend   # 启动前端
```

### 方式三：Docker Compose（推荐）

前置条件：安装 [Docker](https://docs.docker.com/get-docker/) 和 Docker Compose。

```bash
# 1. 创建环境变量文件
cd pre-consultation-system
cp .env.docker .env

# 2. 编辑 .env — 至少设置 DB_PASSWORD 和 JWT_SECRET
#    JWT_SECRET 生成方式: python -c "import secrets; print(secrets.token_hex(32))"

# 3. 一键启动全部服务（MySQL + Backend + Frontend）
docker compose up -d

# 4. 查看日志（可选）
docker compose logs -f backend

# 5. 停止服务
docker compose down
```

> 首次启动约需 2-5 分钟（拉取镜像 + 构建 + MySQL 初始化 + 种子数据导入）。

**服务地址：**

| 服务 | 地址 | 端口（可配） |
|---|---|---|
| 前端 | http://localhost:5173 | `FRONTEND_PORT` |
| 后端 API | http://localhost:8000 | `BACKEND_PORT` |
| Swagger 文档 | http://localhost:8000/docs | — |
| MySQL | localhost:3307 | `DB_EXTERNAL_PORT` |

**启动流程：**
```
docker compose up -d
  ├─ MySQL 启动 → healthcheck 通过
  ├─ Backend entrypoint:
  │   1. 等待 MySQL 就绪（最多 60 秒）
  │   2. 种子数据初始化（幂等：已有数据则跳过）
  │   3. 启动安全检查（startup_check.py）
  │   4. uvicorn --workers 2
  └─ Frontend: 等待 backend healthy → Nginx 启动
```

**常用命令：**
```bash
docker compose up -d              # 启动
docker compose ps                 # 查看状态
docker compose logs -f backend    # 查看后端日志
docker compose restart backend    # 重启后端
docker compose down               # 停止并删除容器
docker compose down -v            # 停止并删除容器+数据卷（⚠ 会清空数据库）
```

### 测试账户

| 角色 | 用户名 | 密码 |
|---|---|---|
| 患者 | `patient1` | `patient123` |
| 医生 | `doctor1` | `doctor123` |
| 管理员 | `admin` | `admin123` |

---

## 项目结构

```
pre-consultation-system/
├── docker-compose.yml              # MySQL + Backend + Frontend
├── .env.docker                     # Docker 部署环境变量模板
├── backend/
│   ├── Dockerfile                  # 后端 Docker 镜像
│   ├── docker-entrypoint.sh        # 容器启动入口（等待DB→种子→启动）
│   ├── .dockerignore               # Docker 构建排除文件
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口，CORS，限流，日志，会话清理
│   │   ├── config.py               # Pydantic Settings（环境变量驱动）
│   │   ├── database.py             # SQLAlchemy engine + SessionLocal
│   │   ├── logger.py               # 日志配置（RotatingFileHandler）
│   │   ├── api/                    # 路由层
│   │   │   ├── auth.py             # 登录 / JWT / refresh / me
│   │   │   ├── consultation.py     # 核心问诊流程
│   │   │   ├── doctor.py           # 医生端：今日患者 / 报告 / 反馈
│   │   │   └── admin.py            # 管理端：CRUD 症状 / 疾病 / 规则
│   │   ├── models/                 # 14 个 SQLAlchemy 模型
│   │   ├── schemas/                # Pydantic 请求/响应模型
│   │   └── services/               # 业务逻辑层
│   │       ├── symptom_extractor.py    # BERT NER + 关键词提取
│   │       ├── symptom_standardizer.py # 症状标准化
│   │       ├── extraction_service.py   # NER异步提取封装
│   │       ├── reasoning_engine.py     # 核心推理引擎
│   │       ├── final_scorer.py         # 规则+DeepSeek融合评分
│   │       ├── deepseek_client.py      # DeepSeek API 客户端
│   │       └── seed_symptoms.py        # 76个预定义症状
│   ├── seed/
│   │   ├── seed_data.py            # 基础种子数据（14科室/34疾病/76症状）
│   │   └── import_ddx.py           # DDX 国际知识图谱导入（50疾病）
│   ├── model/                      # NER 模型训练
│   │   ├── train_ner.py
│   │   ├── predict_ner.py
│   │   ├── augment_ner_data.py     # 训练数据增强
│   │   └── annotated_symptoms.json # 353条标注数据
│   ├── data/                       # DDX 原始 JSON
│   │   ├── ddx_conditions.json     # 49个疾病
│   │   └── ddx_evidences.json      # 223个症状证据
│   ├── tests/                      # pytest 集成测试
│   ├── .env.example                # 环境变量模板
│   ├── startup_check.py            # 生产就绪检查脚本
│   └── requirements.txt
└── frontend/
    ├── Dockerfile                  # 前端 Docker 镜像（多阶段：Node构建→Nginx运行）
    ├── nginx.conf                  # Nginx 配置（静态资源 + /api 反向代理）
    ├── .dockerignore               # Docker 构建排除文件
    └── src/
        ├── views/
        │   ├── patient/    # Consultation.vue, Result.vue, RegistrationConfirm.vue
        │   ├── doctor/     # TodayPatients.vue, PatientReport.vue, FeedbackHistory.vue
        │   └── admin/      # SymptomManage.vue, DiseaseManage.vue, RuleManage.vue
        ├── stores/         # Pinia 状态管理 (consultation.js, user.js)
        └── router/         # Vue Router
```

---

## API 概览

| 端点 | 方法 | 说明 | 限流 |
|---|---|---|---|
| `/api/auth/login` | POST | 登录获取 JWT Token | 5/min |
| `/api/auth/refresh` | POST | 刷新 Token | - |
| `/api/auth/me` | GET | 当前用户信息 | - |
| `/api/consultation/start` | POST | 开始问诊（提交症状描述） | 10/min |
| `/api/consultation/{id}/answer` | POST | 回答追问（YES/NO/UNKNOWN） | 10/min |
| `/api/consultation/{id}/result` | GET | 获取推荐结果 | - |
| `/api/consultation/pipeline-debug` | POST | 调试端点：查看全流程中间结果 | - |
| `/api/consultation/registration` | POST | 挂号 | - |
| `/api/doctor/today` | GET | 医生今日患者列表 | - |
| `/api/doctor/report/{id}` | GET | 患者详细报告 | - |
| `/api/doctor/feedback` | POST | 提交诊断反馈 | - |
| `/api/admin/symptoms` | CRUD | 症状管理 | - |
| `/api/admin/diseases` | CRUD | 疾病管理 | - |
| `/api/admin/rules` | CRUD | 鉴别规则管理 | - |
| `/api/admin/statistics` | GET | 统计数据 | - |

> 完整 API 文档：启动后端后访问 `http://localhost:8000/docs` (Swagger UI)

---

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DB_HOST` | `localhost` | MySQL 主机 |
| `DB_PORT` | `3307` | MySQL 端口 |
| `DB_USER` | `root` | MySQL 用户名 |
| `DB_PASSWORD` | (空) | ⚠ **生产必须设置** |
| `DB_NAME` | `pre_consultation` | 数据库名 |
| `JWT_SECRET` | (默认值) | ⚠ **生产必须替换为随机密钥** |
| `JWT_ALGORITHM` | `HS256` | JWT 签名算法 |
| `JWT_EXPIRE_MINUTES` | `480` | Token 有效期（分钟） |
| `CORS_ORIGINS` | `*` | ⚠ **生产必须限定域名**（逗号分隔） |
| `DEEPSEEK_API_KEY` | (空) | DeepSeek API 密钥（不设则降级为规则引擎） |
| `AI_MODE` | `degrade` | AI 模式：`degrade` / `rule_only` |
| `MAX_QUESTION_ROUNDS` | `5` | 最大追问轮数 |

> 复制 `backend/.env.example` 为 `backend/.env` 并填写实际值。

---

## 安全特性

| 特性 | 实现 |
|---|---|
| JWT 认证 | HS256 签名，8h 过期 + 7d 刷新 |
| 密码加密 | bcrypt 哈希 |
| **日志脱敏** | 请求体中的 `password`/`access_token`/`token`/`secret` 自动替换为 `***` |
| **限流保护** | slowapi：登录 5/min，问答 10/min，全局 200/min |
| **Prompt 注入防护** | DeepSeek 输入含 `ignore`/`system`/`override`/`绕过` 等关键词自动截断 |
| **会话清理** | 后台任务每小时清理超 24h 的未完成会话 |
| **并发控制** | `SELECT ... FOR UPDATE` 行锁防止重复回答 |
| **AI 降级** | DeepSeek 不可用时自动切换为纯规则引擎 |
| **安全警告** | 启动时检测默认 JWT/CORS/DB 密码并打印 RuntimeWarning |

---

## 关键设计决策

- **双引擎融合**：规则引擎（55%）+ DeepSeek AI（45%）加权评分。AI 可用时提升排序质量，不可用时降级为纯规则引擎，保证系统健壮性。
- **追问策略**：鉴别力算法 `∑|w_i − w_j| × score_i × score_j`，优先选择能区分 TOP 候选疾病的症状。
- **安全规则**：紧急疾病必在前 3 名，高置信度（>0.6）疾病不被移除。
- **NER 双引擎**：BERT 模型精度高但可能未安装 → 自动降级为关键词模糊匹配（支持同义词 + 口语填充词去除）。

---

## 后续规划

- [ ] **生产密钥注入**：通过 Docker secrets 或 K8s 环境变量替换默认 JWT_SECRET/DB_PASSWORD
- [ ] **NER 模型部署**：安装 `torch` + `transformers`，训练已有 353 条标注数据
- [ ] **DDX 前置条件映射**：完成剩余 113 个 antecedents 的中文翻译
- [ ] **测试覆盖**：补充症状提取、评分融合、追问选择等核心模块的单元测试
- [ ] **访客模式**：支持无需登录即可体验问诊
- [ ] **PDF 报告导出**：医生端一键导出患者问诊报告
