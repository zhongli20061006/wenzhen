from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.schemas.auth import LoginRequest, TokenResponse
from app.models.user import User
from app.logger import logger

router = APIRouter()
security = HTTPBearer()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        doctor_id = payload.get("doctor_id")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
        return {"username": username, "role": role, "doctor_id": doctor_id}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")


def require_role(required_role: str):
    def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] != required_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
        return current_user
    return role_checker


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not _verify_password(req.password, user.password):
        logger.warning("登录失败: username=%s", req.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    token = create_access_token({"sub": user.username, "role": user.role, "doctor_id": user.doctor_id})
    logger.info("登录成功: username=%s, role=%s, doctor_id=%s", req.username, user.role, user.doctor_id)
    return TokenResponse(access_token=token, role=user.role)


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == current_user["username"]).first()
    result = {
        "username": current_user["username"],
        "role": current_user["role"],
    }
    if user and user.doctor_id:
        from app.models.doctor import Doctor
        doctor = db.query(Doctor).filter(Doctor.id == user.doctor_id).first()
        if doctor:
            result["doctor"] = {
                "id": doctor.id,
                "name": doctor.name,
                "title": doctor.title,
                "department_id": doctor.department_id,
                "department_name": doctor.department.name if doctor.department else "",
                "introduction": doctor.introduction,
            }
    return result
