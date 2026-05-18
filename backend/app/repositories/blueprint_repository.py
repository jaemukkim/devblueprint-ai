from abc import ABC, abstractmethod
from collections.abc import Callable
from copy import deepcopy
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.blueprint import BlueprintModel
from app.schemas.blueprint import BlueprintResponse


class BlueprintRepository(ABC):
    """설계도 결과 저장소가 지켜야 하는 최소 동작을 정의합니다."""

    @abstractmethod
    def get(self, key: str) -> BlueprintResponse | None:
        """cache key에 해당하는 설계도 결과를 조회합니다."""

    @abstractmethod
    def save(self, key: str, blueprint: BlueprintResponse, idea: str | None = None) -> None:
        """cache key와 설계도 결과를 저장합니다."""

    @abstractmethod
    def clear(self) -> None:
        """테스트나 개발 중 캐시를 비울 때 사용합니다."""

    @abstractmethod
    def count(self) -> int:
        """현재 저장된 설계도 결과 개수를 반환합니다."""


class InMemoryBlueprintRepository(BlueprintRepository):
    """PostgreSQL 도입 전까지 사용할 서버 메모리 기반 저장소입니다."""

    def __init__(self) -> None:
        self._items: dict[str, BlueprintResponse] = {}

    def get(self, key: str) -> BlueprintResponse | None:
        blueprint = self._items.get(key)
        if blueprint is None:
            return None
        return deepcopy(blueprint)

    def save(self, key: str, blueprint: BlueprintResponse, idea: str | None = None) -> None:
        self._items[key] = deepcopy(blueprint)

    def clear(self) -> None:
        self._items.clear()

    def count(self) -> int:
        return len(self._items)


class PostgresBlueprintRepository(BlueprintRepository):
    """PostgreSQL에 설계도 결과를 저장하고 cache key로 재사용하는 저장소입니다."""

    def __init__(self, session_factory: Callable[[], Session] = SessionLocal) -> None:
        self._session_factory = session_factory

    def get(self, key: str) -> BlueprintResponse | None:
        with self._session_factory() as db:
            blueprint_model = db.scalar(select(BlueprintModel).where(BlueprintModel.cache_key == key))

            if blueprint_model is None:
                return None

            return BlueprintResponse.model_validate(blueprint_model.result)

    def save(self, key: str, blueprint: BlueprintResponse, idea: str | None = None) -> None:
        with self._session_factory() as db:
            blueprint_model = db.scalar(select(BlueprintModel).where(BlueprintModel.cache_key == key))
            result = blueprint.model_dump(mode="json")

            if blueprint_model is None:
                blueprint_model = BlueprintModel(
                    id=str(uuid4()),
                    cache_key=key,
                    idea=idea or key,
                    result=result,
                )
                db.add(blueprint_model)
            else:
                blueprint_model.idea = idea or blueprint_model.idea
                blueprint_model.result = result

            db.commit()

    def clear(self) -> None:
        with self._session_factory() as db:
            db.execute(delete(BlueprintModel))
            db.commit()

    def count(self) -> int:
        with self._session_factory() as db:
            return db.scalar(select(func.count()).select_from(BlueprintModel)) or 0


def create_blueprint_repository() -> BlueprintRepository:
    """환경 설정에 맞는 설계도 저장소 구현체를 생성합니다."""
    repository_backend = settings.repository_backend.lower()

    if repository_backend == "memory":
        return InMemoryBlueprintRepository()

    if repository_backend == "postgres":
        return PostgresBlueprintRepository()

    raise ValueError(f"지원하지 않는 repository backend입니다: {settings.repository_backend}")


blueprint_repository: BlueprintRepository = create_blueprint_repository()
