import time
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.database import engine, Base, SessionLocal
from app.api import auth, consultation, doctor, admin
from app.config import settings
from app.logger import logger

# 全局限流器：默认 200 req/min per IP
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


async def _session_cleanup_loop():
    """后台任务：每小时清理超过24小时的未完成会话"""
    from app.models.consultation_session import ConsultationSession, SessionStatus
    while True:
        await asyncio.sleep(3600)  # 每小时执行一次
        db = SessionLocal()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            stale = (
                db.query(ConsultationSession)
                .filter(
                    ConsultationSession.updated_at < cutoff,
                    ConsultationSession.status.in_([
                        SessionStatus.INITIAL,
                        SessionStatus.QUESTIONING,
                        SessionStatus.RECOMMENDING,
                        SessionStatus.BOOKING,
                    ])
                )
                .all()
            )
            if stale:
                for s in stale:
                    s.status = SessionStatus.CANCELLED
                db.commit()
                logger.info("会话清理: %d 个过期会话已取消", len(stale))
        except Exception as e:
            db.rollback()
            logger.warning("会话清理异常: %s", e)
        finally:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("正在初始化数据库表...")
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表初始化完成")
    cleanup_task = asyncio.create_task(_session_cleanup_loop())
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("服务关闭")


app = FastAPI(title="智能预问诊系统", version="1.0.0", lifespan=lifespan)

# 绑定 slowapi 状态到 app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    body = await request.body()
    # 日志脱敏：隐藏请求体中的敏感字段（密码、token 等）
    safe_body = ""
    if body:
        try:
            import json as _json
            payload = _json.loads(body)
            for key in ("password", "access_token", "token", "secret"):
                if key in payload:
                    payload[key] = "***"
            safe_body = _json.dumps(payload, ensure_ascii=False)
        except Exception:
            safe_body = f"<binary:{len(body)}b>"
    logger.debug(">>> %s %s | body=%s", request.method, request.url.path, safe_body)
    response = await call_next(request)
    cost = round((time.time() - start) * 1000)
    logger.info("<<< %s %s | status=%d | %dms", request.method, request.url.path, response.status_code, cost)
    return response


app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(consultation.router, prefix="/api/consultation", tags=["预问诊"])
app.include_router(doctor.router, prefix="/api/doctor", tags=["医生端"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理端"])
