from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    use_openai: bool = False
    api_base_url: str = "http://localhost:8000"
    frontend_origins: list[str] = ["http://localhost:8501", "http://localhost:5173"]

    # .env에 아직 코드에서 쓰지 않는 값이 있어도 설정 로딩이 실패하지 않게 합니다.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def split_frontend_origins(cls, value: str | list[str]) -> list[str]:
        """쉼표로 구분한 FRONTEND_ORIGINS 값을 list[str] 형태로 변환합니다."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
