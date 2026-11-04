"""Exportacion de catalogo y binarios para uso sin conexion (modo USB)."""

from __future__ import annotations

import shutil
from pathlib import Path
from rich.console import Console

from recursos import config
from recursos.catalog import load_catalog
from recursos.models import SourceType


def export_offline_bundle(dest_dir: Path, console: Console) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[bold cyan]Exportando recursos a:[/] {dest_dir}\n")

    # 1. Copiar catalog
    catalog_src = config.repo_root() / "catalog" if config.repo_root() else None
    if catalog_src and catalog_src.is_dir():
        cat_dest = dest_dir / "catalog"
        if cat_dest.exists():
            shutil.rmtree(cat_dest)
        shutil.copytree(catalog_src, cat_dest)
        console.print("  [green]+[/green] Catalogo YAML exportado")

    # 2. Copiar archivos locales del repositorio que existan
    tools = load_catalog()
    files_dest = dest_dir / "files"
    files_dest.mkdir(exist_ok=True)

    copied = 0
    repo = config.repo_root()
    for t in tools:
        if t.source.type == SourceType.local_file and t.source.path:
            src_file = None
            if repo and (repo / t.source.path).is_file():
                src_file = repo / t.source.path
            else:
                cached = config.cache_dir() / Path(t.source.path).name
                if cached.is_file():
                    src_file = cached

            if src_file:
                target = files_dest / Path(t.source.path).name
                shutil.copy2(src_file, target)
                console.print(f"  [green]+[/green] Binario copiado: {src_file.name}")
                copied += 1
            else:
                console.print(f"  [yellow]![/yellow] Binario pendiente de descarga: {t.source.path}")

    # 3. Crear launcher batch en la raiz del USB
    launcher = dest_dir / "iniciar_recursos.bat"
    launcher.write_text(
        "@echo off\n"
        "chcp 65001 >nul\n"
        "set RECURSOS_CATALOG=%~dp0catalog\n"
        "set RECURSOS_HOME=%~dp0files\n"
        "echo Iniciando Recursos Tecnologicos en modo Offline...\n"
        "recursos-jeremialex04.exe list\n"
        "pause\n",
        encoding="utf-8",
    )
    console.print(f"  [green]+[/green] Lanzador creado: {launcher.name}\n")
    console.print(f"[bold green]Exportacion completada.[/bold green] Total archivos copiados: {copied}")
