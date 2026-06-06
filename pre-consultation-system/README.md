# 智能预问诊系统

基于规则引擎的患者预问诊与分诊系统，通过智能问答引导患者描述症状，自动计算疾病概率并推荐就诊科室。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI 0.111 |
| 数据库 | MySQL 8.0 + SQLAlchemy 2.0 ORM |
| 认证 | JWT (python-jose + passlib) |
| 前端 | Vue 3 + Pinia + Element Plus |
| 构建 | Vite |
| 容器化 | Docker Compose |

## 项目结构

```
pre-consultation-system/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口，CORS，路由注册
│   │   ├── config.py            # 数据库、JWT、推理阈值配置
│   │   ├── database.py          # SQLAlchemy 引擎与会话管理
│   │   ├── models/              # 数据模型 (10张表)
│   │   │   ├── symptom_dict.py      # 症状字典
│   │   │   ├── department.py        # 科室
│   │   │   ├── disease.py           # 疾病
│   │   │   ├── symptom_disease.py   # 症状-疾病关联
│   │   │   ├── differential_rule.py # 鉴别诊断规则
│   │   │   ├── consultation_session.py # 问诊会话
│   │   │   ├── question_record.py   # 问答记录
│   │   │   ├── doctor.py            # 医生信息
│   │   │   ├── registration.py      # 挂号记录
│   │   │   └── diagnosis_feedback.py # 诊断反馈
│   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   ├── api/                 # API 路由
│   │   │   ├── auth.py          # 登录认证、JWT签发、角色守卫
│   │   │   ├── consultation.py  # 问诊流程：开始→回答→结果→挂号
│   │   │   ├── doctor.py        # 医生端：今日患者、报告、反馈
│   │   │   └── admin.py         # 管理端：CRUD + 统计
│   │   └── services/
│   │       ├── reasoning_engine.py  # 推理引擎核心
│   │       └── symptom_standardizer.py # 症状标准化 (别名匹配 + AI预留)
│   ├── seed/seed_data.py        # 种子数据
│   ├── tests/
│   │   ├── conftest.py          # 测试夹具 (SQLite内存数据库)
│   │   └── test_reasoning_engine.py # 推理引擎单元测试
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── main.js              # Vue入口
│   │   ├── router/index.js      # Hash模式路由 + 角色守卫
│   │   ├── api/index.js         # Axios + JWT拦截器
│   │   ├── stores/              # Pinia状态管理
│   │   └── views/
│   │       ├── auth/Login.vue
│   │       ├── patient/         # 问诊、结果、挂号确认、我的挂号
│   │       ├── doctor/          # 今日患者、患者报告
│   │       └── admin/           # 症状管理、疾病管理、规则管理、统计
│   └── vite.config.js
└── docker-compose.yml
```

## 快速启动

### 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0
- Docker & Docker Compose (可选)

### 1. 数据库

```bash
docker run -d --name mysql-pre \
  -e MYSQL_ROOT_PASSWORD=20061006 \
  -e MYSQL_DATABASE=pre_consultation \
  -p 3307:3306 \
  mysql:8.0 --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci
```

### 2. 后端

```bash
cd backend
pip install -r requirements.txt

# 初始化种子数据
python -m seed.seed_data

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API 文档自动生成，访问 http://localhost:8000/docs

### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

前端运行在 http://localhost:5173

### Docker Compose 一键启动

```bash
docker-compose up -d
```

### 预置测试账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 患者 | patient01 | 123456 |
| 医生 | doctor01 | 123456 |
| 管理员 | admin | 123456 |

## 推理引擎

### 状态机

```
INITIAL → QUESTIONING → RECOMMENDING → BOOKING → COMPLETED
                         (最多5轮)                         → CANCELLED
```

### 停止条件

- 候选疾病数 ≤ 3
- 问答轮次 ≥ 5
- 无可鉴别的追问症状

### 核心函数

| 函数 | 说明 |
|------|------|
| `calculate_disease_scores` | 计算各疾病得分 = 已匹配症状权重 / 总权重 |
| `prune_by_required` | 剔除必要条件不满足的疾病 |
| `apply_differential_rules` | 应用鉴别诊断规则调整得分 |
| `select_next_symptom` | 选择鉴别力最高的下一个追问症状 |
| `generate_recommendation` | 生成科室推荐、紧急程度、药物过敏警告 |

## API 概览

### 认证 (prefix: `/api/auth`)

| 方法 | 路径 | 角色 | 说明 |
|------|------|------|------|
| POST | /login | 无 | 账号密码登录，返回 JWT |

### 预问诊 (prefix: `/api/consultation`)

| 方法 | 路径 | 角色 | 说明 |
|------|------|------|------|
| POST | /start | patient | 开始问诊，收集基础信息 |
| POST | /answer/{session_id} | patient | 回答症状追问 |
| GET | /result/{session_id} | patient | 获取推荐结果 |
| POST | /register | patient | 提交挂号 |
| GET | /my-registrations | patient | 我的挂号记录 |

### 医生端 (prefix: `/api/doctor`)

| 方法 | 路径 | 角色 | 说明 |
|------|------|------|------|
| GET | /today-patients | doctor | 今日挂号患者 |
| GET | /patient-report/{registration_id} | doctor | 患者问诊报告 |
| POST | /feedback | doctor | 提交诊断反馈 |

### 管理端 (prefix: `/api/admin`)

| 方法 | 路径 | 角色 | 说明 |
|------|------|------|------|
| GET/POST | /symptoms | admin | 症状字典 CRUD |
| GET/POST | /diseases | admin | 疾病 CRUD |
| GET/POST | /departments | admin | 科室 CRUD |
| GET/POST | /rules | admin | 鉴别规则 CRUD |
| POST | /associations | admin | 症状-疾病关联 |
| GET | /statistics | admin | 问诊统计与准确率 |

## 测试

```bash
cd backend
pytest tests/ -v
```

包含 12 个推理引擎单元测试（SQLite 内存数据库），覆盖：
- 疾病得分计算（完全匹配、部分匹配、无匹配）
- 必要条件剪枝（满足、不满足但部分匹配）
- 鉴别规则应用（条件匹配、不匹配、得分限制）
- 追问症状选择（必要条件优先、权重差异、无可选症状）
- 推荐生成（排序、紧急程度、过敏警告）

## 配置说明

通过环境变量覆盖默认配置（`app/config.py`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| DB_HOST | localhost | 数据库地址 |
| DB_PORT | 3307 | 数据库端口 |
| DB_USER | root | 数据库用户 |
| DB_PASSWORD | 20061006 | 数据库密码 |
| DB_NAME | pre_consultation | 数据库名 |
| JWT_SECRET | pre-consultation-secret-key... | JWT签名密钥 |
| JWT_EXPIRE_MINUTES | 480 | Token过期时间 (分钟) |
| MAX_QUESTION_ROUNDS | 5 | 最大追问轮数 |
| CANDIDATE_THRESHOLD | 3 | 候选疾病阈值 |
| DISCRIMINATION_THRESHOLD | 0.15 | 症状鉴别力阈值 |

## License

MIT
