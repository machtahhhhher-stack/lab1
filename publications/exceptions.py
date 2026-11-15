"""Собственные исключения программы.

Все они наследуются от PublicationError, поэтому в меню их можно
ловить одним except и не бояться, что программа вылетит.
"""


class PublicationError(Exception):
    """Базовое исключение для всей предметной области."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


class ValidationError(PublicationError):
    """Неправильные данные: пустое название, кривой год и т.п."""

    def __init__(self, field: str, message: str) -> None:
        # запоминаем поле, чтобы было понятно, где именно ошибка
        self.field = field
        super().__init__(f"Поле '{field}': {message}")


class NotFoundError(PublicationError):
    """Объект с таким id не найден в каталоге."""

    def __init__(self, kind: str, obj_id: int) -> None:
        self.kind = kind
        self.obj_id = obj_id
        super().__init__(f"Не найден объект '{kind}' с id={obj_id}")


class DuplicateError(PublicationError):
    """Попытка добавить то, что уже есть (например, тот же DOI)."""


class StorageError(PublicationError):
    """Ошибки при чтении/записи файлов JSON и XML."""
