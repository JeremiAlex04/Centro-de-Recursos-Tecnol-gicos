"""Carga y busqueda del catalogo de herramientas."""

from __future__ import annotations

import os
import sys
import unicodedata
from pathlib import Path
from typing import Optional

import yaml
from pydantic import ValidationError

from recursos.models import Category, Risk, Tool


class CatalogError(Exception):
    pass


def default_catalog_dir() -> Path:
    env = os.environ.get("RECURSOS_CATALOG")
    if env:
        return Path(env)
    # PyInstaller bundle: sys._MEIPASS
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass and (Path(meipass) / "catalog").is_dir():
        return Path(meipass) / "catalog"
    # Entorno de desarrollo: <repo>/catalog
    dev_cat = Path(__file__).resolve().parents[2] / "catalog"
    if dev_cat.is_dir():
        return dev_cat
    # Junto al ejecutable:
    exe_cat = Path(sys.executable).parent / "catalog"
    if exe_cat.is_dir():
        return exe_cat
    return dev_cat


def load_catalog(directory: Optional[Path] = None) -> list[Tool]:
    directory = directory or default_catalog_dir()
    if not directory.is_dir():
        raise CatalogError(f"No existe el directorio de catalogo: {directory}")

    tools: list[Tool] = []
    seen: dict[str, Path] = {}
    for file in sorted(directory.rglob("*.yaml")):
        try:
            data = yaml.safe_load(file.read_text(encoding="utf-8"))
            tool = Tool.model_validate(data)
        except (yaml.YAMLError, ValidationError) as exc:
            raise CatalogError(f"{file.name}: {exc}") from exc
        if tool.id in seen:
            raise CatalogError(f"id duplicado '{tool.id}' en {file.name} y {seen[tool.id].name}")
        seen[tool.id] = file
        tools.append(tool)
    return tools


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def filter_tools(
    tools: list[Tool],
    category: Optional[Category] = None,
    risk: Optional[Risk] = None,
    tag: Optional[str] = None,
) -> list[Tool]:
    result = tools
    if category:
        result = [t for t in result if t.category is category]
    if risk:
        result = [t for t in result if t.risk is risk]
    if tag:
        n = _norm(tag)
        result = [t for t in result if any(_norm(x) == n for x in t.tags)]
    return result


def search(tools: list[Tool], query: str) -> list[Tool]:
    """Busqueda por palabras (todas deben aparecer) en nombre, resumen, tags y sintomas."""
    words = _norm(query).split()
    scored: list[tuple[int, Tool]] = []
    for t in tools:
        fields = {
            3: _norm(t.name + " " + t.id),
            2: _norm(" ".join(t.tags + t.symptoms)),
            1: _norm(t.summary + " " + t.context),
        }
        if not all(any(w in text for text in fields.values()) for w in words):
            continue
        score = sum(weight for w in words for weight, text in fields.items() if w in text)
        scored.append((score, t))
    scored.sort(key=lambda p: (-p[0], p[1].name))
    return [t for _, t in scored]


def get_tool(tools: list[Tool], tool_id: str) -> Optional[Tool]:
    n = _norm(tool_id)
    exact = [t for t in tools if t.id == n]
    if exact:
        return exact[0]
    partial = [t for t in tools if n in t.id]
    return partial[0] if len(partial) == 1 else None
