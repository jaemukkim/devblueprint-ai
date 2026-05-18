from abc import ABC, abstractmethod
from copy import deepcopy

from app.core.config import settings
from app.schemas.blueprint import BlueprintResponse


class BlueprintRepository(ABC):
    """설계도 결과 저장소가 지켜야 하는 최소 동작을 정의합니다."""

    @abstractmethod
    def get(self, key: str) -> BlueprintResponse | None:
        """cache key에 해당하는 설계도 결과를 조회합니다."""

    @abstractmethod
    def save(self, key: str, blueprint: BlueprintResponse) -> None:
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

    def save(self, key: str, blueprint: BlueprintResponse) -> None:
        self._items[key] = deepcopy(blueprint)

    def clear(self) -> None:
        self._items.clear()

    def count(self) -> int:
        return len(self._items)


def create_blueprint_repository() -> BlueprintRepository:
    """환경 설정에 맞는 설계도 저장소 구현체를 생성합니다."""
    repository_backend = settings.repository_backend.lower()

    if repository_backend == "memory":
        return InMemoryBlueprintRepository()

    if repository_backend == "postgres":
        raise NotImplementedError("PostgresBlueprintRepository는 다음 단계에서 구현합니다.")

    raise ValueError(f"지원하지 않는 repository backend입니다: {settings.repository_backend}")


blueprint_repository: BlueprintRepository = create_blueprint_repository()
