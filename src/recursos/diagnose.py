"""Modulo de diagnostico interactivo."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

from recursos.catalog import get_tool, load_catalog
from recursos.models import Tool

DIAGNOSTIC_TREE = [
    {
        "id": "1",
        "title": "Lentitud, bloatware o configuracion de Windows",
        "options": [
            ("Lento, con telemetria o quiero optimizar", "winutil"),
            ("Falta la consola gpedit.msc (Windows Home)", "gpedit"),
            ("Un instalador no abre o da error de privilegios", "msiexec-admin"),
        ],
    },
    {
        "id": "2",
        "title": "Instalacion y desinstalacion de software",
        "options": [
            ("Instalar programas basicos tras formateo en un solo paso", "ninite"),
            ("Un programa no se deja desinstalar o deja restos en el registro", "revo-uninstaller"),
        ],
    },
    {
        "id": "3",
        "title": "Hardware, drivers y perifericos",
        "options": [
            ("Falta sonido, Wi-Fi, tarjeta de red o drivers del chipset", "driver-booster"),
            ("Impresora no se reconoce o faltan sus controladores", "zofti-impresoras"),
        ],
    },
    {
        "id": "4",
        "title": "Almacenamiento y memorias USB",
        "options": [
            ("Memoria USB muestra menos espacio o tiene particiones rebeldes", "diskpart-usb"),
        ],
    },
    {
        "id": "5",
        "title": "Dispositivos moviles (Android)",
        "options": [
            ("Eliminar aplicaciones del operador o bloatware sin root", "adb-appcontrol"),
        ],
    },
    {
        "id": "6",
        "title": "Licenciamiento y activacion",
        "options": [
            ("Activacion con soporte de codigo abierto (script)", "mas"),
            ("Paquete portable de activacion KMS / Office", "kms-tools"),
        ],
    },
    {
        "id": "7",
        "title": "Entornos heredados y pruebas virtuales",
        "options": [
            ("Un software contable/administrativo pide SQL Server antiguo", "sql-antiguos"),
            ("Crear un laboratorio aislado para probar herramientas", "vmware-workstation"),
        ],
    },
]


def run_diagnose(console: Console) -> Tool | None:
    tools = load_catalog()
    console.print(Panel("[bold cyan]Asistente de Diagnostico Tecnico[/bold cyan]\n"
                        "Selecciona el sintoma principal que presenta el equipo.", border_style="cyan"))

    for item in DIAGNOSTIC_TREE:
        console.print(f"  [bold yellow][{item['id']}][/bold yellow] {item['title']}")

    cat_choice = typer.prompt("\nElige una categoria (numero)", default="1").strip()
    selected_group = next((item for item in DIAGNOSTIC_TREE if item["id"] == cat_choice), None)

    if not selected_group:
        console.print("[red]Opcion no valida.[/red]")
        return None

    console.print(f"\n[bold]{selected_group['title']}[/bold]:")
    for idx, (desc, tool_id) in enumerate(selected_group["options"], 1):
        console.print(f"  [bold green][{idx}][/bold green] {desc}")

    sub_choice = typer.prompt("\nElige el caso exacto (numero)", default="1").strip()
    try:
        sub_idx = int(sub_choice) - 1
        if 0 <= sub_idx < len(selected_group["options"]):
            target_tool_id = selected_group["options"][sub_idx][1]
            tool = get_tool(tools, target_tool_id)
            if tool:
                console.print(f"\n[bold green]=> Herramienta recomendada:[/] [bold]{tool.name}[/] ([cyan]{tool.id}[/cyan])")
                console.print(f"   {tool.summary}\n")
                return tool
    except ValueError:
        pass

    console.print("[red]Opcion no valida.[/red]")
    return None
