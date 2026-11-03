"""Rutas, ajustes persistentes y registro de auditoria."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

APP = "recursos-jeremialex04"
GITHUB_REPO = "JeremiAlex04/Centro-de-Recursos-Tecnol-gicos"
# Los archivos grandes de Git LFS se sirven desde este host (se verifica siempre su SHA-256).
LFS_MEDIA_BASE = f"https://media.githubusercontent.com/media/{GITHUB_REPO}/master/"


def data_dir() -> Path:
    env = os.environ.get("RECURSOS_DATA")
    if env:
        base = Path(env)
    else:
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / APP
    return base


def cache_dir() -> Path:
    path = data_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def repo_root() -> Optional[Path]:
    """Carpeta que contiene los archivos del repositorio (instaladores), si existe."""
    env = os.environ.get("RECURSOS_HOME")
    if env:
        return Path(env)
    if getattr(sys, "frozen", False):
        return None
    candidate = Path(__file__).resolve().parents[2]
    return candidate if (candidate / "catalog").is_dir() else None


def _settings_file() -> Path:
    return data_dir() / "settings.json"


def load_settings() -> dict:
    try:
        return json.loads(_settings_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(settings: dict) -> None:
    data_dir().mkdir(parents=True, exist_ok=True)
    _settings_file().write_text(json.dumps(settings, indent=2), encoding="utf-8")


def plugin_enabled(name: str) -> bool:
    return bool(load_settings().get("plugins", {}).get(name, False))


def set_plugin(name: str, enabled: bool) -> None:
    settings = load_settings()
    settings.setdefault("plugins", {})[name] = enabled
    save_settings(settings)


def audit(event: dict) -> None:
    """Agrega una linea JSON al registro de auditoria. Nunca interrumpe la operacion."""
    try:
        data_dir().mkdir(parents=True, exist_ok=True)
        event = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **event}
        event["user"] = os.environ.get("USERNAME") or os.environ.get("USER") or "?"
        with (data_dir() / "audit.log").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError:
        pass
