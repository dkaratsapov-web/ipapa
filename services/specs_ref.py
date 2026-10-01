"""Справочник характеристик устройств — reference/specs.yaml.

Файл читается людьми и правится руками: раздел -> модель -> «подпись: значение».
Модель в каталоге находится по очищенному названию товара (clean_model):
регистр, бренд впереди («Apple», «Google», «Xiaomi»…) и слова вроде «Retina» не важны.
Дополнительные написания — в поле «Другие названия».
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import yaml

from services.images import clean_model

log = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "reference" / "specs.yaml"
ALIASES = "Другие названия"
SOURCE = "Источник"
_DROP = {"apple", "google", "xiaomi", "samsung", "galaxy", "sony", "retina"}


def normalize(model: str) -> str:
    """«Apple MacBook Pro Retina 14 M2 Pro» и «macbook pro 14 m2 pro» -> один ключ."""
    s = model.lower().replace("type-c", "usb-c").replace("ё", "е")
    tokens = re.findall(r"[a-z]+|\d+", s)
    return " ".join(t for t in tokens if t not in _DROP)


class SpecsBook:
    def __init__(self, path: str | os.PathLike | None = None):
        self.path = Path(path or DEFAULT_PATH)
        self._mtime = -1.0
        self._index: dict[str, tuple[str, list[list[str]], str]] = {}

    def _load(self) -> None:
        try:
            mtime = self.path.stat().st_mtime
        except FileNotFoundError:
            self._index, self._mtime = {}, -1.0
            return
        if mtime == self._mtime:
            return
        data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        index: dict[str, tuple[str, list[list[str]], str]] = {}
        for section, models in data.items():
            for model, fields in (models or {}).items():
                if not isinstance(fields, dict):
                    continue
                specs = [[str(k), str(v).strip()] for k, v in fields.items()
                         if k not in (ALIASES, SOURCE) and v not in (None, "")]
                if not specs:
                    continue  # заготовка без данных
                entry = (str(model), specs, str(fields.get(SOURCE) or ""))
                for name in [model, *(fields.get(ALIASES) or [])]:
                    key = normalize(str(name))
                    if key in index and index[key][0] != entry[0]:
                        log.warning("Справочник: «%s» совпадает с «%s»", name, index[key][0])
                    index[key] = entry
        self._index, self._mtime = index, mtime
        log.info("Справочник характеристик: %d моделей", len({e[0] for e in index.values()}))

    def find(self, product_name: str) -> tuple[str, list[list[str]], str] | None:
        """(модель, [[подпись, значение]], источник) по названию товара."""
        self._load()
        return self._index.get(normalize(clean_model(product_name)))

    def models(self) -> set[str]:
        self._load()
        return {e[0] for e in self._index.values()}


book = SpecsBook()
