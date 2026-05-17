from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


# PostgreSQL 연결을 위한 SQLAlchemy engine입니다.
# 아직 API 흐름에는 연결하지 않고, 다음 단계의 repository 구현에서 사용합니다.
engine = create_engine(settings.database_url, pool_pre_ping=True)

# 요청 단위 DB 세션을 만들기 위한 factory입니다.
# FastAPI dependency로 연결하면 API handler에서 안전하게 세션을 주입받을 수 있습니다.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db_session() -> Session:
    """FastAPI dependency로 사용할 DB session generator입니다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
