from abc import abstractmethod
from datetime import date
from typing import Any

from publications.base import Entity, not_empty, to_id_list, to_int, to_list
from publications.exceptions import ValidationError
from publications.venues import Venue


class Publication(Entity):
    """Научная публикация. Сам по себе класс абстрактный -
    создаются только конкретные виды: статья, доклад, монография."""

    COLLECTION = "publications"
    EDITABLE = ("title", "year", "author_ids", "keywords", "doi")
    MIN_YEAR = 1665  # первый научный журнал в истории, раньше точно не надо

    def __init__(self, title: str, year: int, author_ids: list[int],
                 keywords: list[str] | None = None, doi: str = "", obj_id: int = 0) -> None:
        super().__init__(obj_id)
        self.title = title
        self.year = year
        self.author_ids = author_ids
        self.keywords = keywords or []
        self.doi = doi

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = not_empty(value, "title")

    @property
    def year(self) -> int:
        return self._year

    @year.setter
    def year(self, value: int) -> None:
        value = to_int(value, "year")
        if not self.MIN_YEAR <= value <= date.today().year:
            raise ValidationError("year", f"год должен быть от {self.MIN_YEAR} "
                                          f"до {date.today().year}, а не {value}")
        self._year = value

    @property
    def author_ids(self) -> list[int]:
        return self._author_ids

    @author_ids.setter
    def author_ids(self, value: list[int] | str) -> None:
        ids = to_id_list(value, "author_ids")
        if not ids:
            raise ValidationError("author_ids", "у публикации должен быть хотя бы один автор")
        self._author_ids = ids

    @property
    def keywords(self) -> list[str]:
        return self._keywords

    @keywords.setter
    def keywords(self, value: list[str] | str) -> None:
        self._keywords = [word.lower() for word in to_list(value)]

    @property
    def doi(self) -> str:
        return self._doi

    @doi.setter
    def doi(self, value: str) -> None:
        value = (value or "").strip()
        # все DOI начинаются с префикса 10.
        if value and not value.startswith("10."):
            raise ValidationError("doi", "DOI должен начинаться с '10.'")
        self._doi = value

    def kind_name(self) -> str:
        return "публикация"

    @abstractmethod
    def citation(self, authors: list[str], venue: Venue | None) -> str:
        """Библиографическая ссылка (упрощённый ГОСТ).
        У каждого вида публикации она оформляется по-своему."""

    def _doi_part(self) -> str:
        return f" DOI: {self.doi}." if self.doi else ""

    def __str__(self) -> str:
        return f"[{self.id}] {self.title} ({self.year}, {self.kind_name()})"

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.TYPE, "title": self.title,
                "year": self.year, "author_ids": self.author_ids,
                "keywords": self.keywords, "doi": self.doi}

    @staticmethod
    def _common(data: dict[str, Any]) -> dict[str, Any]:
        # общие поля, чтобы не повторять их в каждом from_dict
        return {"title": data["title"], "year": data["year"],
                "author_ids": data["author_ids"], "keywords": data.get("keywords", []),
                "doi": data.get("doi", ""), "obj_id": data["id"]}


class JournalArticle(Publication):
    TYPE = "article"
    EDITABLE = Publication.EDITABLE + ("journal_id", "volume", "issue", "pages")

    def __init__(self, title: str, year: int, author_ids: list[int], journal_id: int,
                 volume: int, issue: int, pages: str, **kwargs: Any) -> None:
        super().__init__(title, year, author_ids, **kwargs)
        self.journal_id = journal_id
        self.volume = volume
        self.issue = issue
        self.pages = pages

    @property
    def journal_id(self) -> int:
        return self._journal_id

    @journal_id.setter
    def journal_id(self, value: int) -> None:
        self._journal_id = to_int(value, "journal_id")

    @property
    def volume(self) -> int:
        return self._volume

    @volume.setter
    def volume(self, value: int) -> None:
        self._volume = to_int(value, "volume")

    @property
    def issue(self) -> int:
        return self._issue

    @issue.setter
    def issue(self, value: int) -> None:
        self._issue = to_int(value, "issue")

    @property
    def pages(self) -> str:
        return self._pages

    @pages.setter
    def pages(self, value: str) -> None:
        self._pages = check_pages(value)

    def kind_name(self) -> str:
        return "статья"

    def citation(self, authors: list[str], venue: Venue | None) -> str:
        journal = venue.name if venue else "?"
        return (f"{', '.join(authors)} {self.title} // {journal}. {self.year}. "
                f"Т. {self.volume}, № {self.issue}. С. {self.pages}.{self._doi_part()}")

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(journal_id=self.journal_id, volume=self.volume,
                    issue=self.issue, pages=self.pages)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JournalArticle":
        return cls(journal_id=data["journal_id"], volume=data["volume"],
                   issue=data["issue"], pages=data["pages"], **cls._common(data))


