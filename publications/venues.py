from datetime import date
from typing import Any

from publications.base import Entity, not_empty, to_int
from publications.exceptions import ValidationError


class Venue(Entity):
    """Место публикации: журнал или конференция."""

    COLLECTION = "venues"
    EDITABLE = ("name",)

    def __init__(self, name: str, obj_id: int = 0) -> None:
        super().__init__(obj_id)
        self.name = name

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = not_empty(value, "name")

    def __str__(self) -> str:
        return f"[{self.id}] {self.name}"


class Journal(Venue):
    TYPE = "journal"
    EDITABLE = Venue.EDITABLE + ("issn", "quartile")
    QUARTILES = ("Q1", "Q2", "Q3", "Q4", "-")

    def __init__(self, name: str, issn: str, quartile: str = "-", obj_id: int = 0) -> None:
        super().__init__(name, obj_id)
        self.issn = issn
        self.quartile = quartile

    @property
    def issn(self) -> str:
        return self._issn

    @issn.setter
    def issn(self, value: str) -> None:
        value = not_empty(value, "issn")
        # ISSN выглядит как 1234-567X
        if len(value) != 9 or value[4] != "-":
            raise ValidationError("issn", "формат должен быть XXXX-XXXX")
        self._issn = value.upper()

    @property
    def quartile(self) -> str:
        return self._quartile

    @quartile.setter
    def quartile(self, value: str) -> None:
        value = (value or "-").strip().upper()
        if value not in self.QUARTILES:
            raise ValidationError("quartile", f"допустимо: {', '.join(self.QUARTILES)}")
        self._quartile = value

    def __str__(self) -> str:
        return f"{super().__str__()} (журнал, ISSN {self.issn}, {self.quartile})"

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.TYPE, "name": self.name,
                "issn": self.issn, "quartile": self.quartile}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Journal":
        return cls(data["name"], data["issn"], data.get("quartile", "-"), data["id"])


class Conference(Venue):
    TYPE = "conference"
    EDITABLE = Venue.EDITABLE + ("city", "year")

    def __init__(self, name: str, city: str, year: int, obj_id: int = 0) -> None:
        super().__init__(name, obj_id)
        self.city = city
        self.year = year

    @property
    def city(self) -> str:
        return self._city

    @city.setter
    def city(self, value: str) -> None:
        self._city = not_empty(value, "city")

    @property
    def year(self) -> int:
        return self._year

    @year.setter
    def year(self, value: int) -> None:
        value = to_int(value, "year")
        # конференцию можно анонсировать на год вперёд, не больше
        if not 1900 <= value <= date.today().year + 1:
            raise ValidationError("year", f"странный год конференции: {value}")
        self._year = value

    def __str__(self) -> str:
        return f"{super().__str__()} (конференция, {self.city}, {self.year})"

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.TYPE, "name": self.name,
                "city": self.city, "year": self.year}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Conference":
        return cls(data["name"], data["city"], data["year"], data["id"])
