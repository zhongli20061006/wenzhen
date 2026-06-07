# 智能预问诊系统

基于 FastAPI + Vue3 的智能预问诊医疗系统，通过症状收集和疾病推理引擎为患者推荐科室和医生。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy + MySQL 8.0 |
| 前端 | Vue 3 + Vite + Element Plus + Pinia |
| 认证 | JWT (HS256) |
| 容器化 | Docker Compose |

## 快速启动

### 1. 启动 MySQL

```bash
cd pre-consultation-system
docker-compose up -d db
```

或使用本地 MySQL，端口 3307，root/20061006，数据库 `pre_consultation`。

### 2. 启动后端

```bash
cd pre-consultation-system/backend
pip install -r requirements.txt
python -m seed.seed_data      # 初始化种子数据（首次）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

或使用启动脚本：

```powershell
.\pre-consultation-system\start-backend.ps1
```

### 3. 启动前端

```bash
cd pre-consultation-system/frontend
npm install
npm run dev
```

或使用启动脚本：

```powershell
.\pre-consultation-system\start-frontend.ps1
```

## 访问

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |

## 测试账户

| 用户名 | 密码 | 角色 | 科室 |
|--------|------|------|------|
| `admin` | `admin123` | 管理员 | - |
| `patient1` | `patient123` | 患者 | - |
| `doctor_respiratory` | `resp123` | 医生 | 呼吸内科 |
| `doctor_digestive` | `dige123` | 医生 | 消化内科 |
| `doctor_cardio` | `cardio123` | 医生 | 心血管内科 |
| `doctor_neuro` | `neuro123` | 医生 | 神经内科 |
| `doctor_endocrine` | `endo123` | 医生 | 内分泌科 |
| `doctor_ortho` | `ortho123` | 医生 | 骨科 |
| `doctor_derm` | `derm123` | 医生 | 皮肤科 |
| `doctor_eye` | `eye123` | 医生 | 眼科 |
| `doctor_ent` | `ent123` | 医生 | 耳鼻喉科 |
| `doctor_oral` | `oral123` | 医生 | 口腔科 |
| `doctor_obgyn` | `obgyn123` | 医生 | 妇产科 |
| `doctor_ped` | `ped123` | 医生 | 儿科 |
| `doctor_emergency` | `emerg123` | 医生 | 急诊科 |
| `doctor_general` | `general123` | 医生 | 全科医学科 |

## 功能流程

### 患者端
1. **登录** → 进入问诊界面
2. **自述不适** → 自由描述或结构化输入症状
3. **AI 追问** → 系统逐轮询问鉴别症状 (最多 5 轮)
4. **查看推荐** → 科室推荐 + 匹配疾病 + 紧急程度
5. **挂号** → 选科室/医生/时段，查看可约名额
6. **我的挂号** → 查看挂号历史

### 医生端
1. **今日患者** → 按上午/下午筛选，点击查看报告
2. **患者报告** → 问诊记录、系统推荐、提交诊断反馈
3. **反馈记录** → 个人反馈历史 + 准确率统计

### 管理员端
1. **症状/疾病/科室管理** → CRUD 操作
2. **症状-疾病关联** → 权重和必选配置
3. **鉴别规则** → 疾病推理调整规则
4. **统计面板** → 问诊量、准确率

## 项目结构

```
问诊系统/
├── start.py                     # 启动脚本
├── .gitignore
└── pre-consultation-system/
    ├── docker-compose.yml       # MySQL + 后端 + 前端
    ├── README.md
    ├── start-backend.ps1
    ├── start-frontend.ps1
    ├── backend/
    │   ├── app/
    │   │   ├── api/             # auth, consultation, doctor, admin
    │   │   ├── models/          # 10 个数据模型
    │   │   ├── schemas/         # Pydantic 请求/响应
    │   │   ├── services/        # 推理引擎、症状标准化
    │   │   ├── main.py          # FastAPI 入口
    │   │   ├── database.py      # SQLAlchemy 配置
    │   │   ├── config.py        # 设置 (JWT, DB)
    │   │   └── logger.py        # 日志模块
    │   ├── seed/                # 种子数据
    │   └── tests/               # pytest
    └── frontend/
        ├── src/
        │   ├── views/
        │   │   ├── auth/        # Login.vue
        │   │   ├── patient/     # 问诊、结果、挂号
        │   │   ├── doctor/      # 今日患者、报告、反馈
        │   │   └── admin/       # 症状/疾病/规则管理、统计
        │   ├── stores/          # Pinia (user, consultation)
        │   ├── router/          # 路由配置
        │   └── api/             # Axios 配置
        └── vite.config.js
```

## 日志

运行时日志保存在 `backend/logs/`，包含：
- `app.log` - 请求摘要和业务操作
- `app_debug.log` - 完整请求体调试信息
- `app_error.log` - 错误追踪
