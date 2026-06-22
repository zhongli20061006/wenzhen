"""T5/T6 verification — writes results to file to avoid console encoding issues"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models.symptom_dict import SymptomDict
from app.services.symptom_extractor import match_keywords
from app.services.extraction_service import extract_symptoms

out = []
def log(s):
    out.append(s)
    print(s)

db = SessionLocal()

# ── DB inspection ──
log("=== All Symptoms ===")
for s in db.query(SymptomDict).order_by(SymptomDict.id).all():
    log(f"  id={s.id:3d}  name='{s.name}'  aliases='{s.aliases}'")

# ── T5: 红疹 + 瘙痒 ──
text5 = "手臂上起了很多红疹，特别痒。有好几天了，擦了皮炎平也没用。"
log(f"\n=== T5 ===")
log(f"Text: {text5}")
results5 = extract_symptoms(text5, db)
names5 = [r.get('symptom_name', '?') for r in results5]
log(f"Extracted: {names5}")
log(f"Expected:  ['红疹', '瘙痒']")
log(f"RESULT: {'PASS' if '红疹' in names5 and '瘙痒' in names5 else 'FAIL'}")

# ── T6: 体重下降 + 多饮 ──
text6 = "我最近一个月瘦了10斤，总是口渴想喝水"
log(f"\n=== T6 ===")
log(f"Text: {text6}")
results6 = extract_symptoms(text6, db)
names6 = [r.get('symptom_name', '?') for r in results6]
log(f"Extracted: {names6}")
log(f"Expected:  ['体重下降', '多饮']")
log(f"RESULT: {'PASS' if '体重下降' in names6 and '多饮' in names6 else 'FAIL'}")

# ── T5 keyword-level debug ──
log(f"\n=== T5 Keyword Debug ===")
kw5 = match_keywords(text5, db)
for r in kw5:
    log(f"  kw: name='{r['symptom_name']}' type={r['match_type']} conf={r['confidence']}")

# ── Missing check ──
for name in ["瘙痒", "体重下降"]:
    sym = db.query(SymptomDict).filter(SymptomDict.name == name).first()
    log(f"\nDB lookup '{name}': {'FOUND id='+str(sym.id)+' aliases='+str(sym.aliases) if sym else 'NOT FOUND'}")

# Write to file
with open(os.path.join(os.path.dirname(__file__), 'verify_t56_result.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

db.close()
