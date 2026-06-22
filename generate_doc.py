# -*- coding: utf-8 -*-
"""Generate technical document for 智能预问诊系统"""

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import datetime

doc = Document()

# ========== 样式设置 ==========
style = doc.styles['Normal']
font = style.font
font.name = 'Arial'
font.size = Pt(10.5)

# ========== 封面 ==========
for _ in range(6):
    doc.add_paragraph()

title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run('智能预问诊系统 — 技术总结文档')
run.bold = True
run.font.size = Pt(26)
run.font.color.rgb = RGBColor(0x1A, 0x56, 0xDB)

subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle.add_run(f'生成日期：{datetime.date.today().isoformat()}')
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

doc.add_page_break()

# ========== 辅助函数 ==========
def add_heading(text, level=1):
    h = doc.add_heading(text, level=level)
    return h

def add_code(text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = 'Consolas'
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    p.paragraph_format.left_indent = Cm(0.5)
    return p

def add_bullet(text, bold_prefix=None):
    p = doc.add_paragraph(style='List Bullet')
    if bold_prefix:
        run = p.add_run(bold_prefix)
        run.bold = True
        p.add_run(text)
    else:
        p.add_run(text)
    return p

def add_table(headers, rows):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            table.rows[ri + 1].cells[ci].text = str(val)
    return table

# ================================================================
# 1. 项目概述
# ================================================================
add_heading('1. 项目概述', level=1)

doc.add_paragraph(
    '智能预问诊系统是一个基于规则引擎与 AI（DeepSeek）辅助的患者预问诊与分诊系统。'
    '系统通过智能化的症状采集和鉴别诊断推理，自动计算疾病概率并推荐就诊科室，'
    '帮助患者在挂号前完成预问诊流程，提升导诊准确率与就诊效率。'
)

add_heading('项目定位', level=2)
add_bullet('替代传统人工导诊台，实现智能分诊')
add_bullet('采集患者结构化症状数据，辅助医生决策')
add_bullet('支持 14 个科室、34 种常见疾病的鉴别诊断')

add_heading('核心功能模块', level=2)
add_bullet('预问诊：症状采集 → 推理引擎 → 追问 → 疾病评分 → 科室推荐')
add_bullet('挂号：科室/医生/时段选择，支持当日挂号')
add_bullet('医生端：今日患者列表、问诊报告、诊断反馈')
add_bullet('管理端：症状/疾病/规则 CRUD、统计仪表盘')

# ================================================================
# 2. 技术栈
# ================================================================
add_heading('2. 技术栈', level=1)

add_heading('2.1 后端', level=2)
add_table(
    ['技术', '版本', '用途'],
    [
        ['FastAPI', '0.111.0', '异步 Python Web 框架'],
        ['Uvicorn', '0.29.0', 'ASGI 服务器'],
        ['SQLAlchemy', '2.0.30', 'ORM 与数据库抽象层'],
        ['PyMySQL', '1.1.0', 'MySQL 驱动'],
        ['python-jose', '3.3.0', 'JWT 令牌生成/验证'],
        ['bcrypt', '4.2.1', '密码哈希'],
        ['Pydantic', '2.7.3', '请求/响应校验'],
        ['Pydantic-Settings', '2.3.0', '配置管理（环境变量）'],
        ['APScheduler', '3.10.4', '后台任务调度'],
        ['httpx', '0.27.0', '异步 HTTP 客户端（DeepSeek API）'],
        ['Transformers', '>=4.40.0', 'BERT NER 模型'],
        ['PyTorch', '>=2.0.0', '深度学习框架'],
        ['XGBoost', '>=2.0.0', '机器学习（特性标志后）'],
    ]
)

add_heading('2.2 前端', level=2)
add_table(
    ['技术', '版本', '用途'],
    [
        ['Vue 3', '^3.5.34', '前端框架'],
        ['Vite', '^8.0.12', '构建工具'],
        ['Pinia', '^3.0.4', '状态管理'],
        ['Vue Router', '^4.6.4', '客户端路由'],
        ['Element Plus', '^2.14.1', 'UI 组件库'],
        ['Axios', '^1.17.0', 'HTTP 客户端'],
    ]
)

add_heading('2.3 基础设施', level=2)
add_bullet('数据库：MySQL 8.0（utf8mb4）')
add_bullet('容器化：Docker Compose（MySQL + Backend + Frontend）')
add_bullet('AI 接口：DeepSeek API（deepseek-v4-flash 模型）')
add_bullet('HuggingFace 镜像：hf-mirror.com（国内加速）')

# ================================================================
# 3. 数据库模型
# ================================================================
add_heading('3. 数据库模型', level=1)
doc.add_paragraph('系统共 13 张数据表，实体关系如下：')

add_heading('3.1 核心业务表', level=2)

add_table(
    ['表名', '说明', '关键字段'],
    [
        ['symptom_dict', '症状字典（62 个症状）', 'name(UNIQUE), aliases, category, level'],
        ['symptom_synonym', '症状同义词（~70 条）', 'symptom_id(FK), term, weight'],
        ['disease', '疾病（34 种）', 'name(UNIQUE), icd_code(UNIQUE), urgency, department_id'],
        ['symptom_disease', '症状-疾病多对多关联', 'weight, is_required, is_positive, is_discriminative'],
        ['department', '科室（14 个）', 'name(UNIQUE), parent_id(自引用)'],
        ['differential_rule', '鉴别诊断规则（10 条）', 'condition_json, result_json, priority'],
        ['disease_confuser', '易混淆疾病对（14 对）', 'disease_a_id, disease_b_id, distinguishing_symptom_ids'],
    ]
)

add_heading('3.2 会话与流程表', level=2)
add_table(
    ['表名', '说明', '关键字段'],
    [
        ['consultation_session', '问诊会话（状态机）', 'id(UUID), status(状态机), collected_data(JSON), candidate_diseases, asked_symptoms'],
        ['question_record', '问答记录', 'consultation_id(FK), round, symptom_id, question_text, answer(YES/NO/UNKNOWN)'],
        ['registration', '挂号记录', 'patient_id, doctor_id, department_id, registration_date, time_slot, status'],
        ['diagnosis_feedback', '医生诊断反馈', 'registration_id, recommended_dept, actual_dept, is_correct, error_reason'],
    ]
)

add_heading('3.3 用户与角色表', level=2)
add_table(
    ['表名', '说明', '关键字段'],
    [
        ['user', '用户（patient/doctor/admin）', 'username(UNIQUE), password(bcrypt), role, doctor_id(FK)'],
        ['doctor', '医生信息', 'name, title, department_id, introduction, max_patients_per_session'],
    ]
)

# ================================================================
# 4. 架构与模块设计
# ================================================================
add_heading('4. 架构与模块设计', level=1)

add_heading('4.1 后端分层', level=2)
add_bullet('API 层 (api/)：路由处理、权限校验、请求/响应序列化')
add_bullet('服务层 (services/)：业务逻辑（推理引擎、DeepSeek 客户端、评分融合、症状提取）')
add_bullet('模型层 (models/)：SQLAlchemy ORM 数据模型')
add_bullet('模式层 (schemas/)：Pydantic 请求/响应模型')

add_heading('4.2 前后端交互', level=2)
doc.add_paragraph(
    '前端 Vue 3 应用使用 Hash 路由模式，通过 Axios 与后端 REST API 通信。'
    'JWT 令牌存储在 localStorage，通过 Axios 拦截器自动注入 Authorization 头。'
    '后端 CORS 全开（*），便于开发调试。'
)

add_heading('4.3 API 路由设计', level=2)
add_table(
    ['前缀', '端点数', '认证', '角色'],
    [
        ['/api/auth', '2', '部分', '无 / Bearer'],
        ['/api/consultation', '11', 'Bearer', 'patient（部分无限制）'],
        ['/api/doctor', '4', 'Bearer', 'doctor'],
        ['/api/admin', '15', 'Bearer', 'admin'],
    ]
)

# ================================================================
# 5. 核心算法
# ================================================================
add_heading('5. 核心算法与逻辑', level=1)

add_heading('5.1 疾病评分引擎', level=2)
doc.add_paragraph(
    'score = (positive_matched_weight × 1.0 + negative_met_weight × 0.6) / total_weight'
)
add_bullet('鉴别症状（is_discriminative）：权重 ×1.5')
add_bullet('阳性症状匹配：全额加分')
add_bullet('阴性症状（is_positive=False）：答"否"时权重 ×0.6，未提及则 ×0.3')

add_heading('5.2 症状追问选择算法', level=2)
add_bullet('对每个未问症状 s，计算鉴别力：')
add_code(
    'disc(s) = Σ|weight(s,di) - weight(s,dj)| × score(di) × score(dj)\n'
    '        对每对疾病(di, dj)求和'
)
add_bullet('放大系数：疾病混淆对 ×1.5 / 鉴别标记 ×1.3 / 必要条件 ×2.0 / 阴性症状 ×0.8')

add_heading('5.3 状态机（问诊生命周期）', level=2)
add_code(
    'INITIAL → QUESTIONING → RECOMMENDING → BOOKING → COMPLETED\n'
    '            ↑ max 5 轮          ↓                      ↘\n'
    '    候选 ≤ 3 或轮次 ≥ 5    无更多症状           CANCELLED'
)

add_heading('5.4 DeepSeek 评分融合', level=2)
add_bullet('规则引擎权重 55% + DeepSeek 权重 45%')
add_bullet('一致性 > 0.7（Kendall Tau 简化版）：统一加成 0.1')
add_bullet('评分差异 > 0.3：标记为冲突')
add_bullet('安全覆盖：紧急疾病强制前 3，规则分 > 0.6 的疾病不可移除')

add_heading('5.5 症状提取管道', level=2)
add_bullet('优先使用微调 BERT NER 模型（shibing624/bert4ner-base-chinese）')
add_bullet('BERT 不可用时回退到关键词匹配（症状名称 + 别名 + 同义词表）')
add_bullet('输入防护：Prompt 注入黑名单拦截 + 2000 字符截断')

# ================================================================
# 6. 遇到的Bug与踩坑记录（核心）
# ================================================================
add_heading('6. 开发中遇到的 Bug 与踩坑记录', level=1)
doc.add_paragraph(
    '以下整理了开发过程中遇到的所有已知问题、修复与决策，按模块分类。'
)

# 6.1
add_heading('6.1 后端配置与集成', level=2)

add_heading('[Bug] DeepSeek 默认禁用导致 AI 融合不生效', level=3)
add_bullet('现象：', '即使配置了 DEEPSEEK_API_KEY，AI 模式仍走 degrade_only（纯规则引擎）')
add_bullet('根因：', 'config.py 中 DEEPSEEK_ENABLED 默认值 = False')
add_bullet('修复：', '提交 7c3ee61，将默认值改为 True')
add_bullet('教训：', '特性标志默认值应与命名语义一致，测试需覆盖启用/禁用两种路径')

add_heading('[问题] Prompt 注入防护双刃剑', level=3)
add_bullet('现象：', '用户输入含"系统"、"指令"等关键词时被误拦截截断')
add_bullet('分析：', '黑名单包含中英文关键词（"系统"、"system"、"指令"、"override"等），医疗场景下"系统"为高频正常用词')
add_bullet('妥协方案：', '拦截时仅截断而非拒绝，保留前 200 字符')
add_bullet('教训：', '黑名单过滤在医疗领域误报率高，需考虑上下文感知或改为白名单+语义检测')

add_heading('[问题] DeepSeek JSON 解析脆弱性', level=3)
add_bullet('现象：', 'LLM 返回非标准 JSON（含 Markdown 代码块、额外文字等），解析失败')
add_bullet('方案：', '两阶段解析：先正则匹配 {...}，再首尾大括号截取；失败返回默认值')
add_bullet('遗留：', '无重试机制，一次解析失败直接走 degrade 路径')

# 6.2
add_heading('6.2 推理引擎', level=2)

add_heading('[Bug] 必要条件剪枝策略过于激进', level=3)
add_bullet('问题：', 'prune_by_required 逻辑：required_met=False 且 score=0 时剔除。但某些疾病必要条件被否定时仍可能有部分匹配得分(score>0)，应保留')
add_bullet('处理：', '已在 prune_by_required 中保留 score>0 的病例 ("score>0" 条件)')
add_bullet('剩余风险：', '必要条件(如"发热"标记为 is_required=True)被回答 NO 后疾病得分降为 0，即使其他症状高度匹配也会被完全排除')

add_heading('[Bug] 鉴别力评分中罕见症状被忽略', level=3)
add_bullet('问题：', 'select_next_symptom 只取 top 10 疾病做两两比较，不属于 top 10 的疾病关联症状不会被纳入追问候选')
add_bullet('影响：', '早期轮次小概率疾病的相关症状不会被问到，可能导致漏诊')
add_bullet('跟踪：', '无修复记录，属已知设计取舍')

add_heading('[Bug] 鉴别规则条件 severity 字段命名歧义', level=3)
add_bullet('问题：', '规则 JSON 中使用 "severity_gte"/"severity_lt"，但 seed_data.py 中传入 {"severity_gte": 0} 导致 >=0 永远为 True')
add_bullet('分析：', 'seed_data.py 规则"咳嗽持续>咳嗽3周+消瘦 - 结核排查"使用了 severity_gte: 0，使条件无条件匹配')
add_bullet('影响：', '该鉴别规则未按预期工作——始终触发调整')

add_heading('[Bug] 阴性症状(negative symptom)评分逻辑疑问', level=3)
add_bullet('问题：', 'calculate_disease_scores 中 is_positive=False 的症状：若被否定(negative_symptom_names)则加分×0.6，若未提及则加×0.3')
add_bullet('分析：', '逻辑假设"未提及=轻微否定"，但临床上"未提及"不等于"无此症状"，可能导致假阴性偏向')
add_bullet('说明：', '这是有意的保守设计，侧重于对阴性症状降权而非排除')

# 6.3
add_heading('6.3 BERT NER 症状提取', level=2)

add_heading('[Bug] predict_ner.py 中的 ID 自增覆写问题', level=3)
add_bullet('现象：', '模型尚未微调或输出目录不存在时，_load_model 回退到原始 bert4ner-base-chinese，但使用 ignore_mismatched_sizes=True')
add_bullet('风险：', '原始模型输出 3 个标签(B-SYMPTOM/I-SYMPTOM/O)，但微调模型可能有不同标签体系，大小不匹配静默忽略可能导致预测混乱')

add_heading('[Bug] map_to_symptom_dict 中的低置信度部分匹配', level=3)
add_code(
    'if text not in {sym.name for sym in symptoms}:\n'
    '    for sym in symptoms:\n'
    '        if sym.name and text in sym.name:\n'
    '            results.append(...confidence=0.4)'
)
add_bullet('问题：', '"头痛"可能在疾病数据里匹配到"偏头痛"症状。使用子串匹配(text in sym.name)过于宽松')
add_bullet('举例：', '患者描述"头痛"，可能被匹配到"头痛"（正确）或"偏头痛"（作为别名正确，但在逻辑中走 partial 路径，confidence 0.4）')

add_heading('[Bug] 症状提取后初始得分计算差异', level=3)
add_bullet('问题：', 'description 经过 BERT 提取出的症状和直接填写症状走不同路径（extract_from_description vs standardize_symptoms），两者解析结果可能不一致')
add_bullet('影响：', '同一患者用自然语言描述 vs 罗列关键词，可能得到不同症状集合和初始得分')

# 6.4
add_heading('6.4 前端', level=2)

add_heading('[Bug] 挂号日期默认值为"明天"', level=3)
add_bullet('现象：', '患者打开挂号确认页面时，日期默认选中第二天')
add_bullet('根因：', 'RegistrationConfirm.vue 中 form.reg_date = new Date(Date.now() + 86400000)')
add_bullet('修复：', '提交 bdd1ac9，改为 new Date()')
add_bullet('教训：', '日期默认值应与业务场景一致——大多数患者期望"今天"')

add_heading('[Bug] 患者角色标签无样式', level=3)
add_bullet('现象：', 'Profile.vue 中患者标签显示为纯文本无背景色')
add_bullet('根因：', 'el-tag type="" 空字符串导致 Element Plus 不应用任何样式')
add_bullet('修复：', '提交 bdd1ac9，patient 角色 type 改为 "info"')
add_bullet('教训：', '枚举映射应覆盖所有可能值，或提供安全的默认回退')

add_heading('[Bug] Vite IPv4 访问受限', level=3)
add_bullet('现象：', '局域网设备无法访问前端（仅 localhost 可用）')
add_bullet('根因：', 'vite.config.js 未设置 host: "0.0.0.0"，Vite 默认绑定 IPv6 localhost')
add_bullet('修复：', '提交 1233b8a，添加 host: "0.0.0.0"')
add_bullet('教训：', '容器化/局域网环境下必须显式指定 host 绑定')

add_heading('[Bug] 前端路由守卫缺失', level=3)
add_bullet('现象：', 'router/index.js 中部分路由（Consultation、Result、RegistrationConfirm）缺少 role 守卫，未登录用户可能访问敏感页面')
add_bullet('说明：', '后端有 JWT 鉴权兜底，但前端缺少 401 拦截友好的重定向逻辑')
add_bullet('妥协：', '后端返回 401 时，Axios 拦截器自动 logout 并 redirect 到 /login')

add_heading('[Bug] Axios 响应拦截器返回 res.data 导致错误处理复杂', level=3)
add_bullet('问题：', 'api/index.js 中 response 拦截器直接返回 res.data，导致调用方无法区分 HTTP 状态码和响应体')
add_bullet('影响：', '错误处理全靠 err.response?.data?.detail，部分端点返回不同格式错误时前端可能显示 undefined')

# 6.5
add_heading('6.5 种子数据', level=2)

add_heading('[Bug] 症状同义词插入前存在重复判断逻辑缺陷', level=3)
add_code(
    'for sname, term, weight in synonym_list:\n'
    '    if sname in symptoms and term in symptoms:\n'
    '        pass  # term也在症状中就跳过——但这时应该使用sname的ID'
)
add_bullet('问题：', '当 synonym 的 term 也是 symptom 名称时(如"偏头痛"既是症状又是"头痛"的别名)，该同义词记录被静默跳过未插入')
add_bullet('影响：', '部分同义词映射缺失，影响关键词匹配召回率')
add_bullet('例外：', '此逻辑实际影响较小，因为此类 term 已在 symptom_dict 中可作为独立症状匹配')

add_heading('[问题] 测试账户密码耦合于用户名', level=3)
add_bullet('现象：', 'seed_users() 中密码基于用户名动态生成：pwd = username.split("_")[1][:4] + "123"')
add_bullet('风险：', '任何知道此生成规则的人可直接推导所有医生账户密码')
add_bullet('说明：', '系统为原型/演示用途，生成规则仅用于方便')

# 6.6
add_heading('6.6 测试', level=2)

add_heading('[Bug] 测试用例剪枝逻辑覆盖不足', level=3)
add_bullet('问题：', 'test_reasoning_engine.py 中 TestPruneByRequired 的 test_score_keeps_partial 测试了一个 required_met=False 但 score=0.5 的疾病应该保留')
add_bullet('缺口：', '未测试 required_met=False 且 score=0 的边缘情况——该情况应该被剔除')
add_bullet('结果：', '功能实际正确，但缺少回归测试保护')

add_heading('[Bug] 测试数据中鉴别规则与种子数据不完全一致', level=3)
add_bullet('现象：', 'conftest.py 的规则 condition_json={"symptoms": ["发热", "头痛", "呕吐"]}，但 symptom_disease 关联中"呕吐"未关联到"普通感冒"')
add_bullet('影响：', '测试中 rule 调整"普通感冒"-0.1 时其 score 从 0.4 降至 0.3（测试正确），但若添加更多疾病可能暴露关联缺失问题')

# ================================================================
# 7. 架构决策记录
# ================================================================
add_heading('7. 架构决策记录（ADR）', level=1)

add_heading('ADR-1: 规则引擎为主 + AI 为辅的混合架构', level=2)
add_bullet('背景：', '需要保证核心功能离线可用，同时利用 LLM 提升准确率')
add_bullet('决策：', '规则引擎权重 55% + DeepSeek 45%，设 degrade 降级模式')
add_bullet('结果：', 'DeepSeek 不可用时自动降级为纯规则引擎，系统不中断')

add_heading('ADR-2: JSON 字段存储会话状态', level=2)
add_bullet('背景：', '问诊会话的数据结构频繁变更且高度动态')
add_bullet('决策：', 'consultation_session 使用 MySQL JSON 类型存储 collected_data、candidate_diseases、asked_symptoms 等')
add_bullet('代价：', '无法在数据库层面做关联查询和索引优化；JSON 字段类型变更不兼容')

add_heading('ADR-3: 前端 Hash 路由', level=2)
add_bullet('背景：', '前端为单页应用，部署在容器/反向代理下')
add_bullet('决策：', '使用 Hash 模式路由而非 History 模式，避免服务端路由配置')
add_bullet('代价：', 'URL 带 # 符号，SEO 不友好（对内部系统可接受）')

add_heading('ADR-4: 状态机在数据库层持久化', level=2)
add_bullet('背景：', '问诊流程有明确的状态转换和并发控制需求')
add_bullet('决策：', '状态字段存储在数据库，通过轮次(round)唯一约束防重复提交')
add_bullet('问题：', '缺少乐观锁/版本号，高并发下可能状态覆盖')

# ================================================================
# 8. 已知问题与改进方向
# ================================================================
add_heading('8. 已知问题与改进方向', level=1)

add_heading('8.1 功能缺陷', level=2)
add_bullet('缺乏并发控制：', '问诊会话无乐观锁，可能状态覆盖')
add_bullet('无异步任务队列：', 'DeepSeek 请求在请求-响应周期内同步等待（10s 超时），阻塞工作线程')
add_bullet('缺乏数据加密：', 'JWT_SECRET 明文在配置中，无密钥轮换机制')
add_bullet('API 响应格式不统一：', '部分端点返回 data 直接，部分嵌套在对象中')
add_bullet('无 Rate Limiting：', '无防刷机制，DeepSeek API 调用可能产生意外费用')

add_heading('8.2 测试覆盖', level=2)
add_bullet('只有推理引擎的 12 个单元测试，覆盖率不足 20%')
add_bullet('无前端的 E2E 测试')
add_bullet('无 DeepSeek 集成的集成测试')
add_bullet('无 API 契约测试')

add_heading('8.3 改进建议', level=2)
add_bullet('引入 Celery 或 APScheduler 异步任务队列处理 AI 请求')
add_bullet('为问诊会话添加乐观锁（version 字段）')
add_bullet('配置从环境变量读取敏感信息，运行态加密存储')
add_bullet('添加前端路由守卫统一拦截 + 全局 401 重定向')
add_bullet('引入 pytest-cov 并设置覆盖率目标（≥70%）')

# ================================================================
# 9. 项目统计
# ================================================================
add_heading('9. 项目统计', level=1)

add_table(
    ['指标', '数值'],
    [
        ['后端 Python 代码（行数）', '约 3,800'],
        ['前端 Vue/JS 代码（行数）', '约 1,500'],
        ['数据表', '13'],
        ['API 端点', '32'],
        ['前端页面', '14'],
        ['单元测试', '12'],
        ['Git 提交', '23'],
        ['Bug 修复提交', '3（显式标记）'],
        ['参与开发者', '1'],
        ['开发周期', '约 2 天（密集开发）'],
    ]
)

# ========== 保存 ==========
output_path = r'D:\DjangoProject\问诊系统\智能预问诊系统_技术总结文档.docx'
doc.save(output_path)
print(f'文档已生成: {output_path}')
