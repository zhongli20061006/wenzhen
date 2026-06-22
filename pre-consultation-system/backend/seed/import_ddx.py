"""
DDX 知识图谱导入脚本
将 data/ddx_conditions.json + data/ddx_evidences.json 导入到中文知识库。

用法：
    python -m seed.import_ddx [--dry-run] [--translate]

选项：
    --dry-run    只分析不写入
    --translate  使用内置翻译表，否则保留英文原名
"""

import sys, os, json, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal, engine, Base
from app.models.department import Department
from app.models.disease import Disease
from app.models.symptom_dict import SymptomDict, SymptomLevel
from app.models.symptom_disease import SymptomDisease
from app.models.symptom_synonym import SymptomSynonym

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# E_* evidence code → Chinese symptom name mapping
# Covers the most common DDX symptoms
EVIDENCE_CN_MAP = {
    "E_91": "发热",
    "E_55": "疼痛",  # location-dependent
    "E_53": "局部疼痛",
    "E_57": "放射性疼痛",
    "E_54": "急性发作疼痛",
    "E_59": "疼痛加重因素",
    "E_56": "疼痛性质",
    "E_58": "疼痛时间模式",
    "E_66": "呼吸困难",
    "E_220": "胸膜炎性胸痛",
    "E_218": "胸痛",
    "E_14": "出汗",
    "E_151": "下肢水肿",
    "E_127": "流泪",
    "E_181": "流鼻涕",
    "E_176": "乏力",
    "E_210": "吞咽困难",
    "E_211": "吞咽疼痛",
    "E_148": "恶心",
    "E_173": "反酸",
    "E_201": "咳嗽",
    "E_215": "声音嘶哑",
    "E_217": "端坐呼吸",
    "E_140": "早饱感",
    "E_88": "寒战",
    "E_144": "不适感",
    "E_162": "体重下降",
    "E_97": "鼻塞",
    "E_9": "关节痛",
    "E_51": "腹泻",
    "E_133": "呕吐",
    "E_129": "腹痛(右上)",
    "E_130": "腹痛(左上)",
    "E_134": "腹痛(右下)",
    "E_132": "腹痛(左下)",
    "E_136": "腹痛(弥漫)",
    "E_135": "腹痛(脐周)",
    "E_131": "腹痛",
    "E_50": "头晕",
    "E_76": "心悸",
    "E_89": "疲劳",
    "E_154": "面色苍白",
    "E_82": "面部潮红",
    "E_179": "注意力不集中",
    "E_145": "呼吸困难(劳力性)",
    "E_45": "咯血",
    "E_33": "失声",
    "E_212": "声音改变",
    "E_194": "喘鸣",
    "E_30": "腹股沟肿块",
    "E_203": "咳嗽加重",
    "E_221": "腹部隆起",
    "E_150": "便秘",
    "E_65": "复视",
    "E_63": "吞咽困难(液体)",
    "E_52": "眼睑下垂",
    "E_172": "言语困难",
    "E_84": "肢体无力",
    "E_90": "面肌无力",
    "E_38": "颈部无力",
    "E_166": "阵发性咳嗽",
    "E_112": "咳嗽后呕吐",
    "E_42": "皮肤瘙痒",
    "E_159": "心动过速",
    "E_214": "胸闷",
    "E_152": "面部水肿",
    "E_190": "犬吠样咳嗽",
    "E_83": "下肢无力",
    "E_157": "感觉异常",
    "E_93": "平衡障碍",
    "E_156": "步态异常",
    "E_177": "焦虑",
    "E_202": "声音嘶哑(犬吠样)",
    "E_219": "痰量增多",
    "E_155": "胸痛(心前区)",
    "E_16": "濒死感",
    "E_164": "脉搏不规律",
    "E_77": "咳痰",
    "E_170": "喷嚏",
    "E_169": "鼻痒",
    "E_175": "肌肉酸痛",
    "E_174": "头痛",
    "E_92": "面色异常",
    "E_114": "听力下降",
    "E_64": "关节肿胀",
    "E_178": "出血倾向",
    "E_39": "结膜出血",
    "E_75": "过度换气",
    "E_171": "恐惧感",
    "E_111": "现实感丧失",
    "E_128": "颈部痉挛",
    "E_193": "眼动危象",
    "E_205": "舌痉挛",
    "E_192": "张口困难",
    "E_168": "肢体扭转",
    "E_180": "坐立不安",
    "E_67": "全身水肿",
    "E_96": "阴囊水肿",
    "E_206": "面部皮疹",
    "E_13": "胸骨后疼痛",
    "E_94": "全身疼痛",
    "E_161": "盗汗",
    "E_182": "面部疼痛",
    "E_103": "鼻后滴漏",
    "E_32": "喂养困难",
    "E_23": "鼻翼煽动",
    "E_74": "淋巴结肿大",
    "E_43": "皮肤结节",
    "E_163": "食欲不振",
    "E_188": "黄疸",
}

