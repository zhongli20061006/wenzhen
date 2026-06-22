import warnings
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    DB_HOST: str = "localhost"
    DB_PORT: int = 3307
    DB_USER: str = "root"
    DB_PASSWORD: str = ""          # ⚠ 必须通过环境变量设置，不再硬编码
    DB_NAME: str = "pre_consultation"

    # ⚠ 生产环境必须通过环境变量 JWT_SECRET 设置自定义密钥
    JWT_SECRET: str = "pre-consultation-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480     # Token 过期时间（分钟），默认 8 小时
    JWT_REFRESH_EXPIRE_DAYS: int = 7  # Refresh Token 过期时间（天）

    # CORS 允许的来源，逗号分隔；生产环境必须限定域名
    CORS_ORIGINS: str = "*"

    MAX_QUESTION_ROUNDS: int = 5
    CANDIDATE_THRESHOLD: int = 3
    DISCRIMINATION_THRESHOLD: float = 0.15

    AI_MODE: str = "degrade"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_ENABLED: bool = True

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"


settings = Settings()

# 警告：使用默认 JWT 密钥（检测到默认值，生产环境必须修改）
_DEFAULT_SECRET = "pre-consultation-secret-key-change-in-production"
if settings.JWT_SECRET == _DEFAULT_SECRET:
    warnings.warn(
        "⚠ 使用默认 JWT_SECRET！生产环境必须通过环境变量设置自定义密钥: set JWT_SECRET=your-random-secret",
        RuntimeWarning,
        stacklevel=2,
    )

# 警告：CORS 允许全部来源（检测到默认值 "*"，生产环境必须限定域名）
if settings.CORS_ORIGINS.strip() == "*":
    warnings.warn(
        "⚠ CORS_ORIGINS 为 '*'（允许所有来源）！生产环境必须限定域名: set CORS_ORIGINS=https://example.com",
        RuntimeWarning,
        stacklevel=2,
    )

# 警告：DB 密码为空（未通过环境变量设置）
if not settings.DB_PASSWORD:
    warnings.warn(
        "⚠ DB_PASSWORD 为空！请通过环境变量设置数据库密码: set DB_PASSWORD=your-db-password",
        RuntimeWarning,
        stacklevel=2,
    )
