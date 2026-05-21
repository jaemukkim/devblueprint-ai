from abc import ABC, abstractmethod
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.blueprint import BlueprintModel
from app.schemas.blueprint import BlueprintResponse


@dataclass
class StoredBlueprint:
    """저장된 설계도 결과와 조회용 메타데이터를 함께 담는 내부 모델입니다."""

    id: str
    idea: str
    revision_instruction: str | None
    result: BlueprintResponse
    created_at: datetime


class BlueprintRepository(ABC):
    """설계도 결과 저장소가 지켜야 하는 최소 동작을 정의합니다."""

    @abstractmethod
    def get(self, key: str) -> BlueprintResponse | None:
        """cache key에 해당하는 설계도 결과를 조회합니다."""

    @abstractmethod
    def get_stored_by_key(self, key: str) -> StoredBlueprint | None:
        """cache key에 해당하는 저장 설계도의 메타데이터와 결과를 함께 조회합니다."""

    @abstractmethod
    def save(
        self,
        key: str,
        blueprint: BlueprintResponse,
        idea: str | None = None,
        revision_instruction: str | None = None,
    ) -> StoredBlueprint:
        """cache key와 설계도 결과를 저장합니다."""

    @abstractmethod
    def get_by_id(self, blueprint_id: str) -> StoredBlueprint | None:
        """저장된 설계도 ID로 상세 결과를 조회합니다."""

    @abstractmethod
    def list_recent(self, limit: int = 20) -> list[StoredBlueprint]:
        """최근 생성된 설계도 목록을 최신순으로 조회합니다."""

    @abstractmethod
    def delete_by_id(self, blueprint_id: str) -> bool:
        """저장된 설계도 ID로 결과를 삭제하고 성공 여부를 반환합니다."""

    @abstractmethod
    def clear(self) -> None:
        """테스트나 개발 중 캐시를 비울 때 사용합니다."""

    @abstractmethod
    def count(self) -> int:
        """현재 저장된 설계도 결과 개수를 반환합니다."""


