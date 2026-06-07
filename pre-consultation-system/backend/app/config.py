from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 3307
    DB_USER: str = "root"
    DB_PASSWORD: str = "20061006"
    DB_NAME: str = "pre_consultation"

    JWT_SECRET: str = "pre-consultation-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

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