# DDX condition → Chinese department mapping
CONDITION_DEPT_MAP = {
    "Spontaneous pneumothorax": "呼吸内科",
    "Cluster headache": "神经内科",
    "Boerhaave": "急诊科",
    "Spontaneous rib fracture": "骨科",
    "GERD": "消化内科",
    "HIV (initial infection)": "全科医学科",
    "Anemia": "全科医学科",
    "Viral pharyngitis": "耳鼻喉科",
    "Inguinal hernia": "消化内科",
    "Myasthenia gravis": "神经内科",
    "Whooping cough": "呼吸内科",
    "Anaphylaxis": "急诊科",
    "Epiglottitis": "急诊科",
    "Guillain-Barré syndrome": "神经内科",
    "Acute laryngitis": "耳鼻喉科",
    "Croup": "儿科",
    "PSVT": "心血管内科",
    "Atrial fibrillation": "心血管内科",
    "Bronchiectasis": "呼吸内科",
    "Allergic sinusitis": "耳鼻喉科",
    "Chagas": "全科医学科",
    "Scombroid food poisoning": "急诊科",
    "Myocarditis": "心血管内科",
    "Larygospasm": "急诊科",
    "Acute dystonic reactions": "神经内科",
    "Localized edema": "全科医学科",
    "SLE": "全科医学科",
    "Tuberculosis": "呼吸内科",
    "Unstable angina": "心血管内科",
    "Stable angina": "心血管内科",
    "Ebola": "急诊科",
    "Acute otitis media": "耳鼻喉科",
    "Panic attack": "神经内科",
    "Bronchospasm / acute asthma exacerbation": "呼吸内科",
    "Bronchitis": "呼吸内科",
    "Acute COPD exacerbation / infection": "呼吸内科",
    "Pulmonary embolism": "急诊科",
    "URTI": "呼吸内科",
    "Influenza": "呼吸内科",
    "Pneumonia": "呼吸内科",
    "Acute rhinosinusitis": "耳鼻喉科",
    "Chronic rhinosinusitis": "耳鼻喉科",
    "Bronchiolitis": "儿科",
    "Pulmonary neoplasm": "呼吸内科",
    "Possible NSTEMI / STEMI": "心血管内科",
    "Sarcoidosis": "呼吸内科",
    "Pancreatic neoplasm": "消化内科",
    "Acute pulmonary edema": "心血管内科",
    "Pericarditis": "心血管内科",
}

# Urgency mapping from DDX severity (1=most urgent, 5=least)
SEVERITY_URGENCY = {1: "紧急", 2: "紧急", 3: "就诊", 4: "就诊", 5: "就诊"}


def load_ddx():
    with open(os.path.join(DATA_DIR, "ddx_conditions.json"), encoding="utf-8") as f:
        conditions = json.load(f)
    with open(os.path.join(DATA_DIR, "ddx_evidences.json"), encoding="utf-8") as f:
        evidences = json.load(f)
    return conditions, evidences


def analyze(conditions, evidences):
    """Analyze DDX data and report stats."""
    print(f"DDX Conditions: {len(conditions)}")
    print(f"DDX Evidences: {len(evidences)}")
    
    symptom_evidence_ids = set()
    antecedent_ids = set()
    for name, cond in conditions.items():
        for eid in cond.get("symptoms", {}):
            symptom_evidence_ids.add(eid)
        for eid in cond.get("antecedents", {}):
            antecedent_ids.add(eid)
    
    print(f"Unique symptom evidence IDs: {len(symptom_evidence_ids)}")
    print(f"Unique antecedent IDs: {len(antecedent_ids)}")
    print(f"Evidence IDs with CN mapping: {len([e for e in symptom_evidence_ids | antecedent_ids if e in EVIDENCE_CN_MAP])}")
    print(f"Evidence IDs without CN mapping: {len([e for e in symptom_evidence_ids | antecedent_ids if e not in EVIDENCE_CN_MAP])}")
    
    # Show unmapped evidences
    unmapped = sorted([e for e in symptom_evidence_ids | antecedent_ids if e not in EVIDENCE_CN_MAP])
    if unmapped:
        print(f"\nUnmapped evidence codes (sample, max 20):")
        for eid in unmapped[:20]:
            ev = evidences.get(eid, {})
            en_q = ev.get("question_en", "?")
            print(f"  {eid}: {en_q[:80]}")
    
    # Conditions without CN department mapping
    unmapped_dept = [n for n in conditions if n not in CONDITION_DEPT_MAP]
    if unmapped_dept:
        print(f"\nConditions without department mapping: {len(unmapped_dept)}")
        for n in unmapped_dept[:10]:
            print(f"  - {n}")


