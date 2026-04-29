from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+pymysql://autoops:autoops123@mysql:3306/autoops"
    SECRET_KEY: str = "change-me-to-a-random-secret-key-32chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ALGORITHM: str = "HS256"
    GITLAB_URL: str = "http://gitlab"
    GITLAB_TOKEN: str = ""
    LOKI_URL: str = "http://loki:3100"
    PROMETHEUS_URL: str = "http://prometheus:9090"

    class Config:
        env_file = ".env"


settings = Settings()