class ConferencePaper(Publication):
    TYPE = "paper"
    EDITABLE = Publication.EDITABLE + ("conference_id", "pages")

    def __init__(self, title: str, year: int, author_ids: list[int], conference_id: int,
                 pages: str, **kwargs: Any) -> None:
        super().__init__(title, year, author_ids, **kwargs)
        self.conference_id = conference_id
        self.pages = pages

    @property
    def conference_id(self) -> int:
        return self._conference_id

    @conference_id.setter
    def conference_id(self, value: int) -> None:
        self._conference_id = to_int(value, "conference_id")

    @property
    def pages(self) -> str:
        return self._pages

    @pages.setter
    def pages(self, value: str) -> None:
        self._pages = check_pages(value)

    def kind_name(self) -> str:
        return "доклад"

    def citation(self, authors: list[str], venue: Venue | None) -> str:
        conf = f"{venue.name} ({venue.city})" if venue else "?"
        return (f"{', '.join(authors)} {self.title} // Материалы конференции "
                f"«{conf}». {self.year}. С. {self.pages}.{self._doi_part()}")

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(conference_id=self.conference_id, pages=self.pages)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConferencePaper":
        return cls(conference_id=data["conference_id"], pages=data["pages"],
                   **cls._common(data))


class Monograph(Publication):
    TYPE = "monograph"
    EDITABLE = Publication.EDITABLE + ("publisher", "page_count", "isbn")

    def __init__(self, title: str, year: int, author_ids: list[int], publisher: str,
                 page_count: int, isbn: str = "", **kwargs: Any) -> None:
        super().__init__(title, year, author_ids, **kwargs)
        self.publisher = publisher
        self.page_count = page_count
        self.isbn = isbn

    @property
    def publisher(self) -> str:
        return self._publisher

    @publisher.setter
    def publisher(self, value: str) -> None:
        self._publisher = not_empty(value, "publisher")

    @property
    def page_count(self) -> int:
        return self._page_count

    @page_count.setter
    def page_count(self, value: int) -> None:
        value = to_int(value, "page_count")
        if value <= 0:
            raise ValidationError("page_count", "в книге должна быть хоть одна страница")
        self._page_count = value

    @property
    def isbn(self) -> str:
        return self._isbn

    @isbn.setter
    def isbn(self, value: str) -> None:
        value = (value or "").strip()
        digits = value.replace("-", "")
        # ISBN бывает из 10 или 13 цифр (в старом в конце может быть X)
        if value and (len(digits) not in (10, 13) or not digits[:-1].isdigit()):
            raise ValidationError("isbn", "ISBN должен содержать 10 или 13 цифр")
        self._isbn = value

    def kind_name(self) -> str:
        return "монография"

    def citation(self, authors: list[str], venue: Venue | None) -> str:
        # у монографии нет журнала/конференции, venue не нужен
        isbn = f" ISBN {self.isbn}." if self.isbn else ""
        return (f"{', '.join(authors)} {self.title}: монография. - "
                f"{self.publisher}, {self.year}. - {self.page_count} с.{isbn}")

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(publisher=self.publisher, page_count=self.page_count, isbn=self.isbn)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Monograph":
        return cls(publisher=data["publisher"], page_count=data["page_count"],
                   isbn=data.get("isbn", ""), **cls._common(data))


class Review(Entity):
    """Рецензия на публикацию."""

    COLLECTION = "reviews"
    TYPE = "review"
    EDITABLE = ("score", "verdict", "comment")
    VERDICTS = ("принять", "доработать", "отклонить")

    def __init__(self, publication_id: int, reviewer_id: int, score: int,
                 verdict: str, comment: str = "", obj_id: int = 0) -> None:
        super().__init__(obj_id)
        self.publication_id = to_int(publication_id, "publication_id")
        self.reviewer_id = to_int(reviewer_id, "reviewer_id")
        self.score = score
        self.verdict = verdict
        self.comment = comment

    @property
    def score(self) -> int:
        return self._score

    @score.setter
    def score(self, value: int) -> None:
        value = to_int(value, "score")
        if not 1 <= value <= 10:
            raise ValidationError("score", "оценка ставится от 1 до 10")
        self._score = value

    @property
    def verdict(self) -> str:
        return self._verdict

    @verdict.setter
    def verdict(self, value: str) -> None:
        value = (value or "").strip().lower()
        if value not in self.VERDICTS:
            raise ValidationError("verdict", f"варианты: {', '.join(self.VERDICTS)}")
        self._verdict = value

    def __str__(self) -> str:
        return (f"[{self.id}] публикация {self.publication_id}, рецензент "
                f"{self.reviewer_id}: {self.score}/10, {self.verdict}")

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.TYPE, "publication_id": self.publication_id,
                "reviewer_id": self.reviewer_id, "score": self.score,
                "verdict": self.verdict, "comment": self.comment}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Review":
        return cls(data["publication_id"], data["reviewer_id"], data["score"],
                   data["verdict"], data.get("comment", ""), data["id"])


def check_pages(value: str) -> str:
    """Страницы пишутся как '15' или '15-27'."""
    value = not_empty(value, "pages")
    parts = value.split("-")
    if len(parts) > 2 or not all(p.strip().isdigit() for p in parts):
        raise ValidationError("pages", "пример правильного формата: 15-27")
    if len(parts) == 2 and int(parts[0]) > int(parts[1]):
        raise ValidationError("pages", "первая страница больше последней")
    return value.replace(" ", "")
