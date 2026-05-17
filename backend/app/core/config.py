from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    use_openai: bool = False
    api_base_url: str = "http://localhost:8000"

    # .env에 프론트엔드용 값이나 아직 코드에서 쓰지 않는 값이 있어도 설정 로딩이 실패하지 않게 합니다.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
