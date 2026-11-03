"""Herramienta de diagnostico del entorno (doctor)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.request
from rich.console import Console
from rich.table import Table

from recursos import config
from recursos.security import is_admin


def run_doctor(console: Console) -> bool:
    console.print("\n[bold cyan]Verificando entorno de ejecucion...[/bold cyan]\n")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Componente", style="dim", width=25)
    table.add_column("Estado", width=12)
    table.add_column("Detalle")

    all_ok = True

    # 1. Sistema Operativo
    is_win = sys.platform == "win32"
    table.add_row(
        "Sistema Operativo",
        "[green]OK[/green]" if is_win else "[yellow]Aviso[/yellow]",
        f"{sys.platform} ({os.name})",
    )

    # 2. Privilegios de Administrador
    admin = is_admin()
    table.add_row(
        "Privilegios Admin",
        "[green]SI[/green]" if admin else "[yellow]NO[/yellow]",
        "Ejecutando con permisos elevados" if admin else "Algunas herramientas requieren 'Ejecutar como administrador'",
    )

    # 3. PowerShell
    ps_cmd = shutil.which("powershell") or shutil.which("pwsh")
    if ps_cmd:
        try:
            res = subprocess.run([ps_cmd, "-Command", "$PSVersionTable.PSVersion.ToString()"],
                                 capture_output=True, text=True, timeout=5)
            ps_ver = res.stdout.strip()
            table.add_row("PowerShell", "[green]OK[/green]", f"Disponible (version {ps_ver})")
        except Exception:
            table.add_row("PowerShell", "[green]OK[/green]", "Disponible")
    else:
        table.add_row("PowerShell", "[red]Falta[/red]", "No se encontro powershell en el PATH")
        all_ok = False

    # 4. Conectividad a Internet
    net_ok = False
    try:
        urllib.request.urlopen("https://github.com", timeout=4)
        net_ok = True
        table.add_row("Conexion Internet", "[green]OK[/green]", "Acceso a GitHub verificado")
    except Exception as e:
        table.add_row("Conexion Internet", "[yellow]Offline[/yellow]", f"Sin conexion ({e.__class__.__name__})")

    # 5. Directorio de Cache / Datos
    try:
        cdir = config.cache_dir()
        test_file = cdir / ".doctor_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        table.add_row("Directorio de datos", "[green]OK[/green]", f"{cdir}")
    except Exception as e:
        table.add_row("Directorio de datos", "[red]Error[/red]", f"Fallo de escritura: {e}")
        all_ok = False

    # 6. Espacio en disco
    if is_win:
        for drive in ("C:", "D:"):
            if os.path.exists(drive):
                try:
                    usage = shutil.disk_usage(drive)
                    free_gb = usage.free / (1024**3)
                    style = "[green]" if free_gb > 2.0 else ("[yellow]" if free_gb > 0.5 else "[red]")
                    table.add_row(f"Espacio en disco ({drive})",
                                  f"{style}{free_gb:.1f} GB libre[/]",
                                  f"Total: {usage.total / (1024**3):.1f} GB")
                    if free_gb < 0.2:
                        all_ok = False
                except Exception:
                    pass

    console.print(table)
    console.print()
    return all_ok
