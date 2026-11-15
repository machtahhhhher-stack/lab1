from typing import Any

from publications.base import Entity, not_empty, to_int
from publications.exceptions import ValidationError


class Organization(Entity):
    """Организация (вуз, институт), где работают авторы."""

    COLLECTION = "organizations"
    TYPE = "organization"
    EDITABLE = ("name", "city")

    def __init__(self, name: str, city: str, obj_id: int = 0) -> None:
        super().__init__(obj_id)
        self.name = name
        self.city = city

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = not_empty(value, "name")

    @property
    def city(self) -> str:
        return self._city

    @city.setter
    def city(self, value: str) -> None:
        self._city = not_empty(value, "city")

    def __str__(self) -> str:
        return f"[{self.id}] {self.name} ({self.city})"

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.TYPE, "name": self.name, "city": self.city}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Organization":
        return cls(data["name"], data["city"], data["id"])


class Person(Entity):
    """Человек: базовый класс для автора, рецензента и редактора."""

    COLLECTION = "people"
    EDITABLE = ("full_name", "email")

    def __init__(self, full_name: str, email: str = "", obj_id: int = 0) -> None:
        super().__init__(obj_id)
        self.full_name = full_name
        self.email = email

    @property
    def full_name(self) -> str:
        return self._full_name

    @full_name.setter
    def full_name(self, value: str) -> None:
        self._full_name = not_empty(value, "full_name")

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        value = (value or "").strip()
        # почта необязательна, но если есть - должна быть похожа на почту
        if value and ("@" not in value or "." not in value.split("@")[-1]):
            raise ValidationError("email", f"'{value}' не похоже на адрес почты")
        self._email = value

    def short_name(self) -> str:
        """'Иванов Иван Иванович' -> 'Иванов И. И.' (для ссылок по ГОСТ)."""
        parts = self.full_name.split()
        initials = " ".join(p[0] + "." for p in parts[1:])
        return f"{parts[0]} {initials}".strip()

    def role(self) -> str:
        # переопределяется в наследниках (полиморфизм)
        return "человек"

    def __str__(self) -> str:
        return f"[{self.id}] {self.full_name} - {self.role()}"

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.TYPE,
                "full_name": self.full_name, "email": self.email}


class Author(Person):
    TYPE = "author"
    EDITABLE = Person.EDITABLE + ("organization_id", "h_index")

    def __init__(self, full_name: str, email: str = "", organization_id: int = 0,
                 h_index: int = 0, obj_id: int = 0) -> None:
        super().__init__(full_name, email, obj_id)
        self.organization_id = organization_id
        self.h_index = h_index

    @property
    def organization_id(self) -> int:
        return self._organization_id

    @organization_id.setter
    def organization_id(self, value: int) -> None:
        self._organization_id = to_int(value, "organization_id")

    @property
    def h_index(self) -> int:
        return self._h_index

    @h_index.setter
    def h_index(self, value: int) -> None:
        value = to_int(value, "h_index")
        if value < 0:
            raise ValidationError("h_index", "индекс Хирша не бывает отрицательным")
        self._h_index = value

    def role(self) -> str:
        return f"автор (h-index {self.h_index})"

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(organization_id=self.organization_id, h_index=self.h_index)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Author":
        return cls(data["full_name"], data.get("email", ""),
                   data.get("organization_id", 0), data.get("h_index", 0), data["id"])


class Reviewer(Person):
    TYPE = "reviewer"
    EDITABLE = Person.EDITABLE + ("specialization",)

    def __init__(self, full_name: str, email: str = "", specialization: str = "",
                 obj_id: int = 0) -> None:
        super().__init__(full_name, email, obj_id)
        self.specialization = specialization

    @property
    def specialization(self) -> str:
        return self._specialization

    @specialization.setter
    def specialization(self, value: str) -> None:
        self._specialization = not_empty(value, "specialization")

    def role(self) -> str:
        return f"рецензент ({self.specialization})"

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["specialization"] = self.specialization
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Reviewer":
        return cls(data["full_name"], data.get("email", ""),
                   data["specialization"], data["id"])


class Editor(Person):
    TYPE = "editor"
    EDITABLE = Person.EDITABLE + ("journal_id",)

    def __init__(self, full_name: str, email: str = "", journal_id: int = 0,
                 obj_id: int = 0) -> None:
        super().__init__(full_name, email, obj_id)
        self.journal_id = journal_id

    @property
    def journal_id(self) -> int:
        return self._journal_id

    @journal_id.setter
    def journal_id(self, value: int) -> None:
        self._journal_id = to_int(value, "journal_id")

    def role(self) -> str:
        return "редактор журнала"

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["journal_id"] = self.journal_id
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Editor":
        return cls(data["full_name"], data.get("email", ""),
                   data.get("journal_id", 0), data["id"])
