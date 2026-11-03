"""CLI de gestion y ejecucion del Centro de Recursos Tecnologicos."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from recursos import __version__, config
from recursos.catalog import CatalogError, filter_tools, get_tool, load_catalog, search
from recursos.diagnose import run_diagnose
from recursos.docs_builder import build_markdown
from recursos.doctor import run_doctor
from recursos.models import Category, Risk, Tool
from recursos.offline import export_offline_bundle
from recursos.runner import RunError, SecurityError, execute

app = typer.Typer(
    help="Centro de Recursos Tecnologicos - Herramientas de soporte y mantenimiento.",
    no_args_is_help=False,
    add_completion=True,
)
plugin_app = typer.Typer(help="Gestionar plugins y modulos opcionales.")
app.add_typer(plugin_app, name="plugin")

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


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Muestra la version."
    ),
    cli: bool = typer.Option(
        False, "--cli", help="Fuerza el modo terminal y muestra la ayuda en lugar de abrir la interfaz grafica."
    ),
) -> None:
    if ctx.invoked_subcommand is None:
        if cli:
            console.print(ctx.get_help())
            raise typer.Exit()
        try:
            from recursos.gui import launch_gui
            launch_gui()
        except Exception as exc:
            console.print(f"[yellow]No se pudo iniciar la interfaz grafica ({exc}). Modo terminal:[/yellow]\n")
            console.print(ctx.get_help())


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


@app.command("run")
def run_cmd(
    tool_id: str = typer.Argument(..., help="ID de la herramienta a ejecutar."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Muestra que haria sin ejecutar nada."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Acepta confirmaciones de riesgo medio automaticamente."),
) -> None:
    """Ejecuta una herramienta con validacion de integridad y seguridad."""
    tool = get_tool(_load(), tool_id)
    if tool is None:
        console.print(f"[red]Herramienta no encontrada:[/] '{tool_id}'. Usa 'list' para ver las disponibles.")
        raise typer.Exit(code=1)
    try:
        execute(tool, dry_run=dry_run, assume_yes=yes, console=console)
    except (RunError, SecurityError) as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(code=1)


@app.command("install")
def install_cmd(
    tool_id: str = typer.Argument(..., help="ID del programa a instalar."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simula la instalacion."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Acepta confirmaciones automaticamente."),
) -> None:
    """Instala o descarga un programa (alias de run para herramientas instalables)."""
    tool = get_tool(_load(), tool_id)
    if tool is None:
        console.print(f"[red]Herramienta no encontrada:[/] '{tool_id}'")
        raise typer.Exit(code=1)
    try:
        execute(tool, dry_run=dry_run, assume_yes=yes, console=console, install=True)
    except (RunError, SecurityError) as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(code=1)


@app.command("diagnose")
def diagnose_cmd() -> None:
    """Asistente interactivo para diagnosticar fallas en el equipo."""
    tool = run_diagnose(console)
    if tool:
        run_now = typer.confirm("Deseas ejecutar esta herramienta ahora?", default=True)
        if run_now:
            try:
                execute(tool, dry_run=False, assume_yes=False, console=console)
            except (RunError, SecurityError) as e:
                console.print(f"[red]Error al ejecutar:[/] {e}")


@app.command("doctor")
def doctor_cmd() -> None:
    """Verifica privilegios de administrador, PowerShell, internet y espacio en disco."""
    ok = run_doctor(console)
    if not ok:
        raise typer.Exit(code=1)


@app.command("docs")
def docs_cmd(
    build: bool = typer.Option(False, "--build", help="Genera CATALOGO-HERRAMIENTAS.md desde el catalogo YAML."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Ruta del archivo Markdown a generar."),
) -> None:
    """Construye o consulta la documentacion automatica."""
    if build:
        tools = _load()
        md_text = build_markdown(tools)
        target = output or (config.repo_root() / "CATALOGO-HERRAMIENTAS.md" if config.repo_root() else Path("CATALOGO-HERRAMIENTAS.md"))
        target.write_text(md_text, encoding="utf-8")
        console.print(f"[green]Documentacion generada en:[/] {target}")
    else:
        console.print("Usa [bold]--build[/bold] para regenerar CATALOGO-HERRAMIENTAS.md.")


@app.command("export-offline")
def export_offline_cmd(
    dest: Path = typer.Argument(..., help="Carpeta destino o unidad USB (ej.: E:\\Recursos)."),
) -> None:
    """Exporta el catalogo y los instaladores para usar la herramienta sin conexion."""
    export_offline_bundle(dest, console)


@app.command("clean")
def clean_cmd(
    all_data: bool = typer.Option(False, "--all", help="Elimina tambien logs y configuraciones."),
) -> None:
    """Limpia los archivos temporales y binarios descargados en cache."""
    cdir = config.cache_dir()
    if cdir.exists():
        shutil.rmtree(cdir)
        cdir.mkdir(parents=True, exist_ok=True)
        console.print("[green]Cache temporal limpiada con exito.[/green]")
    if all_data:
        ddir = config.data_dir()
        if ddir.exists():
            shutil.rmtree(ddir)
            console.print("[green]Todos los datos locales han sido eliminados.[/green]")

@app.command("gui")
def gui_cmd() -> None:
    """Abre la aplicacion grafica de escritorio para gestionar todas las herramientas."""
    try:
        from recursos.gui import launch_gui
        launch_gui()
    except Exception as exc:
        console.print(f"[red]Error al abrir la interfaz grafica:[/] {exc}")
        raise typer.Exit(code=1)



# --- Subcomandos de plugins ---

@plugin_app.command("list")
def plugin_list() -> None:
    """Lista el estado de los plugins disponibles."""
    table = Table(header_style="bold cyan")
    table.add_column("Plugin")
    table.add_column("Estado")
    table.add_column("Descripcion")

    act_enabled = config.plugin_enabled("activation")
    table.add_row(
        "activation",
        "[green]Habilitado[/green]" if act_enabled else "[yellow]Deshabilitado[/yellow]",
        "Herramientas de activacion (MAS, KMS). Requiere revision de licencias.",
    )
    console.print(table)


@plugin_app.command("enable")
def plugin_enable(name: str = typer.Argument(..., help="Nombre del plugin (ej.: activation)")) -> None:
    """Habilita un plugin opcional."""
    if name == "activation":
        console.print("[bold yellow]ADVERTENCIA DE RESPONSABILIDAD LEGAL Y SEGURIDAD[/bold yellow]")
        console.print("Las herramientas del plugin de activacion no son oficiales de Microsoft.")
        console.print("El uso de estas herramientas debe cumplir con los terminos de licenciamiento.")
        confirm = typer.confirm("Entiendo y deseo habilitar este plugin?", default=False)
        if confirm:
            config.set_plugin(name, True)
            console.print("[green]Plugin 'activation' habilitado.[/green]")
        else:
            console.print("[yellow]Operacion cancelada.[/yellow]")
    else:
        config.set_plugin(name, True)
        console.print(f"[green]Plugin '{name}' habilitado.[/green]")


@plugin_app.command("disable")
def plugin_disable(name: str = typer.Argument(..., help="Nombre del plugin.")) -> None:
    """Deshabilita un plugin opcional."""
    config.set_plugin(name, False)
    console.print(f"[green]Plugin '{name}' deshabilitado.[/green]")

