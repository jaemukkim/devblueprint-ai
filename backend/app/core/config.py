from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    use_openai: bool = False
    api_base_url: str = "http://localhost:8000"
    frontend_origins: str = "http://localhost:8501,http://localhost:5173"
    database_url: str = "postgresql+psycopg://devuser:dev1234@localhost:5432/devblueprint"
    repository_backend: str = "memory"

    # .env에 아직 코드에서 쓰지 않는 값이 있어도 설정 로딩이 실패하지 않게 합니다.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def frontend_origin_list(self) -> list[str]:
        """쉼표로 구분한 FRONTEND_ORIGINS 값을 CORS middleware용 list[str]로 변환합니다."""
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


settings = Settings()