class InMemoryBlueprintRepository(BlueprintRepository):
    """PostgreSQL 도입 전까지 사용할 서버 메모리 기반 저장소입니다."""

    def __init__(self) -> None:
        self._items: dict[str, StoredBlueprint] = {}

    def get(self, key: str) -> BlueprintResponse | None:
        stored_blueprint = self._items.get(key)
        if stored_blueprint is None:
            return None
        return deepcopy(stored_blueprint.result)

    def get_stored_by_key(self, key: str) -> StoredBlueprint | None:
        stored_blueprint = self._items.get(key)
        if stored_blueprint is None:
            return None
        return deepcopy(stored_blueprint)

    def save(
        self,
        key: str,
        blueprint: BlueprintResponse,
        idea: str | None = None,
        revision_instruction: str | None = None,
    ) -> StoredBlueprint:
        stored_blueprint = self._items.get(key)

        if stored_blueprint is None:
            stored_blueprint = StoredBlueprint(
                id=str(uuid4()),
                idea=idea or key,
                revision_instruction=revision_instruction,
                result=deepcopy(blueprint),
                created_at=datetime.now(timezone.utc),
            )
            self._items[key] = stored_blueprint
            return deepcopy(stored_blueprint)

        stored_blueprint.idea = idea or stored_blueprint.idea
        stored_blueprint.revision_instruction = revision_instruction
        stored_blueprint.result = deepcopy(blueprint)
        return deepcopy(stored_blueprint)

    def get_by_id(self, blueprint_id: str) -> StoredBlueprint | None:
        for stored_blueprint in self._items.values():
            if stored_blueprint.id == blueprint_id:
                return deepcopy(stored_blueprint)
        return None

    def list_recent(self, limit: int = 20) -> list[StoredBlueprint]:
        stored_blueprints = sorted(
            self._items.values(),
            key=lambda stored_blueprint: stored_blueprint.created_at,
            reverse=True,
        )
        return deepcopy(stored_blueprints[:limit])

    def delete_by_id(self, blueprint_id: str) -> bool:
        for key, stored_blueprint in list(self._items.items()):
            if stored_blueprint.id == blueprint_id:
                del self._items[key]
                return True

        return False

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

    def get_stored_by_key(self, key: str) -> StoredBlueprint | None:
        with self._session_factory() as db:
            blueprint_model = db.scalar(select(BlueprintModel).where(BlueprintModel.cache_key == key))

            if blueprint_model is None:
                return None

            return self._to_stored_blueprint(blueprint_model)

    def get_by_id(self, blueprint_id: str) -> StoredBlueprint | None:
        if not is_valid_uuid(blueprint_id):
            return None

        with self._session_factory() as db:
            blueprint_model = db.get(BlueprintModel, blueprint_id)

            if blueprint_model is None:
                return None

            return self._to_stored_blueprint(blueprint_model)

    def list_recent(self, limit: int = 20) -> list[StoredBlueprint]:
        with self._session_factory() as db:
            blueprint_models = db.scalars(
                select(BlueprintModel).order_by(BlueprintModel.created_at.desc()).limit(limit)
            ).all()

            return [self._to_stored_blueprint(blueprint_model) for blueprint_model in blueprint_models]

    def delete_by_id(self, blueprint_id: str) -> bool:
        if not is_valid_uuid(blueprint_id):
            return False

        with self._session_factory() as db:
            blueprint_model = db.get(BlueprintModel, blueprint_id)

            if blueprint_model is None:
                return False

            db.delete(blueprint_model)
            db.commit()
            return True

    def save(
        self,
        key: str,
        blueprint: BlueprintResponse,
        idea: str | None = None,
        revision_instruction: str | None = None,
    ) -> StoredBlueprint:
        with self._session_factory() as db:
            blueprint_model = db.scalar(select(BlueprintModel).where(BlueprintModel.cache_key == key))
            result = blueprint.model_dump(mode="json")

            if blueprint_model is None:
                blueprint_model = BlueprintModel(
                    id=str(uuid4()),
                    cache_key=key,
                    idea=idea or key,
                    revision_instruction=revision_instruction,
                    result=result,
                )
                db.add(blueprint_model)
            else:
                blueprint_model.idea = idea or blueprint_model.idea
                blueprint_model.revision_instruction = revision_instruction
                blueprint_model.result = result

            db.commit()
            db.refresh(blueprint_model)
            return self._to_stored_blueprint(blueprint_model)

    def clear(self) -> None:
        with self._session_factory() as db:
            db.execute(delete(BlueprintModel))
            db.commit()

    def count(self) -> int:
        with self._session_factory() as db:
            return db.scalar(select(func.count()).select_from(BlueprintModel)) or 0

    def _to_stored_blueprint(self, blueprint_model: BlueprintModel) -> StoredBlueprint:
        """ORM 모델을 API 응답 생성에 쓰기 쉬운 내부 모델로 변환합니다."""
        return StoredBlueprint(
            id=blueprint_model.id,
            idea=blueprint_model.idea,
            revision_instruction=blueprint_model.revision_instruction,
            result=BlueprintResponse.model_validate(blueprint_model.result),
            created_at=blueprint_model.created_at,
        )


def create_blueprint_repository() -> BlueprintRepository:
    """환경 설정에 맞는 설계도 저장소 구현체를 생성합니다."""
    repository_backend = settings.repository_backend.lower()

    if repository_backend == "memory":
        return InMemoryBlueprintRepository()

    if repository_backend == "postgres":
        return PostgresBlueprintRepository()

    raise ValueError(f"지원하지 않는 repository backend입니다: {settings.repository_backend}")


def is_valid_uuid(value: str) -> bool:
    """문자열이 PostgreSQL UUID 컬럼에 안전하게 전달될 수 있는지 확인합니다."""
    try:
        UUID(value)
    except ValueError:
        return False

    return True


blueprint_repository: BlueprintRepository = create_blueprint_repository()
