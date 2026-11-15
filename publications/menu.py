from typing import Callable

from publications.base import Entity
from publications.catalog import PublicationCatalog
from publications.exceptions import PublicationError
from publications.papers import ConferencePaper, JournalArticle, Monograph, Publication, Review
from publications.people import Author, Editor, Organization, Reviewer
from publications.storage import JsonStorage, Storage, XmlStorage
from publications.venues import Conference, Journal


class ConsoleMenu:
    """Текстовый интерфейс программы."""

    SECTIONS = {
        "1": ("Публикации", "publications"),
        "2": ("Люди (авторы, рецензенты, редакторы)", "people"),
        "3": ("Организации", "organizations"),
        "4": ("Журналы и конференции", "venues"),
        "5": ("Рецензии", "reviews"),
    }

    def __init__(self, catalog: PublicationCatalog, json_path: str, xml_path: str) -> None:
        self.catalog = catalog
        self.json = JsonStorage(json_path)
        self.xml = XmlStorage(xml_path)
        # для каждой коллекции - своя функция создания объекта
        self.creators: dict[str, Callable[[], Entity]] = {
            "publications": self.create_publication,
            "people": self.create_person,
            "organizations": self.create_organization,
            "venues": self.create_venue,
            "reviews": self.create_review,
        }

    def run(self) -> None:
        print("=== Каталог научных публикаций ===")
        while True:
            print()
            for key, (title, _) in self.SECTIONS.items():
                print(f"{key}. {title}")
            print("6. Поиск публикаций")
            print("7. Сохранить в JSON и XML")
            print("8. Загрузить из JSON")
            print("9. Загрузить из XML")
            print("0. Выход")
            try:
                choice = input("> ").strip()
                if choice == "0":
                    print("Пока!")
                    break
                self.handle(choice)
            except PublicationError as error:
                # наши ошибки - показываем и продолжаем работу
                print(f"Ошибка: {error}")
            except (KeyboardInterrupt, EOFError):
                print("\nВыход по Ctrl+C")
                break

    def handle(self, choice: str) -> None:
        if choice in self.SECTIONS:
            self.section_menu(*self.SECTIONS[choice])
        elif choice == "6":
            self.search()
        elif choice == "7":
            self.save_all()
        elif choice == "8":
            self.load_from(self.json)
        elif choice == "9":
            self.load_from(self.xml)
        else:
            print("Нет такого пункта")

    # ---------- меню раздела (CRUD) ----------
    def section_menu(self, title: str, collection: str) -> None:
        while True:
            print(f"\n--- {title} ---")
            print("1. Показать все\n2. Добавить\n3. Изменить\n4. Удалить")
            if collection == "publications":
                print("5. Библиографическая ссылка")
            print("0. Назад")
            choice = input("> ").strip()
            if choice == "0":
                return
            try:
                if choice == "1":
                    self.show_all(collection)
                elif choice == "2":
                    obj = self.catalog.add(self.creators[collection]())
                    print(f"Добавлено: {obj}")
                elif choice == "3":
                    self.edit(collection)
                elif choice == "4":
                    obj = self.catalog.remove(collection, ask_int("id для удаления: "))
                    print(f"Удалено: {obj}")
                elif choice == "5" and collection == "publications":
                    pub = self.catalog.get(collection, ask_int("id публикации: "))
                    print(self.catalog.citation(pub))
                else:
                    print("Нет такого пункта")
            except PublicationError as error:
                # ошибка в одном действии не должна выкидывать из раздела
                print(f"Ошибка: {error}")

    def show_all(self, collection: str) -> None:
        items = self.catalog.all(collection)
        if not items:
            print("Пусто")
        for item in items:
            line = str(item)
            if isinstance(item, Publication):
                avg = self.catalog.average_score(item.id)
                if avg is not None:
                    line += f", средняя оценка {avg:.1f}"
            print(line)

    def edit(self, collection: str) -> None:
        obj = self.catalog.get(collection, ask_int("id: "))
        print("Сейчас:")
        for key, value in obj.to_dict().items():
            print(f"  {key}: {value}")
        field = ask("Какое поле меняем? ", options=obj.EDITABLE)
        value = ask("Новое значение (списки - через запятую): ")
        print(f"Изменено: {self.catalog.update(collection, obj.id, {field: value})}")

    # ---------- создание объектов ----------
    def create_publication(self) -> Publication:
        kind = ask("Вид (article / paper / monograph): ",
                   options=("article", "paper", "monograph"))
        common = {
            "title": ask("Название: "),
            "year": ask_int("Год: "),
            "author_ids": ask("id авторов через запятую: "),
            "keywords": ask("Ключевые слова через запятую: "),
            "doi": ask("DOI (можно пусто): "),
        }
        if kind == "article":
            return JournalArticle(journal_id=ask_int("id журнала: "),
                                  volume=ask_int("Том: "), issue=ask_int("Номер: "),
                                  pages=ask("Страницы (например 10-18): "), **common)
        if kind == "paper":
            return ConferencePaper(conference_id=ask_int("id конференции: "),
                                   pages=ask("Страницы: "), **common)
        return Monograph(publisher=ask("Издательство: "),
                         page_count=ask_int("Количество страниц: "),
                         isbn=ask("ISBN (можно пусто): "), **common)

    def create_person(self) -> Author | Reviewer | Editor:
        kind = ask("Кто (author / reviewer / editor): ",
                   options=("author", "reviewer", "editor"))
        name = ask("ФИО: ")
        email = ask("Почта (можно пусто): ")
        if kind == "author":
            return Author(name, email, ask_int("id организации (0 - нет): "),
                          ask_int("Индекс Хирша: "))
        if kind == "reviewer":
            return Reviewer(name, email, ask("Специализация: "))
        return Editor(name, email, ask_int("id журнала: "))

    def create_organization(self) -> Organization:
        return Organization(ask("Название: "), ask("Город: "))

    def create_venue(self) -> Journal | Conference:
        kind = ask("Что (journal / conference): ", options=("journal", "conference"))
        name = ask("Название: ")
        if kind == "journal":
            return Journal(name, ask("ISSN: "), ask("Квартиль (Q1-Q4 или -): "))
        return Conference(name, ask("Город: "), ask_int("Год: "))

    def create_review(self) -> Review:
        return Review(ask_int("id публикации: "), ask_int("id рецензента: "),
                      ask_int("Оценка 1-10: "),
                      ask("Решение (принять / доработать / отклонить): "),
                      ask("Комментарий: "))

    # ---------- прочее ----------
    def search(self) -> None:
        found = self.catalog.search(ask("Что ищем (слово из названия или ключевое слово): "))
        print(f"Найдено: {len(found)}")
        for pub in found:
            print(pub)

    def save_all(self) -> None:
        self.json.save(self.catalog)
        self.xml.save(self.catalog)
        print(f"Сохранено в {self.json.path} и {self.xml.path}")

    def load_from(self, storage: Storage) -> None:
        # если файл битый, load() кинет StorageError и старый каталог останется
        self.catalog = storage.load()
        print(f"Загружено из {storage.path}: {self.catalog.count()}")


# ---------- функции ввода ----------

def ask(prompt: str, options: tuple[str, ...] = ()) -> str:
    """Спрашивает строку. Если заданы варианты - пока не введут один из них."""
    while True:
        answer = input(prompt).strip()
        if not options or answer in options:
            return answer
        print(f"Нужно одно из: {', '.join(options)}")


def ask_int(prompt: str) -> int:
    """Спрашивает число, пока не введут нормальное."""
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            # встроенное исключение: ввели буквы вместо числа
            print("Это не число, попробуйте ещё раз")
