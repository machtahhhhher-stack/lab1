from typing import Any

from publications.base import Entity
from publications.exceptions import DuplicateError, NotFoundError, PublicationError
from publications.papers import ConferencePaper, JournalArticle, Monograph, Publication, Review
from publications.people import Author, Editor, Organization, Person, Reviewer
from publications.venues import Conference, Journal, Venue

# какие классы бывают в файле: значение поля "type" -> класс
TYPES: dict[str, type[Entity]] = {
    cls.TYPE: cls for cls in (Organization, Author, Reviewer, Editor, Journal, Conference,
                              JournalArticle, ConferencePaper, Monograph, Review)
}

# порядок важен: при загрузке сначала то, на что ссылаются другие
# (редактор ссылается на журнал, статья - на авторов, рецензия - на статью)
COLLECTIONS = ("organizations", "venues", "people", "publications", "reviews")


class PublicationCatalog:
    """Каталог - хранит все объекты и умеет CRUD
    (create, read, update, delete) над ними."""

    def __init__(self) -> None:
        # для каждой коллекции свой словарь {id: объект}
        self._items: dict[str, dict[int, Entity]] = {name: {} for name in COLLECTIONS}
        self._next_id: dict[str, int] = {name: 1 for name in COLLECTIONS}

    # ---------- CREATE ----------
    def add(self, obj: Entity) -> Entity:
        self._check_links(obj)
        self._check_duplicates(obj)
        collection = obj.COLLECTION
        if obj.id == 0:
            # новый объект - выдаём ему следующий свободный id
            obj.id = self._next_id[collection]
        elif obj.id in self._items[collection]:
            raise DuplicateError(f"В '{collection}' уже есть объект с id={obj.id}")
        self._items[collection][obj.id] = obj
        self._next_id[collection] = max(self._next_id[collection], obj.id + 1)
        return obj

    # ---------- READ ----------
    def get(self, collection: str, obj_id: int) -> Entity:
        try:
            return self._items[collection][obj_id]
        except KeyError:
            raise NotFoundError(collection, obj_id) from None

    def all(self, collection: str, cls: type[Entity] | None = None) -> list[Entity]:
        """Все объекты коллекции, можно отфильтровать по классу."""
        items = list(self._items[collection].values())
        if cls is not None:
            items = [item for item in items if isinstance(item, cls)]
        return items

    def search(self, text: str) -> list[Publication]:
        """Поиск публикаций по названию и ключевым словам."""
        text = text.lower().strip()
        return [pub for pub in self.all("publications")
                if text in pub.title.lower() or text in pub.keywords]

    def publications_of(self, author_id: int) -> list[Publication]:
        self.get("people", author_id)  # если автора нет - будет NotFoundError
        return [pub for pub in self.all("publications") if author_id in pub.author_ids]

    def citation(self, pub: Publication) -> str:
        authors = [self.get("people", a_id).short_name() for a_id in pub.author_ids]
        venue = None
        if isinstance(pub, JournalArticle):
            venue = self.get("venues", pub.journal_id)
        elif isinstance(pub, ConferencePaper):
            venue = self.get("venues", pub.conference_id)
        return pub.citation(authors, venue)

    def average_score(self, publication_id: int) -> float | None:
        scores = [r.score for r in self.all("reviews") if r.publication_id == publication_id]
        return sum(scores) / len(scores) if scores else None

    # ---------- UPDATE ----------
    def update(self, collection: str, obj_id: int, changes: dict[str, Any]) -> Entity:
        obj = self.get(collection, obj_id)
        backup = obj.to_dict()
        try:
            obj.update(changes)
            self._check_links(obj)
        except PublicationError:
            # если что-то пошло не так - откатываем объект обратно
            self._items[collection][obj_id] = type(obj).from_dict(backup)
            raise
        return obj

    # ---------- DELETE ----------
    def remove(self, collection: str, obj_id: int) -> Entity:
        obj = self.get(collection, obj_id)
        users = self._used_by(obj)
        if users:
            names = ", ".join(str(u) for u in users[:3])
            raise PublicationError(f"Нельзя удалить {obj}: на него ссылаются {names}")
        return self._items[collection].pop(obj_id)

    def clear(self) -> None:
        self.__init__()

    def count(self) -> dict[str, int]:
        return {name: len(items) for name, items in self._items.items()}

    # ---------- проверки ----------
    def _check_links(self, obj: Entity) -> None:
        """Проверяем, что все id, на которые ссылается объект, существуют
        и указывают на объект нужного типа."""
        links: list[tuple[str, int, type[Entity]]] = []
        if isinstance(obj, Publication):
            links += [("people", a_id, Author) for a_id in obj.author_ids]
        if isinstance(obj, JournalArticle):
            links.append(("venues", obj.journal_id, Journal))
        elif isinstance(obj, ConferencePaper):
            links.append(("venues", obj.conference_id, Conference))
        elif isinstance(obj, Author) and obj.organization_id:
            links.append(("organizations", obj.organization_id, Organization))
        elif isinstance(obj, Editor) and obj.journal_id:
            links.append(("venues", obj.journal_id, Journal))
        elif isinstance(obj, Review):
            links.append(("publications", obj.publication_id, Publication))
            links.append(("people", obj.reviewer_id, Reviewer))

        for collection, obj_id, cls in links:
            target = self.get(collection, obj_id)
            if not isinstance(target, cls):
                raise PublicationError(f"id={obj_id} - это {target}, а нужен {cls.__name__}")

    def _check_duplicates(self, obj: Entity) -> None:
        for other in self.all(obj.COLLECTION):
            if other.id == obj.id:
                continue
            if isinstance(obj, Publication) and obj.doi and obj.doi == other.doi:
                raise DuplicateError(f"Публикация с DOI {obj.doi} уже есть: {other}")
            if isinstance(obj, Person) and obj.email and obj.email == other.email:
                raise DuplicateError(f"Почта {obj.email} уже занята: {other}")
            if isinstance(obj, Journal) and isinstance(other, Journal) and obj.issn == other.issn:
                raise DuplicateError(f"Журнал с ISSN {obj.issn} уже есть: {other}")

    def _used_by(self, obj: Entity) -> list[Entity]:
        """Кто ссылается на этот объект (чтобы не удалить нужное)."""
        result: list[Entity] = []
        for collection in COLLECTIONS:
            for other in self.all(collection):
                if (obj.COLLECTION, obj.id) in self._refs(other):
                    result.append(other)
        return result

    @staticmethod
    def _refs(obj: Entity) -> list[tuple[str, int]]:
        """Список ссылок объекта в виде пар (коллекция, id)."""
        refs: list[tuple[str, int]] = []
        if isinstance(obj, Publication):
            refs += [("people", a_id) for a_id in obj.author_ids]
        for attr, collection in (("journal_id", "venues"), ("conference_id", "venues"),
                                 ("organization_id", "organizations"),
                                 ("publication_id", "publications"),
                                 ("reviewer_id", "people")):
            if hasattr(obj, attr):
                refs.append((collection, getattr(obj, attr)))
        return refs

    # ---------- для сохранения ----------
    def to_dict(self) -> dict[str, list[dict[str, Any]]]:
        return {name: [obj.to_dict() for obj in items.values()]
                for name, items in self._items.items()}

    @classmethod
    def from_dict(cls, data: dict[str, list[dict[str, Any]]]) -> "PublicationCatalog":
        catalog = cls()
        for collection in COLLECTIONS:
            for item in data.get(collection, []):
                type_name = item.get("type")
                if type_name not in TYPES:
                    raise PublicationError(f"Неизвестный тип объекта: '{type_name}'")
                catalog.add(TYPES[type_name].from_dict(item))
        return catalog
