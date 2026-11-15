import json
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from publications.catalog import COLLECTIONS, PublicationCatalog
from publications.exceptions import PublicationError, StorageError


class Storage(ABC):
    """Общий интерфейс хранилища: сохранить каталог в файл и прочитать обратно."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def save(self, catalog: PublicationCatalog) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._write(catalog.to_dict())
        except OSError as error:
            # PermissionError, нет места на диске и т.п.
            raise StorageError(f"Не удалось записать {self.path}: {error}") from error

    def load(self) -> PublicationCatalog:
        if not self.path.exists():
            raise StorageError(f"Файл {self.path} не найден")
        try:
            data = self._read()
            return PublicationCatalog.from_dict(data)
        except StorageError:
            raise
        except PublicationError as error:
            # файл читается, но данные внутри неправильные
            raise StorageError(f"В файле {self.path.name} плохие данные: {error}") from error
        except (KeyError, TypeError, AttributeError) as error:
            raise StorageError(f"В файле {self.path.name} нарушена структура ({error})") from error
        except OSError as error:
            raise StorageError(f"Не удалось прочитать {self.path}: {error}") from error

    @abstractmethod
    def _write(self, data: dict[str, Any]) -> None:
        ...

    @abstractmethod
    def _read(self) -> dict[str, Any]:
        ...


class JsonStorage(Storage):
    def _write(self, data: dict[str, Any]) -> None:
        with open(self.path, "w", encoding="utf-8") as file:
            # ensure_ascii=False - чтобы русские буквы не превращались в а...
            json.dump(data, file, ensure_ascii=False, indent=2)

    def _read(self) -> dict[str, Any]:
        try:
            with open(self.path, encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError as error:
            raise StorageError(f"Битый JSON: строка {error.lineno}, {error.msg}") from error


class XmlStorage(Storage):
    """Структура файла:

    <catalog>
      <people>
        <author id="1">
          <full_name>...</full_name>
          ...
        </author>
      </people>
      ...
    </catalog>

    Тег объекта = его тип, id - атрибут. Списки (авторы, ключевые слова)
    помечаются атрибутом list="true", элементы внутри - теги <item>.
    """

    def _write(self, data: dict[str, Any]) -> None:
        root = ET.Element("catalog")
        for collection, items in data.items():
            coll_el = ET.SubElement(root, collection)
            for item in items:
                obj_el = ET.SubElement(coll_el, item["type"], id=str(item["id"]))
                for key, value in item.items():
                    if key in ("id", "type"):
                        continue
                    field_el = ET.SubElement(obj_el, key)
                    if isinstance(value, list):
                        field_el.set("list", "true")
                        for element in value:
                            ET.SubElement(field_el, "item").text = str(element)
                    else:
                        field_el.text = str(value)
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")  # красивые отступы, есть с Python 3.9
        tree.write(self.path, encoding="utf-8", xml_declaration=True)

    def _read(self) -> dict[str, Any]:
        try:
            root = ET.parse(self.path).getroot()
        except ET.ParseError as error:
            raise StorageError(f"Битый XML: {error}") from error
        if root.tag != "catalog":
            raise StorageError(f"Ожидался корневой тег <catalog>, а там <{root.tag}>")

        data: dict[str, Any] = {}
        for collection in COLLECTIONS:
            coll_el = root.find(collection)
            data[collection] = [] if coll_el is None else [
                self._element_to_dict(obj_el) for obj_el in coll_el
            ]
        return data

    @staticmethod
    def _element_to_dict(obj_el: ET.Element) -> dict[str, Any]:
        item: dict[str, Any] = {"type": obj_el.tag, "id": obj_el.get("id")}
        for field_el in obj_el:
            if field_el.get("list") == "true":
                item[field_el.tag] = [sub.text or "" for sub in field_el]
            else:
                # всё в XML - строки; в числа их переведут сеттеры классов
                item[field_el.tag] = field_el.text or ""
        return item
