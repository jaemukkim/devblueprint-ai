from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """모든 SQLAlchemy ORM 모델이 상속할 공통 Base입니다."""
