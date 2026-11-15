"""Лабораторная работа №1. Вариант 30 - научные публикации.

Запуск: python main.py
"""
from pathlib import Path

from publications.catalog import PublicationCatalog
from publications.exceptions import StorageError
from publications.menu import ConsoleMenu
from publications.storage import JsonStorage

DATA_DIR = Path(__file__).parent / "data"
JSON_FILE = DATA_DIR / "catalog.json"
XML_FILE = DATA_DIR / "catalog.xml"


def main() -> None:
    # при старте пробуем подтянуть сохранённые данные
    try:
        catalog = JsonStorage(JSON_FILE).load()
        print(f"Загружены данные из {JSON_FILE.name}: {catalog.count()}")
    except StorageError as error:
        print(f"{error}. Начинаем с пустого каталога.")
        catalog = PublicationCatalog()

    ConsoleMenu(catalog, str(JSON_FILE), str(XML_FILE)).run()


if __name__ == "__main__":
    main()
