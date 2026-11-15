from abc import ABC, abstractmethod
from typing import Any

from publications.exceptions import ValidationError


class Entity(ABC):
    """Общий предок для всего, что хранится в каталоге.

    У каждого объекта есть id, его можно превратить в словарь
    (для JSON/XML) и обновить отдельные поля.
    """

    # в какую коллекцию каталога кладём объект и как он называется в файле
    COLLECTION: str = ""
    TYPE: str = ""
    # поля, которые разрешено менять через меню
    EDITABLE: tuple[str, ...] = ()

    def __init__(self, obj_id: int = 0) -> None:
        self.id = obj_id

    @property
    def id(self) -> int:
        return self._id

    @id.setter
    def id(self, value: int) -> None:
        self._id = to_int(value, "id")

    def update(self, changes: dict[str, Any]) -> None:
        """Меняет поля объекта. Проверки делают сеттеры свойств."""
        for field, value in changes.items():
            if field not in self.EDITABLE:
                raise ValidationError(field, "это поле нельзя изменить")
            setattr(self, field, value)

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Словарь для сохранения в файл."""

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, Any]) -> "Entity":
        """Обратное действие - собрать объект из словаря."""


# --- вспомогательные функции для проверки данных ---

def to_int(value: Any, field: str) -> int:
    """Приводит значение к int, иначе кидает ValidationError."""
    try:
        return int(value)
    except (TypeError, ValueError):
        # встроенную ошибку заменяем своей, с понятным текстом
        raise ValidationError(field, f"ожидалось целое число, получено '{value}'") from None


def not_empty(value: Any, field: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise ValidationError(field, "не может быть пустым")
    return text


def to_list(value: Any) -> list[str]:
    """Из строки 'a, b, c' делает список ['a', 'b', 'c']."""
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [str(item) for item in value]


def to_id_list(value: Any, field: str) -> list[int]:
    return [to_int(item, field) for item in to_list(value)]
