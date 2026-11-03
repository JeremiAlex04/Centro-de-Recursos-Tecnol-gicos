"""Comandos de consulta: list, search, info (fase 2 del plan).

La ejecucion de herramientas (run/install) se implementa en la fase 3, junto con la
verificacion de hash y las confirmaciones de riesgo.
"""

from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from recursos import __version__
from recursos.catalog import CatalogError, filter_tools, get_tool, load_catalog, search
from recursos.models import Category, Risk, Tool

app = typer.Typer(
    help="Catalogo de herramientas de soporte tecnico: consulta y uso.",
    no_args_is_help=True,
    add_completion=True,
)
console = Console()

RISK_STYLE = {Risk.low: "green", Risk.medium: "yellow", Risk.high: "red"}
RISK_LABEL = {Risk.low: "bajo", Risk.medium: "medio", Risk.high: "alto"}


def _load() -> list[Tool]:
    try:
        return load_catalog()
    except CatalogError as exc:
        console.print(f"[red]Error de catalogo:[/red] {exc}")
        raise typer.Exit(code=2)


def _table(tools: list[Tool]) -> Table:
    table = Table(show_lines=False, header_style="bold cyan")
    for col in ("ID", "Herramienta", "Categoria", "Riesgo", "Admin", "Resumen"):
        table.add_column(col, overflow="fold")
    for t in tools:
        table.add_row(
            t.id,
            t.name,
            t.category.value,
            f"[{RISK_STYLE[t.risk]}]{RISK_LABEL[t.risk]}[/]",
            "si" if t.requires_admin else "no",
            t.summary,
        )
    return table


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"recursos-jeremialex04 {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Muestra la version."
    ),
) -> None:
    pass


@app.command("list")
def list_cmd(
    category: Optional[Category] = typer.Option(None, "--category", "-c", help="Filtra por categoria."),
    risk: Optional[Risk] = typer.Option(None, "--risk", "-r", help="Filtra por riesgo."),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filtra por etiqueta."),
    as_json: bool = typer.Option(False, "--json", help="Salida en JSON."),
) -> None:
    """Lista las herramientas del catalogo."""
    tools = filter_tools(_load(), category, risk, tag)
    if as_json:
        typer.echo(json.dumps([t.model_dump(mode="json") for t in tools], ensure_ascii=False, indent=2))
        return
    if not tools:
        console.print("[yellow]Sin resultados.[/yellow]")
        raise typer.Exit(code=1)
    console.print(_table(tools))


@app.command("search")
def search_cmd(
    query: list[str] = typer.Argument(..., help="Palabras clave o sintoma."),
    as_json: bool = typer.Option(False, "--json", help="Salida en JSON."),
) -> None:
    """Busca por nombre, etiquetas o sintoma (ej.: 'impresora', 'no desinstala')."""
    found = search(_load(), " ".join(query))
    if as_json:
        typer.echo(json.dumps([t.model_dump(mode="json") for t in found], ensure_ascii=False, indent=2))
        return
    if not found:
        console.print("[yellow]Sin resultados.[/yellow]")
        raise typer.Exit(code=1)
    console.print(_table(found))


@app.command("info")
def info_cmd(tool_id: str = typer.Argument(..., help="ID de la herramienta (ver 'list').")) -> None:
    """Muestra contexto, utilidad, pasos y avisos de una herramienta."""
    tool = get_tool(_load(), tool_id)
    if tool is None:
        console.print(f"[red]No se encontro una herramienta unica para '{tool_id}'.[/red] Usa 'list'.")
        raise typer.Exit(code=1)

    color = RISK_STYLE[tool.risk]
    header = (
        f"[bold]{tool.name}[/bold]  ({tool.category.value})\n"
        f"Riesgo: [{color}]{RISK_LABEL[tool.risk]}[/]  |  "
        f"Admin: {'si' if tool.requires_admin else 'no'}  |  "
        f"Internet: {'si' if tool.requires_internet else 'no'}  |  Licencia: {tool.license}"
    )
    console.print(Panel(header, border_style=color))
    console.print(f"[bold cyan]Resumen[/]\n  {tool.summary}")
    if tool.context:
        console.print(f"\n[bold cyan]Contexto[/]\n  {tool.context}")
    if tool.purpose:
        console.print("\n[bold cyan]Para que sirve[/]")
        for p in tool.purpose:
            console.print(f"  - {p}")
    if tool.steps:
        console.print("\n[bold cyan]Como usarla[/]")
        for i, s in enumerate(tool.steps, 1):
            console.print(f"  {i}. {s}")
    for w in tool.warnings:
        console.print(f"\n[bold {color}]AVISO:[/] {w}")
    if tool.docs:
        console.print(f"\n[dim]Documentacion: {tool.docs}[/dim]")