def import_ddx(dry_run=False, translate=True):
    """Import DDX data into the database."""
    conditions, evidences = load_ddx()
    
    if dry_run:
        analyze(conditions, evidences)
        return
    
    db = SessionLocal()
    try:
        # Ensure base departments exist
        dept_map = {}
        for d in db.query(Department).all():
            dept_map[d.name] = d.id
        
        needed_depts = set(CONDITION_DEPT_MAP.values())
        for dn in needed_depts:
            if dn not in dept_map:
                dep = Department(name=dn)
                db.add(dep)
                db.flush()
                dept_map[dn] = dep.id
                print(f"  + Department: {dn}")
        
        # Get existing symptoms
        existing_symptoms = {s.name: s for s in db.query(SymptomDict).all()}
        existing_diseases = {d.name: d for d in db.query(Disease).all()}
        
        # Collect all needed symptom names
        all_evidence_ids = set()
        for cond in conditions.values():
            for eid in cond.get("symptoms", {}):
                all_evidence_ids.add(eid)
        
        # Create missing symptoms
        new_symptoms = 0
        symptom_id_map = {}  # E_* → symptom_dict.id
        for eid in all_evidence_ids:
            cn_name = EVIDENCE_CN_MAP.get(eid) if translate else None
            if not cn_name:
                ev = evidences.get(eid, {})
                cn_name = ev.get("question_en", eid)[:50]
            
            if cn_name in existing_symptoms:
                symptom_id_map[eid] = existing_symptoms[cn_name].id
            elif cn_name in symptom_id_map:
                continue  # already created
            else:
                sym = SymptomDict(
                    name=cn_name,
                    aliases="",
                    category="DDX导入",
                    level=SymptomLevel.SECONDARY.value,
                )
                db.add(sym)
                db.flush()
                symptom_id_map[eid] = sym.id
                existing_symptoms[cn_name] = sym
                new_symptoms += 1
        
        print(f"New symptoms created: {new_symptoms}")
        
        # Create missing diseases and associations
        new_diseases = 0
        new_assocs = 0
        skipped_assocs = 0
        
        for cond_name, cond in conditions.items():
            if translate:
                # Use condition name as-is (mostly English medical terms)
                disease_name = cond_name
            else:
                disease_name = cond_name
            
            # Determine department
            dep_name = CONDITION_DEPT_MAP.get(cond_name, "全科医学科")
            dep_id = dept_map.get(dep_name)
            if not dep_id:
                dep_id = dept_map.get("全科医学科")
            
            # Determine urgency
            severity = cond.get("severity", 3)
            urgency = SEVERITY_URGENCY.get(severity, "就诊")
            
            # Create disease if not exists
            if disease_name in existing_diseases:
                disease = existing_diseases[disease_name]
            else:
                icd = cond.get("icd10-id", "")
                # Check if ICD code already used by another disease
                existing_icd = db.query(Disease).filter(Disease.icd_code == icd[:10]).first() if icd else None
                if existing_icd:
                    print(f"  Skip {disease_name}: ICD {icd[:10]} already used by '{existing_icd.name}'")
                    existing_diseases[disease_name] = existing_icd
                    disease = existing_icd
                else:
                    desc = cond.get("cond-name-eng", disease_name)
                    disease = Disease(
                        name=disease_name,
                        icd_code=icd[:10] if icd else "",
                        description=desc,
                        urgency=urgency,
                        department_id=dep_id,
                    )
                    db.add(disease)
                    db.flush()
                    existing_diseases[disease_name] = disease
                    new_diseases += 1
            
            # Create symptom-disease associations
            symptom_eids = list(cond.get("symptoms", {}).keys())
            for eid in symptom_eids:
                sym_id = symptom_id_map.get(eid)
                if not sym_id:
                    skipped_assocs += 1
                    continue
                
                # Check if association already exists
                existing = db.query(SymptomDisease).filter(
                    SymptomDisease.disease_id == disease.id,
                    SymptomDisease.symptom_id == sym_id,
                ).first()
                if existing:
                    continue
                
                assoc = SymptomDisease(
                    disease_id=disease.id,
                    symptom_id=sym_id,
                    weight=0.5,
                    is_required=False,
                    is_discriminative=False,
                )
                db.add(assoc)
                new_assocs += 1
        
        if not dry_run:
            db.commit()
        
        print(f"New diseases created: {new_diseases}")
        print(f"New symptom-disease associations: {new_assocs}")
        print(f"Skipped (no mapping): {skipped_assocs}")
        print(f"Total diseases in DB: {db.query(Disease).count()}")
        print(f"Total symptoms in DB: {db.query(SymptomDict).count()}")
        print(f"Total associations in DB: {db.query(SymptomDisease).count()}")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Import DDX knowledge graph")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only, do not write")
    parser.add_argument("--translate", action="store_true", default=True, help="Use Chinese translation (default)")
    parser.add_argument("--no-translate", dest="translate", action="store_false", help="Keep English names")
    args = parser.parse_args()
    
    conditions, evidences = load_ddx()
    
    if args.dry_run:
        print("=== DRY RUN: Analysis Only ===\n")
        analyze(conditions, evidences)
        print("\nRun without --dry-run to import.")
    else:
        print("=== Importing DDX Knowledge Graph ===\n")
        import_ddx(dry_run=False, translate=args.translate)
        print("\nDone.")


if __name__ == "__main__":
    main()
