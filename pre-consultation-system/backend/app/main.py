import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.api import auth, consultation, doctor, admin
from app.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("正在初始化数据库表...")
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表初始化完成")
    yield
    logger.info("服务关闭")


app = FastAPI(title="智能预问诊系统", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    body = await request.body()
    logger.debug(">>> %s %s | body=%s", request.method, request.url.path, body.decode() if body else "")
    response = await call_next(request)
    cost = round((time.time() - start) * 1000)
    logger.info("<<< %s %s | status=%d | %dms", request.method, request.url.path, response.status_code, cost)
    return response


app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(consultation.router, prefix="/api/consultation", tags=["预问诊"])
app.include_router(doctor.router, prefix="/api/doctor", tags=["医生端"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理端"])
