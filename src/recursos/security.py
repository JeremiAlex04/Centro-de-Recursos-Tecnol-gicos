"""Verificacion de integridad, privilegios y confirmaciones segun el riesgo."""

from __future__ import annotations

import hashlib
import os
import sys
import urllib.request
from pathlib import Path

import typer
from rich.console import Console

from recursos.models import Risk, Tool


class SecurityError(Exception):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sha256(path: Path, expected: str) -> bool:
    return sha256_file(path).lower() == expected.lower()


def is_admin() -> bool:
    if sys.platform == "win32":
        import ctypes

        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    return hasattr(os, "geteuid") and os.geteuid() == 0


def download(url: str, dest: Path, console: Console, timeout: int = 60) -> None:
    """Descarga solo por HTTPS, con barra de progreso simple."""
    if not url.startswith("https://"):
        raise SecurityError(f"Solo se permite HTTPS: {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "recursos-jeremialex04"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, tmp.open("wb") as out:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if total:
                    console.print(f"  descargando {done * 100 // total:3d}%", end="\r")
        tmp.replace(dest)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    console.print(" " * 30, end="\r")


def confirm_risk(tool: Tool, assume_yes: bool, console: Console) -> bool:
    """low: sin preguntar. medium: [s/N] (--yes lo omite). high: escribir el id (--yes NO lo omite)."""
    if tool.risk is Risk.low:
        return True
    if tool.risk is Risk.medium:
        if assume_yes:
            return True
        return typer.confirm("Esta herramienta modifica el sistema. Continuar?", default=False)
    console.print("[bold red]RIESGO ALTO.[/] Puede borrar datos, ser detectada como malware o tener implicaciones legales.")
    typed = typer.prompt(f"Escribe '{tool.id}' para continuar (otra cosa cancela)", default="", show_default=False)
    return typed.strip() == tool.id
