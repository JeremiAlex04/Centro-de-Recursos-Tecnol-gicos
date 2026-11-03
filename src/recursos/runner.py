"""Ejecutores: llevan a cabo cada tipo de herramienta con las salvaguardas de seguridad."""

from __future__ import annotations

import os
import subprocess
import sys
import urllib.parse
import webbrowser
from pathlib import Path

from rich.console import Console

from recursos import config
from recursos.models import Category, SourceType, Tool
from recursos.security import (
    SecurityError,
    confirm_risk,
    download,
    is_admin,
    sha256_file,
    verify_sha256,
)

INSTALLABLE = {SourceType.local_file, SourceType.url, SourceType.script}


class RunError(Exception):
    pass


def _announce(tool: Tool, console: Console) -> None:
    console.print(f"[bold]{tool.name}[/bold]  [dim]({tool.source.type.value}, riesgo {tool.risk.value})[/dim]")
    for w in tool.warnings:
        console.print(f"  [yellow]! {w}[/yellow]")


def _resolve_local_file(tool: Tool, console: Console, dry_run: bool) -> Path:
    src = tool.source
    root = config.repo_root()
    if root and (root / src.path).is_file():
        path = root / src.path
    else:
        url = config.LFS_MEDIA_BASE + urllib.parse.quote(src.path.replace("\\", "/"))
        path = config.cache_dir() / Path(src.path).name
        if dry_run:
            console.print(f"  [dim](dry-run) se descargaria de {url}[/dim]")
            return path
        if not path.is_file() or not verify_sha256(path, src.sha256):
            console.print(f"  Archivo no disponible localmente; descargando de GitHub ({src.path})")
            try:
                download(url, path, console, timeout=120)
            except Exception as exc:
                raise RunError(f"No se pudo descargar el archivo: {exc}") from exc
    if dry_run:
        return path
    console.print("  Verificando SHA-256...")
    if not verify_sha256(path, src.sha256):
        if path.parent == config.cache_dir():
            path.unlink(missing_ok=True)
        raise SecurityError(
            f"El SHA-256 NO coincide para {path.name}. Esperado {src.sha256.lower()}, "
            f"obtenido {sha256_file(path)}. Ejecucion abortada."
        )
    console.print("  [green]Hash correcto[/green]")
    return path


def _launch_file(path: Path) -> None:
    if sys.platform != "win32":
        raise RunError("Lanzar archivos solo esta soportado en Windows.")
    if path.suffix.lower() in (".exe", ".msi", ".bat", ".cmd"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:  # zip, rar...: mostrar el archivo en el Explorador
        subprocess.Popen(["explorer", f"/select,{path}"])


def _run_local_file(tool: Tool, console: Console, dry_run: bool) -> None:
    path = _resolve_local_file(tool, console, dry_run)
    if dry_run:
        console.print(f"  [dim](dry-run) se lanzaria {path}[/dim]")
        return
    console.print(f"  Lanzando {path.name}")
    _launch_file(path)


def _run_url(tool: Tool, console: Console, dry_run: bool) -> None:
    console.print(f"  Abriendo {tool.source.url}")
    if not dry_run:
        webbrowser.open(tool.source.url)


def _run_script(tool: Tool, console: Console, dry_run: bool, assume_yes: bool) -> None:
    import typer

    url = tool.source.url
    if dry_run:
        console.print(f"  [dim](dry-run) se descargaria {url}, se mostraria su hash y se ejecutaria con PowerShell[/dim]")
        return
    dest = config.cache_dir() / f"{tool.id}.ps1"
    try:
        download(url, dest, console)
    except Exception as exc:
        raise RunError(f"No se pudo descargar el script: {exc}") from exc
    digest = sha256_file(dest)
    text = dest.read_text(encoding="utf-8", errors="replace")
    console.print(f"  Origen : {url}")
    console.print(f"  Tamano : {dest.stat().st_size} bytes   SHA-256: {digest}")
    console.print("  [dim]--- primeras lineas ---[/dim]")
    for line in text.splitlines()[:12]:
        console.print(f"  [dim]{line[:110]}[/dim]", markup=True, highlight=False)
    console.print(f"  [dim]--- guardado en {dest} (puedes revisarlo completo) ---[/dim]")
    if not (assume_yes and tool.risk.value != "high"):
        if not typer.confirm("Ejecutar este script ahora?", default=False):
            raise RunError("Cancelado por el usuario.")
    if sys.platform != "win32":
        raise RunError("La ejecucion de scripts PowerShell solo esta soportada en Windows.")
    config.audit({"action": "script-exec", "tool": tool.id, "sha256": digest, "url": url})
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(dest)], check=False
    )


def _run_native(tool: Tool, console: Console, dry_run: bool) -> None:
    cmd = tool.source.command
    console.print(f"  Comando: [bold]{cmd}[/bold]")
    if tool.steps:
        console.print("  [dim]Pasos recomendados:[/dim]")
        for i, s in enumerate(tool.steps, 1):
            console.print(f"  [dim]{i}. {s}[/dim]", highlight=False)
    if dry_run:
        console.print("  [dim](dry-run) no se ejecuta[/dim]")
        return
    subprocess.run(cmd, shell=True, check=False)


def _show_guide(tool: Tool, console: Console) -> None:
    console.print("\n[bold cyan]Pasos[/bold cyan]")
    for i, s in enumerate(tool.steps, 1):
        console.print(f"  {i}. {s}", highlight=False)


def execute(tool: Tool, *, dry_run: bool, assume_yes: bool, console: Console, install: bool = False) -> None:
    """Ejecuta una herramienta. Lanza RunError/SecurityError si no puede o no debe continuar."""
    if install and tool.source.type not in INSTALLABLE:
        raise RunError(f"'{tool.id}' es de tipo {tool.source.type.value}; usa 'run' en lugar de 'install'.")

    if tool.category is Category.activacion and not config.plugin_enabled("activation"):
        raise RunError(
            "Las herramientas de activacion estan desactivadas por defecto.\n"
            "  Revisa el aviso de licenciamiento y habilitalas con: recursos-jeremialex04 plugin enable activation"
        )

    _announce(tool, console)
    if tool.requires_admin and not is_admin():
        console.print("  [yellow]Aviso: requiere permisos de administrador; abre la terminal como administrador.[/yellow]")

    if not dry_run and tool.source.type is not SourceType.guide:
        if not confirm_risk(tool, assume_yes, console):
            raise RunError("Cancelado por el usuario.")

    t = tool.source.type
    if t is SourceType.guide:
        _show_guide(tool, console)
    elif t is SourceType.url:
        _run_url(tool, console, dry_run)
    elif t is SourceType.local_file:
        _run_local_file(tool, console, dry_run)
    elif t is SourceType.script:
        _run_script(tool, console, dry_run, assume_yes)
    elif t is SourceType.native_command:
        _run_native(tool, console, dry_run)

    config.audit({"action": "install" if install else "run", "tool": tool.id, "dry_run": dry_run})
