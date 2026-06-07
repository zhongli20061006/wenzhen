"""
种子数据初始化脚本。
运行方式：python -m seed.seed_data
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import bcrypt
from app.database import SessionLocal, engine, Base
from app.models.department import Department
from app.models.disease import Disease
from app.models.symptom_dict import SymptomDict, SymptomLevel
from app.models.symptom_disease import SymptomDisease
from app.models.differential_rule import DifferentialRule
from app.models.doctor import Doctor
from app.models.user import User

Base.metadata.create_all(bind=engine)


def seed():
    db = SessionLocal()

    if db.query(Department).count() > 0:
        print("数据已存在，跳过初始化")
        db.close()
        return

    # ========== 科室 ==========
    depts = {}
    dept_list = [
        "呼吸内科", "消化内科", "心血管内科", "神经内科", "内分泌科",
        "骨科", "皮肤科", "眼科", "耳鼻喉科", "口腔科",
        "妇产科", "儿科", "急诊科", "全科医学科",
    ]
    for name in dept_list:
        dep = Department(name=name)
        db.add(dep)
        db.flush()
        depts[name] = dep.id
    print(f"科室: {len(dept_list)} 个")

    # ========== 症状 ==========
    symptoms = {}
    symptom_list = [
        ("发热", "发烧,体温升高,烧,高热,低热", "全身", SymptomLevel.MAIN),
        ("咳嗽", "干咳,呛咳,咳痰,阵咳", "呼吸系统", SymptomLevel.MAIN),
        ("咳痰", "痰多,黄痰,白痰,泡沫痰", "呼吸系统", SymptomLevel.MAIN),
        ("呼吸困难", "气短,气促,喘不上气,呼吸不畅", "呼吸系统", SymptomLevel.MAIN),
        ("胸痛", "胸口痛,胸闷,胸骨后痛", "循环系统", SymptomLevel.MAIN),
        ("心悸", "心慌,心跳快,心跳不齐", "循环系统", SymptomLevel.SECONDARY),
        ("头痛", "头疼,偏头痛,前额痛,后脑痛", "头颈部", SymptomLevel.MAIN),
        ("头晕", "眩晕,天旋地转,头昏", "头颈部", SymptomLevel.MAIN),
        ("恶心", "想吐,反胃", "消化系统", SymptomLevel.SECONDARY),
        ("呕吐", "吐,干呕,喷射性呕吐", "消化系统", SymptomLevel.MAIN),
        ("腹痛", "肚子痛,胃痛,腹部不适,绞痛", "消化系统", SymptomLevel.MAIN),
        ("腹泻", "拉肚子,水样便,大便次数多", "消化系统", SymptomLevel.MAIN),
        ("便秘", "大便干结,排便困难,大便不畅", "消化系统", SymptomLevel.SECONDARY),
        ("腹胀", "肚子胀,胃胀,腹部胀满", "消化系统", SymptomLevel.SECONDARY),
        ("食欲不振", "不想吃饭,厌食,没胃口", "消化系统", SymptomLevel.SECONDARY),
        ("消瘦", "体重下降,瘦了,体重减轻", "全身", SymptomLevel.SECONDARY),
        ("乏力", "没力气,疲乏,浑身没劲,疲劳", "全身", SymptomLevel.SECONDARY),
        ("关节痛", "关节疼,关节肿痛,膝盖痛", "运动系统", SymptomLevel.SECONDARY),
        ("腰痛", "腰疼,腰酸,腰部不适,腰肌痛", "运动系统", SymptomLevel.MAIN),
        ("皮疹", "出疹子,红斑,丘疹,荨麻疹", "皮肤", SymptomLevel.MAIN),
        ("瘙痒", "痒,皮肤痒,全身痒", "皮肤", SymptomLevel.SECONDARY),
        ("视力模糊", "看不清,视力下降,视物模糊", "五官", SymptomLevel.SECONDARY),
        ("耳鸣", "耳朵响,嗡嗡声,听力下降", "五官", SymptomLevel.SECONDARY),
        ("鼻塞", "鼻子不通,鼻堵,流鼻涕", "五官", SymptomLevel.SECONDARY),
        ("咽痛", "嗓子痛,喉咙痛,吞咽痛", "五官", SymptomLevel.MAIN),
        ("月经不调", "月经紊乱,经期不规律,月经量少", "生殖系统", SymptomLevel.MAIN),
        ("阴道出血", "不规则出血,接触性出血", "生殖系统", SymptomLevel.MAIN),
        ("尿频", "小便次数多,尿多,排尿频繁", "泌尿系统", SymptomLevel.SECONDARY),
        ("尿痛", "小便痛,排尿痛,尿道刺痛", "泌尿系统", SymptomLevel.SECONDARY),
        ("水肿", "浮肿,眼睑肿,下肢肿,全身肿", "全身", SymptomLevel.SECONDARY),
        ("抽搐", "抽筋,惊厥,痉挛,四肢抽动", "神经", SymptomLevel.MAIN),
        ("意识障碍", "昏迷,意识不清,嗜睡,反应迟钝", "神经", SymptomLevel.MAIN),
        ("肢体麻木", "手脚麻,半身麻木,面麻,舌麻", "神经", SymptomLevel.SECONDARY),
        ("口眼歪斜", "面瘫,嘴巴歪,眼斜,嘴角下垂", "神经", SymptomLevel.MAIN),
        ("言语不清", "说话不利索,口齿不清,失语", "神经", SymptomLevel.MAIN),
        ("吞咽困难", "咽不下东西,吞咽哽咽", "消化系统", SymptomLevel.SECONDARY),
        ("便血", "大便带血,黑便,血便", "消化系统", SymptomLevel.MAIN),
        ("呕血", "吐血,呕吐物带血", "消化系统", SymptomLevel.MAIN),
        ("黄疸", "皮肤发黄,眼睛黄,小便黄", "消化系统", SymptomLevel.MAIN),
        ("多饮", "口渴,喜欢喝水,饮水量大", "全身", SymptomLevel.SECONDARY),
        ("多尿", "夜尿多,尿量多,尿频量多", "泌尿系统", SymptomLevel.SECONDARY),
        ("多食", "吃得多,容易饿,食量大", "全身", SymptomLevel.SECONDARY),
        ("背痛", "背疼,后背痛,肩背痛", "运动系统", SymptomLevel.SECONDARY),
        ("颈部僵硬", "脖子硬,颈痛,颈椎痛", "运动系统", SymptomLevel.SECONDARY),
        ("畏光", "怕光,怕见光,遇光不适", "五官", SymptomLevel.SECONDARY),
        ("流泪", "流眼泪,泪多,迎风流泪", "五官", SymptomLevel.SECONDARY),
        ("打喷嚏", "喷嚏,打喷涕,连续喷嚏", "呼吸系统", SymptomLevel.SECONDARY),
        ("流鼻涕", "流清涕,流黄涕,鼻水", "呼吸系统", SymptomLevel.SECONDARY),
        ("夜间盗汗", "睡觉出汗,夜间出汗,醒后汗止", "全身", SymptomLevel.SECONDARY),
        ("淋巴结肿大", "淋巴肿大,颈部结节,腋下肿块", "全身", SymptomLevel.SECONDARY),
        ("口腔溃疡", "口疮,嘴破,口腔糜烂", "口腔", SymptomLevel.SECONDARY),
        ("牙痛", "牙疼,牙龈痛,牙髓痛", "口腔", SymptomLevel.MAIN),
        ("颈部肿块", "甲状腺肿,脖子粗,颈部包块", "头颈部", SymptomLevel.MAIN),
        ("心悸气短", "活动后心慌,劳力性气短", "循环系统", SymptomLevel.MAIN),
        ("肩痛", "肩膀痛,肩周痛,抬肩困难", "运动系统", SymptomLevel.SECONDARY),
    ("肌肉痛", "肌肉酸痛,浑身疼,全身酸痛,肌痛", "全身", SymptomLevel.SECONDARY),
    ("胸闷", "胸口闷,胸部压迫感,憋气", "循环系统", SymptomLevel.SECONDARY),
    ("耳痛", "耳朵疼,耳内痛,耳根痛", "五官", SymptomLevel.SECONDARY),
    ("关节肿胀", "关节肿,膝盖肿,关节红肿", "运动系统", SymptomLevel.SECONDARY),
    ("面部压痛", "面痛,脸颊痛,面部按压痛", "五官", SymptomLevel.SECONDARY),
    ("耳后痛", "耳根后痛,耳后压痛", "五官", SymptomLevel.SECONDARY),
    ]
    for name, aliases, category, level in symptom_list:
        sym = SymptomDict(name=name, aliases=aliases, category=category, level=level.value)
        db.add(sym)
        db.flush()
        symptoms[name] = sym.id
    print(f"症状: {len(symptom_list)} 个")

    # ========== 疾病 ==========
    diseases = {}
    disease_list = [
        ("普通感冒", "J00", "鼻病毒等引起的上呼吸道感染", "就诊", "呼吸内科"),
        ("流感", "J11", "流感病毒引起的急性呼吸道传染病", "紧急", "呼吸内科"),
        ("肺炎", "J18", "肺部感染性炎症", "紧急", "呼吸内科"),
        ("支气管炎", "J20", "支气管黏膜炎症", "就诊", "呼吸内科"),
        ("慢性阻塞性肺疾病", "J44", "慢性气道阻塞性疾病", "就诊", "呼吸内科"),
        ("哮喘", "J45", "慢性气道炎症性疾病", "紧急", "呼吸内科"),
        ("高血压", "I10", "动脉血压持续升高", "就诊", "心血管内科"),
        ("冠心病", "I25", "冠状动脉粥样硬化性心脏病", "紧急", "心血管内科"),
        ("心律失常", "I49", "心脏电活动异常", "就诊", "心血管内科"),
        ("心肌炎", "I51", "心肌局限性或弥漫性炎症", "紧急", "心血管内科"),
        ("胃炎", "K29", "胃黏膜炎症", "就诊", "消化内科"),
        ("消化性溃疡", "K25", "胃或十二指肠黏膜溃疡", "就诊", "消化内科"),
        ("急性胃肠炎", "A09", "胃肠道急性感染", "就诊", "消化内科"),
        ("肝硬化", "K74", "肝弥漫性纤维化", "就诊", "消化内科"),
        ("胆囊炎", "K81", "胆囊炎症", "就诊", "消化内科"),
        ("偏头痛", "G43", "原发性头痛疾病", "就诊", "神经内科"),
        ("脑膜炎", "G03", "脑膜炎症性病变", "紧急", "神经内科"),
        ("脑卒中", "I64", "急性脑血管意外", "紧急", "神经内科"),
        ("面神经麻痹", "G51", "面神经非化脓性炎症", "就诊", "神经内科"),
        ("颈椎病", "M47", "颈椎间盘退行性变", "就诊", "骨科"),
        ("腰椎间盘突出", "M51", "腰椎间盘破裂突出", "就诊", "骨科"),
        ("骨关节炎", "M19", "关节软骨退行性变", "就诊", "骨科"),
        ("湿疹", "L30", "皮肤炎症性瘙痒性疾病", "就诊", "皮肤科"),
        ("荨麻疹", "L50", "皮肤黏膜血管反应性疾病", "就诊", "皮肤科"),
        ("带状疱疹", "B02", "水痘-带状疱疹病毒感染", "就诊", "皮肤科"),
        ("结膜炎", "H10", "结膜炎症", "就诊", "眼科"),
        ("白内障", "H26", "晶状体混浊", "就诊", "眼科"),
        ("中耳炎", "H66", "中耳黏膜炎症", "就诊", "耳鼻喉科"),
        ("扁桃体炎", "J03", "腭扁桃体急性炎症", "就诊", "耳鼻喉科"),
        ("鼻窦炎", "J01", "鼻窦黏膜炎症", "就诊", "耳鼻喉科"),
        ("龋齿", "K02", "牙体硬组织慢性破坏", "就诊", "口腔科"),
        ("牙髓炎", "K04", "牙髓组织炎症", "就诊", "口腔科"),
        ("糖尿病", "E11", "胰岛素分泌或作用缺陷", "就诊", "内分泌科"),
        ("甲状腺功能亢进", "E05", "甲状腺激素分泌过多", "就诊", "内分泌科"),
    ]
    for name, icd, desc, urgency, dep_name in disease_list:
        dis = Disease(
            name=name, icd_code=icd, description=desc,
            urgency=urgency, department_id=depts[dep_name],
        )
        db.add(dis)
        db.flush()
        diseases[name] = dis.id
    print(f"疾病: {len(disease_list)} 个")

    # ========== 症状-疾病关联 ==========
    assoc_list = [
        # 普通感冒
        ("普通感冒", "发热", 0.6, False),
        ("普通感冒", "咳嗽", 0.8, False),
        ("普通感冒", "咳痰", 0.4, False),
        ("普通感冒", "鼻塞", 0.7, False),
        ("普通感冒", "咽痛", 0.6, False),
        ("普通感冒", "打喷嚏", 0.7, False),
        ("普通感冒", "流鼻涕", 0.8, False),
        ("普通感冒", "头痛", 0.5, False),
        ("普通感冒", "乏力", 0.4, False),
        # 流感
        ("流感", "发热", 1.0, True),
        ("流感", "咳嗽", 0.7, False),
        ("流感", "头痛", 0.8, False),
        ("流感", "乏力", 0.9, False),
        ("流感", "肌肉痛", 0.7, False),
        ("流感", "咽痛", 0.5, False),
        ("流感", "流鼻涕", 0.4, False),
        # 肺炎
        ("肺炎", "发热", 0.9, True),
        ("肺炎", "咳嗽", 0.9, True),
        ("肺炎", "咳痰", 0.7, False),
        ("肺炎", "呼吸困难", 0.8, False),
        ("肺炎", "胸痛", 0.5, False),
        ("肺炎", "乏力", 0.6, False),
        # 支气管炎
        ("支气管炎", "咳嗽", 0.9, True),
        ("支气管炎", "咳痰", 0.8, False),
        ("支气管炎", "发热", 0.5, False),
        ("支气管炎", "呼吸困难", 0.4, False),
        ("支气管炎", "胸痛", 0.3, False),
        # COPD
        ("慢性阻塞性肺疾病", "咳嗽", 0.9, True),
        ("慢性阻塞性肺疾病", "咳痰", 0.8, False),
        ("慢性阻塞性肺疾病", "呼吸困难", 0.9, True),
        ("慢性阻塞性肺疾病", "乏力", 0.4, False),
        ("慢性阻塞性肺疾病", "消瘦", 0.3, False),
        # 哮喘
        ("哮喘", "呼吸困难", 0.9, True),
        ("哮喘", "咳嗽", 0.7, False),
        ("哮喘", "胸闷", 0.8, False),
        ("哮喘", "心悸", 0.3, False),
        # 高血压
        ("高血压", "头痛", 0.6, False),
        ("高血压", "头晕", 0.7, False),
        ("高血压", "心悸", 0.5, False),
        ("高血压", "耳鸣", 0.3, False),
        ("高血压", "视力模糊", 0.4, False),
        # 冠心病
        ("冠心病", "胸痛", 0.9, True),
        ("冠心病", "心悸", 0.7, False),
        ("冠心病", "呼吸困难", 0.6, False),
        ("冠心病", "乏力", 0.4, False),
        ("冠心病", "恶心", 0.3, False),
        # 心律失常
        ("心律失常", "心悸", 0.9, True),
        ("心律失常", "胸痛", 0.5, False),
        ("心律失常", "呼吸困难", 0.5, False),
        ("心律失常", "头晕", 0.6, False),
        # 心肌炎
        ("心肌炎", "发热", 0.6, False),
        ("心肌炎", "乏力", 0.8, False),
        ("心肌炎", "胸痛", 0.7, False),
        ("心肌炎", "心悸", 0.8, False),
        ("心肌炎", "呼吸困难", 0.6, False),
        # 胃炎
        ("胃炎", "腹痛", 0.9, True),
        ("胃炎", "腹胀", 0.6, False),
        ("胃炎", "恶心", 0.7, False),
        ("胃炎", "食欲不振", 0.5, False),
        ("胃炎", "呕吐", 0.4, False),
        # 消化性溃疡
        ("消化性溃疡", "腹痛", 0.9, True),
        ("消化性溃疡", "恶心", 0.5, False),
        ("消化性溃疡", "呕吐", 0.4, False),
        ("消化性溃疡", "便血", 0.5, False),
        ("消化性溃疡", "呕血", 0.3, False),
        ("消化性溃疡", "食欲不振", 0.4, False),
        # 急性胃肠炎
        ("急性胃肠炎", "腹痛", 0.8, False),
        ("急性胃肠炎", "腹泻", 0.9, True),
        ("急性胃肠炎", "恶心", 0.7, False),
        ("急性胃肠炎", "呕吐", 0.7, False),
        ("急性胃肠炎", "发热", 0.5, False),
        # 肝硬化
        ("肝硬化", "乏力", 0.7, False),
        ("肝硬化", "食欲不振", 0.6, False),
        ("肝硬化", "腹胀", 0.5, False),
        ("肝硬化", "黄疸", 0.7, False),
        ("肝硬化", "消瘦", 0.5, False),
        ("肝硬化", "水肿", 0.5, False),
        # 胆囊炎
        ("胆囊炎", "腹痛", 0.9, True),
        ("胆囊炎", "发热", 0.6, False),
        ("胆囊炎", "恶心", 0.6, False),
        ("胆囊炎", "呕吐", 0.5, False),
        ("胆囊炎", "黄疸", 0.4, False),
        # 偏头痛
        ("偏头痛", "头痛", 1.0, True),
        ("偏头痛", "恶心", 0.7, False),
        ("偏头痛", "呕吐", 0.6, False),
        ("偏头痛", "畏光", 0.6, False),
        # 脑膜炎
        ("脑膜炎", "发热", 0.9, True),
        ("脑膜炎", "头痛", 0.9, True),
        ("脑膜炎", "呕吐", 0.8, False),
        ("脑膜炎", "颈部僵硬", 0.9, True),
        ("脑膜炎", "意识障碍", 0.6, False),
        ("脑膜炎", "抽搐", 0.5, False),
        # 脑卒中
        ("脑卒中", "头痛", 0.6, False),
        ("脑卒中", "头晕", 0.7, False),
        ("脑卒中", "口眼歪斜", 0.9, True),
        ("脑卒中", "言语不清", 0.8, False),
        ("脑卒中", "肢体麻木", 0.8, False),
        ("脑卒中", "意识障碍", 0.7, False),
        # 面神经麻痹
        ("面神经麻痹", "口眼歪斜", 1.0, True),
        ("面神经麻痹", "耳后痛", 0.5, False),
        # 颈椎病
        ("颈椎病", "颈部僵硬", 0.8, False),
        ("颈椎病", "头痛", 0.5, False),
        ("颈椎病", "头晕", 0.6, False),
        ("颈椎病", "肩痛", 0.6, False),
        ("颈椎病", "肢体麻木", 0.5, False),
        # 腰椎间盘突出
        ("腰椎间盘突出", "腰痛", 0.9, True),
        ("腰椎间盘突出", "肢体麻木", 0.6, False),
        ("腰椎间盘突出", "背痛", 0.4, False),
        # 骨关节炎
        ("骨关节炎", "关节痛", 0.9, True),
        ("骨关节炎", "关节肿胀", 0.6, False),
        # 湿疹
        ("湿疹", "皮疹", 0.9, True),
        ("湿疹", "瘙痒", 0.8, False),
        # 荨麻疹
        ("荨麻疹", "皮疹", 0.9, True),
        ("荨麻疹", "瘙痒", 0.9, False),
        ("荨麻疹", "发热", 0.2, False),
        # 带状疱疹
        ("带状疱疹", "皮疹", 0.9, True),
        ("带状疱疹", "瘙痒", 0.3, False),
        ("带状疱疹", "发热", 0.4, False),
        ("带状疱疹", "乏力", 0.3, False),
        # 结膜炎
        ("结膜炎", "视力模糊", 0.3, False),
        ("结膜炎", "畏光", 0.5, False),
        ("结膜炎", "流泪", 0.6, False),
        # 白内障
        ("白内障", "视力模糊", 0.9, True),
        ("白内障", "畏光", 0.4, False),
        # 中耳炎
        ("中耳炎", "耳痛", 0.9, True),
        ("中耳炎", "耳鸣", 0.6, False),
        ("中耳炎", "发热", 0.5, False),
        # 扁桃体炎
        ("扁桃体炎", "咽痛", 0.9, True),
        ("扁桃体炎", "发热", 0.7, False),
        ("扁桃体炎", "头痛", 0.4, False),
        ("扁桃体炎", "乏力", 0.3, False),
        # 鼻窦炎
        ("鼻窦炎", "鼻塞", 0.8, False),
        ("鼻窦炎", "头痛", 0.7, False),
        ("鼻窦炎", "流鼻涕", 0.8, False),
        ("鼻窦炎", "发热", 0.4, False),
        ("鼻窦炎", "面部压痛", 0.6, False),
        # 龋齿
        ("龋齿", "牙痛", 0.9, True),
        # 牙髓炎
        ("牙髓炎", "牙痛", 1.0, True),
        ("牙髓炎", "发热", 0.3, False),
        # 糖尿病
        ("糖尿病", "多饮", 0.8, False),
        ("糖尿病", "多尿", 0.8, False),
        ("糖尿病", "多食", 0.7, False),
        ("糖尿病", "消瘦", 0.6, False),
        ("糖尿病", "乏力", 0.5, False),
        # 甲亢
        ("甲状腺功能亢进", "多食", 0.7, False),
        ("甲状腺功能亢进", "消瘦", 0.8, False),
        ("甲状腺功能亢进", "心悸", 0.7, False),
        ("甲状腺功能亢进", "多饮", 0.4, False),
        ("甲状腺功能亢进", "乏力", 0.5, False),
    ]
    count = 0
    for disease_name, symptom_name, weight, is_required in assoc_list:
        if disease_name not in diseases or symptom_name not in symptoms:
            continue
        if db.query(SymptomDisease).filter(
            SymptomDisease.symptom_id == symptoms[symptom_name],
            SymptomDisease.disease_id == diseases[disease_name],
        ).first():
            continue
        sd = SymptomDisease(
            symptom_id=symptoms[symptom_name],
            disease_id=diseases[disease_name],
            weight=weight,
            is_required=is_required,
        )
        db.add(sd)
        count += 1
    print(f"症状-疾病关联: {count} 条")

    # ========== 鉴别规则 ==========
    rules = [
        ("发热+头痛+呕吐 - 排除脑膜炎", {
            "symptoms": ["发热", "头痛", "呕吐"],
        }, {"disease_adjust": {"脑膜炎": 0.3, "流感": -0.1, "普通感冒": -0.2}}, 10),
        ("发热+咳嗽+呼吸困难 - 肺炎高危", {
            "symptoms": ["发热", "咳嗽", "呼吸困难"],
        }, {"disease_adjust": {"肺炎": 0.3, "支气管炎": 0.1, "普通感冒": -0.2}}, 9),
        ("发热+头痛+乏力 - 流感高概率", {
            "symptoms": ["发热", "头痛", "乏力"],
        }, {"disease_adjust": {"流感": 0.25, "普通感冒": -0.15}}, 8),
        ("胸痛+心悸 - 心脏疾病偏向", {
            "symptoms": ["胸痛", "心悸"],
        }, {"disease_adjust": {"冠心病": 0.2, "心律失常": 0.15, "心肌炎": 0.1}}, 8),
        ("腹痛+黄疸 - 肝胆疾病偏向", {
            "symptoms": ["腹痛", "黄疸"],
        }, {"disease_adjust": {"胆囊炎": 0.25, "肝硬化": 0.2}}, 7),
        ("头痛剧烈+畏光 - 偏头痛倾向", {
            "symptoms": ["头痛", "畏光"],
        }, {"disease_adjust": {"偏头痛": 0.2, "脑膜炎": -0.1}}, 6),
        ("急性发作+口眼歪斜+言语不清 - 脑卒中", {
            "symptoms": ["口眼歪斜", "言语不清"],
        }, {"disease_adjust": {"脑卒中": 0.35}}, 10),
        ("抽搐+意识障碍 - 神经系统紧急", {
            "symptoms": ["抽搐", "意识障碍"],
        }, {"disease_adjust": {"脑膜炎": 0.2, "脑卒中": 0.2}}, 9),
        ("多饮+多尿+多食+消瘦 - 糖尿病", {
            "symptoms": ["多饮", "多尿"],
        }, {"disease_adjust": {"糖尿病": 0.3}}, 7),
        ("咳嗽持续>咳嗽3周+消瘦 - 结核排查", {
            "symptoms": ["咳嗽", "消瘦"],
            "severity_gte": 0,
        }, {"disease_adjust": {"支气管炎": 0.1}}, 5),
    ]
    for name, condition, result, priority in rules:
        rule = DifferentialRule(name=name, condition_json=condition, result_json=result, priority=priority)
        db.add(rule)
    print(f"鉴别规则: {len(rules)} 条")

    # ========== 医生 ==========
    doctor_list = [
        ("呼吸内科", "张建国", "主任医师", "呼吸系统疾病诊疗30年经验"),
        ("呼吸内科", "李敏", "副主任医师", "擅长哮喘、COPD诊治"),
        ("消化内科", "王志明", "主任医师", "消化内镜诊疗专家"),
        ("消化内科", "赵倩", "主治医师", "胃肠疾病诊治"),
        ("心血管内科", "刘伟", "主任医师", "冠心病介入治疗"),
        ("心血管内科", "陈静", "副主任医师", "高血压、心力衰竭"),
        ("神经内科", "杨芳", "主任医师", "脑血管疾病专家"),
        ("神经内科", "周强", "副主任医师", "头痛、眩晕诊治"),
        ("骨科", "吴刚", "主任医师", "脊柱外科专家"),
        ("骨科", "孙丽", "主治医师", "关节疾病诊治"),
        ("皮肤科", "钱峰", "副主任医师", "皮肤性病科专家"),
        ("皮肤科", "林小红", "主治医师", "湿疹、荨麻疹诊治"),
        ("眼科", "黄明", "主任医师", "白内障手术专家"),
        ("眼科", "何雪", "主治医师", "眼底病诊治"),
        ("耳鼻喉科", "胡兵", "副主任医师", "鼻内镜手术"),
        ("耳鼻喉科", "宋文", "主治医师", "咽喉疾病诊治"),
        ("口腔科", "马丽", "主任医师", "口腔颌面外科"),
        ("口腔科", "罗平", "主治医师", "牙体牙髓病"),
        ("内分泌科", "谢芳", "主任医师", "糖尿病、甲状腺疾病"),
        ("内分泌科", "唐敏", "副主任医师", "内分泌代谢疾病"),
        ("妇产科", "李芳华", "主任医师", "妇产科疾病专家"),
        ("儿科", "王小明", "副主任医师", "儿科疾病诊治"),
        ("急诊科", "赵大勇", "主任医师", "急危重症救治"),
        ("全科医学科", "孙丽华", "主治医师", "全科医学综合诊疗"),
    ]
    for dep_name, name, title, intro in doctor_list:
        doctor = Doctor(name=name, title=title, department_id=depts[dep_name], introduction=intro)
        db.add(doctor)
    print(f"医生: {len(doctor_list)} 个")

    db.commit()
    db.close()
    print("=" * 40)
    print("种子数据初始化完成！")


def seed_users():
    db = SessionLocal()

    existing = db.query(User).filter(User.username == "admin").first()
    if existing:
        print("用户账号已存在，跳过")
        db.close()
        return

    doctors = db.query(Doctor).all()
    doctor_map = {}
    for d in doctors:
        dep_name = d.department.name
        if dep_name not in doctor_map:
            doctor_map[dep_name] = d.id

    doctor_accounts = [
        ("呼吸内科", "doctor_respiratory"),
        ("消化内科", "doctor_digestive"),
        ("心血管内科", "doctor_cardio"),
        ("神经内科", "doctor_neuro"),
        ("内分泌科", "doctor_endocrine"),
        ("骨科", "doctor_ortho"),
        ("皮肤科", "doctor_derm"),
        ("眼科", "doctor_eye"),
        ("耳鼻喉科", "doctor_ent"),
        ("口腔科", "doctor_oral"),
        ("妇产科", "doctor_obgyn"),
        ("儿科", "doctor_ped"),
        ("急诊科", "doctor_emergency"),
        ("全科医学科", "doctor_general"),
    ]

    users = [
        ("admin", "admin123", "admin", None),
        ("patient1", "patient123", "patient", None),
    ]

    for dep_name, username in doctor_accounts:
        did = doctor_map.get(dep_name)
        if did:
            pwd = username.split("_")[1][:4] + "123"
            users.append((username, pwd, "doctor", did))

    for username, pwd, role, doctor_id in users:
        hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
        db.add(User(username=username, password=hashed, role=role, doctor_id=doctor_id))

    db.commit()
    db.close()
    print(f"用户账号: {len(users)} 个已创建")


if __name__ == "__main__":
    seed()
    seed_users()
