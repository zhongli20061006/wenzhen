"""Debug T5/T6 keyword matching"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models.symptom_dict import SymptomDict

db = SessionLocal()

# Check symptom id=21
s21 = db.query(SymptomDict).filter(SymptomDict.id == 21).first()
if s21:
    print(f"id=21: name=[{s21.name}] aliases=[{s21.aliases}]")

# T5 keyword test
text = "手臂上起了很多红疹，特别痒。有好几天了，擦了皮炎平也没用。"
from app.services.symptom_extractor import match_keywords
results = match_keywords(text, db)
print(f"\nT5 matched: {len(results)} results")
for r in results:
    print(f"  name={r['symptom_name']} id={r['symptom_id']} type={r['match_type']} conf={r['confidence']}")

# Check aliases for 瘙痒
pruritus = db.query(SymptomDict).filter(SymptomDict.name == "瘙痒").first()
if pruritus:
    print(f"\n瘙痒: id={pruritus.id}, aliases=[{pruritus.aliases}]")
    for alias in pruritus.aliases.split(","):
        a = alias.strip()
        print(f"  alias [{a}] in text? {a in text}")
else:
    print("\n瘙痒: NOT IN DB")

# T6: check 体重下降
weight = db.query(SymptomDict).filter(SymptomDict.name == "体重下降").first()
if weight:
    print(f"\n体重下降: id={weight.id}, aliases=[{weight.aliases}]")
else:
    print("\n体重下降: NOT IN DB")

# Check T6 text
text2 = "我最近一个月瘦了10斤，总是口渴想喝水"
results2 = match_keywords(text2, db)
print(f"\nT6 matched: {len(results2)} results")
for r in results2:
    print(f"  name={r['symptom_name']} id={r['symptom_id']} type={r['match_type']} conf={r['confidence']}")

# Full list of all symptom names
all_symptoms = sorted([s.name for s in db.query(SymptomDict).all()])
print(f"\nTotal symptoms in DB: {len(all_symptoms)}")
print(f"Names: {all_symptoms}")

db.close()
