"""
生产部署就绪检查脚本
用法: python startup_check.py
在启动应用前运行，检查所有安全配置是否正确。
"""

import sys, os, secrets
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check():
    issues = []
    warnings = []
    ok = []

    # ---- 数据库 ----
    from app.config import settings

    if not settings.DB_PASSWORD:
        issues.append("[CRITICAL] DB_PASSWORD 为空 — 必须设置数据库密码")
    elif len(settings.DB_PASSWORD) < 8:
        warnings.append("[WARN] DB_PASSWORD 长度不足 8 位")
    else:
        ok.append("[OK] DB_PASSWORD 已设置")

    # ---- JWT ----
    _DEFAULT_JWT = "pre-consultation-secret-key-change-in-production"
    if settings.JWT_SECRET == _DEFAULT_JWT:
        issues.append("[CRITICAL] JWT_SECRET 使用默认值 — 必须替换为随机密钥")
    elif len(settings.JWT_SECRET) < 32:
        warnings.append(f"[WARN] JWT_SECRET 长度仅 {len(settings.JWT_SECRET)} 字符，建议 ≥ 32")
    else:
        ok.append("[OK] JWT_SECRET 已设置强密钥")

    # ---- CORS ----
    cors_origins = settings.CORS_ORIGINS.strip()
    if cors_origins == "*":
        warnings.append("[WARN] CORS_ORIGINS='*' 允许所有来源 — 生产环境请限定域名")
    elif cors_origins:
        ok.append(f"[OK] CORS_ORIGINS 已限定: {cors_origins}")
    else:
        issues.append("[CRITICAL] CORS_ORIGINS 为空 — 将拒绝所有跨域请求")

    # ---- DeepSeek ----
    if settings.DEEPSEEK_API_KEY:
        ok.append("[OK] DEEPSEEK_API_KEY 已设置 — AI 增强可用")
    else:
        warnings.append("[WARN] DEEPSEEK_API_KEY 未设置 — AI 增强不可用（系统降级为规则引擎）")

    # ---- 数据库连接 ----
    try:
        from app.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        ok.append("[OK] 数据库连接正常")
    except Exception as e:
        issues.append(f"[CRITICAL] 数据库连接失败: {e}")

    # ---- 必需的数据表 ----
    try:
        from app.database import SessionLocal
        from app.models.department import Department
        from app.models.disease import Disease
        from app.models.symptom_dict import SymptomDict
        from app.models.user import User
        db = SessionLocal()
        dept_count = db.query(Department).count()
        disease_count = db.query(Disease).count()
        sym_count = db.query(SymptomDict).count()
        user_count = db.query(User).count()
        db.close()

        if dept_count == 0:
            issues.append("[CRITICAL] 科室表为空 — 请运行 python -m seed.seed_data")
        else:
            ok.append(f"[OK] 种子数据就绪: {dept_count}科室, {disease_count}疾病, {sym_count}症状, {user_count}用户")
    except Exception as e:
        issues.append(f"[CRITICAL] 数据表检查失败: {e}")

    # ---- 日志目录 ----
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    if os.path.isdir(log_dir) and os.access(log_dir, os.W_OK):
        ok.append("[OK] 日志目录可写")
    else:
        try:
            os.makedirs(log_dir, exist_ok=True)
            ok.append("[OK] 日志目录已创建")
        except Exception:
            warnings.append("[WARN] 日志目录不可写")

    # ---- NER 模型(可选) ----
    try:
        import torch
        import transformers
        ok.append("[OK] PyTorch + Transformers 已安装 (NER 模型可用)")
    except ImportError:
        warnings.append("[WARN] torch/transformers 未安装 — NER 模型不可用，关键词匹配作为降级方案")

    # ---- 输出报告 ----
    print("=" * 60)
    print("  智能预问诊系统 — 生产就绪检查")
    print("=" * 60)

    if issues:
        print(f"\n[FAIL] 阻断性问题 ({len(issues)}):")
        for i in issues:
            print(f"  {i}")

    if warnings:
        print(f"\n[WARN]  警告 ({len(warnings)}):")
        for w in warnings:
            print(f"  {w}")

    print(f"\n[OK] 通过 ({len(ok)}):")
    for o in ok:
        print(f"  {o}")

    print("\n" + "=" * 60)
    if issues:
        print("[FAIL] 存在阻断性问题，请修复后重试。")
        print("   提示: python -m seed.seed_data 初始化数据库")
        sys.exit(1)
    elif warnings:
        print("[WARN]  检查通过 (有警告)。系统可启动，但建议修复警告。")
    else:
        print("[OK] 全部通过！系统可以安全启动。")
    print("=" * 60)


if __name__ == "__main__":
    check()
