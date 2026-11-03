"""Aplicacion de escritorio (GUI) para el Centro de Recursos Tecnologicos."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import urllib.request
import webbrowser
from pathlib import Path
from typing import Optional

import customtkinter as ctk
from tkinter import messagebox

from recursos import config
from recursos.catalog import get_tool, load_catalog, search
from recursos.diagnose import DIAGNOSTIC_TREE
from recursos.models import Category, Risk, SourceType, Tool
from recursos.runner import execute
from recursos.security import is_admin, sha256_file, verify_sha256

# Configuracion global de tema
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CATEGORY_ICONS = {
    Category.sistema: "🖥️ Sistema",
    Category.software: "📦 Software",
    Category.drivers: "🔧 Drivers",
    Category.almacenamiento: "💾 Almacenamiento",
    Category.moviles: "📱 Móviles",
    Category.activacion: "🔑 Activación",
    Category.virtualizacion: "🗄️ Virtualización",
}

RISK_COLORS = {
    Risk.low: ("#2EA44F", "#238636"),
    Risk.medium: ("#D29922", "#9E6A03"),
    Risk.high: ("#F85149", "#DA3633"),
}

# Descripciones breves y claras de la aplicacion de uso en soporte tecnico
USO_ESCENARIOS = {
    "winutil": "💡 Cuándo usarlo: Tras formatear Windows o en PCs lentas para eliminar bloatware, desactivar telemetría y configurar aplicaciones básicas con un solo clic.",
    "gpedit": "💡 Cuándo usarlo: En laptops o PCs con Windows 10/11 Home donde no existe la consola gpedit.msc para aplicar directivas locales y bloquear actualizaciones.",
    "msiexec-admin": "💡 Cuándo usarlo: Cuando un instalador .msi o .exe no abre al darle doble clic o muestra error de permisos insuficientes (error 2502 / 2503).",
    "ninite": "💡 Cuándo usarlo: Al preparar una PC nueva; descarga e instala navegadores, utilidades, 7-Zip y reproductores sin anuncios ni clics repetitivos.",
    "revo-uninstaller": "💡 Cuándo usarlo: Cuando un programa no se deja desinstalar desde el Panel de Control, está corrupto o deja carpetas y restos en el registro.",
    "driver-booster": "💡 Cuándo usarlo: En equipos recién formateados donde falta audio, Wi-Fi o tarjeta gráfica; busca e instala todos los controladores faltantes.",
    "zofti-impresoras": "💡 Cuándo usarlo: Cuando una impresora Epson, HP, Canon o Brother no imprime, no es detectada o se reinstaló el sistema operativo.",
    "diskpart-usb": "💡 Cuándo usarlo: Cuando una memoria USB que fue booteable muestra menos capacidad de la real o tiene múltiples particiones bloqueadas.",
    "adb-appcontrol": "💡 Cuándo usarlo: Para limpiar celulares Android lentos quitando las aplicaciones preinstaladas del operador o fabricante sin necesidad de Root.",
    "mas": "💡 Cuándo usarlo: Para activar Windows u Office mediante métodos documentados de código abierto cuando el equipo muestra la marca de agua de licencia.",
    "kms-tools": "💡 Cuándo usarlo: Alternativa offline portátil para soporte en campo de licencias y mantenimiento/desinstalación limpia de paquetes de Office dañados.",
    "sql-antiguos": "💡 Cuándo usarlo: Al migrar sistemas contables, de facturación o puntos de venta antiguos que exigen versiones heredadas de Microsoft SQL Server.",
    "vmware-workstation": "💡 Cuándo usarlo: Para crear máquinas virtuales y laboratorios de prueba aislados sin poner en riesgo la computadora física principal.",
}


class DetailWindow(ctk.CTkToplevel):
    """Ventana emergente con los detalles completos y pasos de una herramienta."""

    def __init__(self, parent: ctk.CTk, tool: Tool, on_run_callback):
        super().__init__(parent)
        self.tool = tool
        self.on_run = on_run_callback

        self.title(f"Detalles: {tool.name}")
        self.geometry("700x550")
        self.minsize(550, 450)
        self.attributes("-topmost", True)

        self._build_ui()

    def _build_ui(self):
        # Cabecera
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        title = ctk.CTkLabel(header, text=self.tool.name, font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(anchor="w")

        meta_text = (
            f"Categoría: {self.tool.category.value.capitalize()} | "
            f"Riesgo: {self.tool.risk.value.upper()} | "
            f"Requiere Admin: {'Sí' if self.tool.requires_admin else 'No'} | "
            f"Internet: {'Sí' if self.tool.requires_internet else 'No'}"
        )
        ctk.CTkLabel(header, text=meta_text, text_color="gray70", font=ctk.CTkFont(size=12)).pack(anchor="w")

        # Tabs de contenido
        tabview = ctk.CTkTabview(self)
        tabview.pack(fill="both", expand=True, padx=20, pady=10)

        tab_guia = tabview.add("Guía y Pasos de Uso")
        tab_info = tabview.add("Ficha Técnica")

        # Pestaña Guía
        guia_scroll = ctk.CTkScrollableFrame(tab_guia, fg_color="transparent")
        guia_scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(guia_scroll, text="¿Para qué sirve?", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(5, 2))
        ctk.CTkLabel(guia_scroll, text=self.tool.summary, wraplength=600, justify="left").pack(anchor="w", pady=(0, 10))

        if self.tool.context:
            ctk.CTkLabel(guia_scroll, text="Contexto:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(5, 2))
            ctk.CTkLabel(guia_scroll, text=self.tool.context, wraplength=600, justify="left").pack(anchor="w", pady=(0, 10))

        # Pasos
        if self.tool.steps:
            ctk.CTkLabel(guia_scroll, text="Instrucciones paso a paso:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(5, 2))
            for idx, step in enumerate(self.tool.steps, 1):
                p_frame = ctk.CTkFrame(guia_scroll, fg_color=("gray85", "gray20"), corner_radius=6)
                p_frame.pack(fill="x", pady=2, padx=2)
                ctk.CTkLabel(p_frame, text=f"{idx}. {step}", wraplength=580, justify="left").pack(anchor="w", padx=10, pady=5)

        # Advertencias
        if self.tool.warnings:
            ctk.CTkLabel(guia_scroll, text="⚠️ Advertencias y Precauciones:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#F85149").pack(anchor="w", pady=(10, 2))
            for w in self.tool.warnings:
                w_frame = ctk.CTkFrame(guia_scroll, fg_color=("#FFEBE9", "#490202"), corner_radius=6)
                w_frame.pack(fill="x", pady=2, padx=2)
                ctk.CTkLabel(w_frame, text=f"• {w}", text_color=("#CF222E", "#FF7B72"), wraplength=580, justify="left").pack(anchor="w", padx=10, pady=5)

        # Pestaña Ficha Técnica
        info_scroll = ctk.CTkScrollableFrame(tab_info, fg_color="transparent")
        info_scroll.pack(fill="both", expand=True)

        details = [
            ("ID del sistema", self.tool.id),
            ("Tipo de recurso", self.tool.source.type.value),
            ("Licencia", self.tool.license),
            ("URL o Comando", self.tool.source.url or self.tool.source.command or self.tool.source.path or "-"),
            ("Checksum SHA-256", self.tool.source.sha256 or "N/A"),
            ("Documentación local", self.tool.docs or "N/A"),
        ]
        for label, val in details:
            d_box = ctk.CTkFrame(info_scroll, fg_color=("gray85", "gray20"), corner_radius=6)
            d_box.pack(fill="x", pady=3)
            ctk.CTkLabel(d_box, text=label, font=ctk.CTkFont(weight="bold", size=12), width=160, anchor="w").pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(d_box, text=val, wraplength=420, justify="left", anchor="w").pack(side="left", fill="x", expand=True, padx=5, pady=8)

        # Botones inferiores
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkButton(
            bottom,
            text="🚀 Lanzar esta Herramienta",
            fg_color="#2EA44F",
            hover_color="#238636",
            font=ctk.CTkFont(weight="bold"),
            command=self._launch_now,
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            bottom,
            text="Cerrar",
            fg_color=("gray75", "gray25"),
            text_color=("black", "white"),
            command=self.destroy,
        ).pack(side="right", padx=5)

    def _launch_now(self):
        self.destroy()
        self.on_run(self.tool)


class ExecutionLogWindow(ctk.CTkToplevel):
    """Ventana de consola que muestra en tiempo real la ejecucion y descargas."""

    def __init__(self, parent: ctk.CTk, tool: Tool):
        super().__init__(parent)
        self.tool = tool
        self.title(f"Ejecutando: {tool.name}")
        self.geometry("620x380")
        self.minsize(500, 300)
        self.attributes("-topmost", True)

        ctk.CTkLabel(self, text=f"🚀 {tool.name}", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(15, 5))
        self.status_lbl = ctk.CTkLabel(self, text="Iniciando...", text_color="gray70")
        self.status_lbl.pack(anchor="w", padx=20, pady=(0, 10))

        self.textbox = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=12))
        self.textbox.pack(fill="both", expand=True, padx=20, pady=(0, 15))

    def log(self, text: str):
        self.textbox.insert("end", text + "\n")
        self.textbox.see("end")

    def set_status(self, text: str, color="white"):
        self.status_lbl.configure(text=text, text_color=color)


class RecursosApp(ctk.CTk):
    """Ventana Principal de la Aplicacion de Escritorio."""

    def __init__(self):
        super().__init__()

        self.title("Centro de Recursos Tecnológicos (JeremiAlex04)")
        self.geometry("1180x760")
        self.minsize(980, 640)

        # Cargar catálogo de herramientas
        self.all_tools: list[Tool] = load_catalog()
        self.filtered_tools: list[Tool] = list(self.all_tools)
        self.current_category: Optional[Category] = None

        self._build_layout()
        self._populate_tools()

    def _build_layout(self):
        # Configuracion del Grid Principal: Sidebar (Col 0) + Contenido (Col 1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ==================== BARRA LATERAL (SIDEBAR) ====================
        sidebar = ctk.CTkFrame(self, width=240, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(9, weight=1)

        # Logotipo / Titulo
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=15, pady=(20, 15))

        ctk.CTkLabel(logo_frame, text="🛠️ Recursos TI", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(logo_frame, text="Soporte y Reparación", font=ctk.CTkFont(size=12), text_color="gray70").pack(anchor="w")

        # Seccion Categorias
        ctk.CTkLabel(sidebar, text="CATEGORÍAS", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray60").pack(anchor="w", padx=15, pady=(10, 5))

        self.cat_buttons: dict[str, ctk.CTkButton] = {}
        
        btn_all = ctk.CTkButton(
            sidebar,
            text="🗂️ Todas las Herramientas",
            anchor="w",
            fg_color="#1F6AA5",
            hover_color="#144870",
            command=lambda: self._select_category(None),
        )
        btn_all.pack(fill="x", padx=12, pady=2)
        self.cat_buttons["all"] = btn_all

        for cat in Category:
            btn = ctk.CTkButton(
                sidebar,
                text=CATEGORY_ICONS[cat],
                anchor="w",
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray85", "gray25"),
                command=lambda c=cat: self._select_category(c),
            )
            btn.pack(fill="x", padx=12, pady=2)
            self.cat_buttons[cat.value] = btn

        # Seccion Utilidades Auxiliares
        ctk.CTkLabel(sidebar, text="UTILIDADES", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray60").pack(anchor="w", padx=15, pady=(15, 5))

        btn_diag = ctk.CTkButton(
            sidebar,
            text="🩺 Asistente Diagnóstico",
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray85", "gray25"),
            command=self._show_diagnostico_view,
        )
        btn_diag.pack(fill="x", padx=12, pady=2)

        btn_doc = ctk.CTkButton(
            sidebar,
            text="🏥 Estado del PC (Doctor)",
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray85", "gray25"),
            command=self._show_doctor_view,
        )
        btn_doc.pack(fill="x", padx=12, pady=2)

        # Panel Inferior de la barra lateral
        bottom_side = ctk.CTkFrame(sidebar, fg_color="transparent")
        bottom_side.pack(side="bottom", fill="x", padx=15, pady=15)

        # Switch de tema (Oscuro / Claro)
        self.theme_switch = ctk.CTkSwitch(bottom_side, text="Modo Oscuro", command=self._toggle_theme)
        self.theme_switch.select()
        self.theme_switch.pack(anchor="w", pady=(0, 10))

        # Boton limpiar cache
        btn_clean = ctk.CTkButton(
            bottom_side,
            text="🧹 Limpiar Temporales",
            height=28,
            fg_color=("gray75", "gray30"),
            text_color=("black", "white"),
            command=self._clean_cache,
        )
        btn_clean.pack(fill="x")

        # ==================== AREA PRINCIPAL (DERECHA) ====================
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        # Barra Superior de Busqueda y Filtros
        top_bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        top_bar.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            top_bar,
            placeholder_text="🔍 Buscar herramienta o síntoma (ej.: wifi, lentitud, formateo, desinstalar)...",
            height=38,
            font=ctk.CTkFont(size=14),
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", self._on_search_change)

        self.status_count = ctk.CTkLabel(top_bar, text="", font=ctk.CTkFont(size=12), text_color="gray70")
        self.status_count.grid(row=0, column=1, padx=5)

        # Marco de Contenido Dinamico (Herramientas, Diagnostico o Doctor)
        self.content_area = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_area.grid(row=1, column=0, sticky="nsew")
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(0, weight=1)

        # Marco de tarjetas con desplazamiento
        self.tools_scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        self.tools_scroll.grid(row=0, column=0, sticky="nsew")

    def _populate_tools(self):
        """Renderiza las tarjetas interactivas de herramientas."""
        for widget in self.tools_scroll.winfo_children():
            widget.destroy()

        self.status_count.configure(text=f"Mostrando {len(self.filtered_tools)} de {len(self.all_tools)} herramientas")

        if not self.filtered_tools:
            no_res = ctk.CTkFrame(self.tools_scroll, fg_color=("gray90", "gray18"), corner_radius=10)
            no_res.pack(fill="x", pady=20, padx=10)
            ctk.CTkLabel(no_res, text="No se encontraron herramientas con ese criterio.", font=ctk.CTkFont(size=15)).pack(pady=30)
            return

        for tool in self.filtered_tools:
            self._create_tool_card(tool)

    def _create_tool_card(self, tool: Tool):
        """Crea una tarjeta interactiva con descripcion breve de su aplicacion de uso."""
        card = ctk.CTkFrame(self.tools_scroll, corner_radius=10, fg_color=("gray90", "gray17"))
        card.pack(fill="x", pady=7, padx=5)

        # Fila 1: Titulo + Badges
        r1 = ctk.CTkFrame(card, fg_color="transparent")
        r1.pack(fill="x", padx=15, pady=(12, 4))

        ctk.CTkLabel(r1, text=tool.name, font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        # Badge de categoria
        cat_badge = ctk.CTkLabel(
            r1,
            text=f"  {tool.category.value.capitalize()}  ",
            font=ctk.CTkFont(size=11),
            fg_color=("gray75", "gray30"),
            corner_radius=6,
        )
        cat_badge.pack(side="left", padx=8)

        # Badge de riesgo
        risk_color = RISK_COLORS[tool.risk][1]
        risk_badge = ctk.CTkLabel(
            r1,
            text=f"  Riesgo {tool.risk.value.upper()}  ",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=risk_color,
            text_color="white",
            corner_radius=6,
        )
        risk_badge.pack(side="left", padx=4)

        # Badge de Administrador si aplica
        if tool.requires_admin:
            adm_badge = ctk.CTkLabel(
                r1,
                text="  🛡️ Requiere Admin  ",
                font=ctk.CTkFont(size=11),
                fg_color=("#8250DF", "#5A32A3"),
                text_color="white",
                corner_radius=6,
            )
            adm_badge.pack(side="left", padx=4)

        # Fila 2: Resumen del proposito
        r2 = ctk.CTkFrame(card, fg_color="transparent")
        r2.pack(fill="x", padx=15, pady=(0, 6))

        ctk.CTkLabel(
            r2,
            text=tool.summary,
            font=ctk.CTkFont(size=13),
            wraplength=800,
            justify="left",
            text_color=("gray20", "gray85"),
        ).pack(anchor="w")

        # Fila 3: APLICACION DE USO PRACTICA (Destacada)
        r3 = ctk.CTkFrame(card, fg_color=("gray82", "gray22"), corner_radius=6)
        r3.pack(fill="x", padx=15, pady=(0, 10))

        uso_text = USO_ESCENARIOS.get(tool.id, f"💡 Aplicación: Para resolver problemas clasificados en {tool.category.value}.")
        ctk.CTkLabel(
            r3,
            text=uso_text,
            font=ctk.CTkFont(size=12, slant="italic"),
            wraplength=800,
            justify="left",
            text_color=("gray10", "gray95"),
        ).pack(anchor="w", padx=10, pady=6)

        # Fila 4: Botones de accion
        r4 = ctk.CTkFrame(card, fg_color="transparent")
        r4.pack(fill="x", padx=15, pady=(0, 12))

        # Texto del boton segun tipo
        action_text = "🚀 Ejecutar"
        if tool.source.type == SourceType.url:
            action_text = "🌐 Abrir Enlace"
        elif tool.source.type == SourceType.local_file and "Setup" in (tool.source.path or ""):
            action_text = "📦 Instalar"

        ctk.CTkButton(
            r4,
            text=action_text,
            width=120,
            height=30,
            fg_color="#2EA44F",
            hover_color="#238636",
            font=ctk.CTkFont(weight="bold", size=12),
            command=lambda t=tool: self._execute_tool_flow(t),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            r4,
            text="📖 Ver Pasos y Guía",
            width=140,
            height=30,
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray40"),
            text_color=("black", "white"),
            font=ctk.CTkFont(size=12),
            command=lambda t=tool: self._show_tool_details(t),
        ).pack(side="left")

    def _select_category(self, cat: Optional[Category]):
        """Filtra las herramientas por la categoria seleccionada."""
        self.current_category = cat
        for key, btn in self.cat_buttons.items():
            if (cat is None and key == "all") or (cat and key == cat.value):
                btn.configure(fg_color="#1F6AA5")
            else:
                btn.configure(fg_color="transparent")

        self._filter_and_refresh()

    def _on_search_change(self, event=None):
        self._filter_and_refresh()

    def _filter_and_refresh(self):
        query = self.search_entry.get().strip()
        tools = self.all_tools

        if self.current_category:
            tools = [t for t in tools if t.category == self.current_category]

        if query:
            tools = search(tools, query)

        self.filtered_tools = tools
        self._show_tools_view()
        self._populate_tools()

    def _show_tools_view(self):
        for widget in self.content_area.winfo_children():
            widget.grid_forget()
        self.tools_scroll.grid(row=0, column=0, sticky="nsew")

    def _show_tool_details(self, tool: Tool):
        DetailWindow(self, tool, self._execute_tool_flow)

    def _execute_tool_flow(self, tool: Tool):
        """Gestiona la ejecucion segura, pidiendo confirmaciones y mostrando la consola."""
        # 1. Validacion de plugin de activacion
        if tool.category == Category.activacion and not config.plugin_enabled("activation"):
            resp = messagebox.askyesno(
                "Módulo de Activación Deshabilitado",
                f"Las herramientas de activación están deshabilitadas por defecto.\n\n"
                f"¿Deseas habilitar temporalmente el plugin de activación para usar '{tool.name}'?",
            )
            if resp:
                config.set_plugin("activation", True)
            else:
                return

        # 2. Confirmacion de riesgo alto
        if tool.risk == Risk.high:
            resp = messagebox.askokcancel(
                "⚠️ Advertencia de Riesgo Alto",
                f"La herramienta '{tool.name}' tiene nivel de riesgo ALTO.\n\n"
                f"Puede borrar datos de unidades o realizar modificaciones profundas.\n\n"
                f"¿Estás seguro de que deseas continuar?",
            )
            if not resp:
                return

        # 3. Lanzar ventana de consola
        log_win = ExecutionLogWindow(self, tool)
        log_win.log(f"Iniciando ejecucion de: {tool.name}")
        log_win.log(f"Tipo: {tool.source.type.value} | Riesgo: {tool.risk.value}")

        def _worker():
            try:
                # Runner custom para redirigir texto al textbox
                class GuiConsole:
                    def print(self, msg, *args, **kwargs):
                        # Limpiar markup simple
                        clean_msg = str(msg).replace("[bold]", "").replace("[/bold]", "")
                        clean_msg = clean_msg.replace("[green]", "").replace("[/green]", "")
                        clean_msg = clean_msg.replace("[yellow]", "").replace("[/yellow]", "")
                        clean_msg = clean_msg.replace("[red]", "").replace("[/red]", "")
                        clean_msg = clean_msg.replace("[cyan]", "").replace("[/cyan]", "")
                        clean_msg = clean_msg.replace("[dim]", "").replace("[/dim]", "")
                        log_win.textbox.after(0, lambda m=clean_msg: log_win.log(m))

                gui_con = GuiConsole()
                execute(tool, dry_run=False, assume_yes=True, console=gui_con)
                log_win.textbox.after(0, lambda: log_win.set_status("✅ Ejecución iniciada correctamente", "#2EA44F"))
            except Exception as e:
                log_win.textbox.after(0, lambda err=str(e): log_win.log(f"\n[ERROR] {err}"))
                log_win.textbox.after(0, lambda: log_win.set_status("❌ Error durante la ejecución", "#F85149"))

        threading.Thread(target=_worker, daemon=True).start()

    def _show_diagnostico_view(self):
        """Muestra el asistente guiado de diagnostico de problemas."""
        for widget in self.content_area.winfo_children():
            widget.grid_forget()

        diag_frame = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        diag_frame.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(diag_frame, text="🩺 Asistente de Diagnóstico Técnico", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(5, 5))
        ctk.CTkLabel(diag_frame, text="Selecciona el problema que presenta el equipo para ver la solución recomendada:", text_color="gray70").pack(anchor="w", pady=(0, 15))

        for cat in DIAGNOSTIC_TREE:
            group_card = ctk.CTkFrame(diag_frame, corner_radius=10, fg_color=("gray90", "gray17"))
            group_card.pack(fill="x", pady=6, padx=5)

            ctk.CTkLabel(group_card, text=f"📂 {cat['title']}", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=15, pady=(10, 5))

            for desc, tool_id in cat["options"]:
                tool = get_tool(self.all_tools, tool_id)
                if not tool:
                    continue

                item = ctk.CTkFrame(group_card, fg_color=("gray85", "gray22"), corner_radius=6)
                item.pack(fill="x", padx=15, pady=3)

                ctk.CTkLabel(item, text=f"• {desc}", font=ctk.CTkFont(size=13), wraplength=550, justify="left").pack(side="left", padx=10, pady=8)

                ctk.CTkButton(
                    item,
                    text=f"Usar {tool.name}",
                    height=28,
                    font=ctk.CTkFont(size=12),
                    command=lambda t=tool: self._show_tool_details(t),
                ).pack(side="right", padx=10, pady=6)

            ctk.CTkFrame(group_card, height=6, fg_color="transparent").pack()

    def _show_doctor_view(self):
        """Muestra la evaluacion del estado del sistema y recursos locales."""
        for widget in self.content_area.winfo_children():
            widget.grid_forget()

        doc_frame = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        doc_frame.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(doc_frame, text="🏥 Estado del Sistema (Doctor)", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(5, 5))
        ctk.CTkLabel(doc_frame, text="Verificación de componentes necesarios para el soporte técnico:", text_color="gray70").pack(anchor="w", pady=(0, 15))

        # Cuadros de estado
        admin = is_admin()
        ps_available = bool(shutil.which("powershell") or shutil.which("pwsh"))

        net_ok = False
        try:
            urllib.request.urlopen("https://github.com", timeout=3)
            net_ok = True
        except Exception:
            pass

        items = [
            ("Sistema Operativo", f"{sys.platform} ({os.name})", True, "Compatible con Windows"),
            ("Permisos de Administrador", "Activo" if admin else "No activo", admin, "Requerido para ciertas reparaciones"),
            ("PowerShell", "Disponible" if ps_available else "No detectado", ps_available, "Necesario para scripts .ps1"),
            ("Conexión a Internet", "Conectado a GitHub" if net_ok else "Sin conexión", net_ok, "Permite descargar herramientas"),
        ]

        for title, val, ok, note in items:
            box = ctk.CTkFrame(doc_frame, corner_radius=10, fg_color=("gray90", "gray17"))
            box.pack(fill="x", pady=5, padx=5)

            color = "#2EA44F" if ok else "#D29922"
            ctk.CTkLabel(box, text="  ●  ", text_color=color, font=ctk.CTkFont(size=16)).pack(side="left", padx=(10, 0))
            ctk.CTkLabel(box, text=title, font=ctk.CTkFont(weight="bold", size=14), width=220, anchor="w").pack(side="left", padx=5, pady=12)
            ctk.CTkLabel(box, text=val, font=ctk.CTkFont(size=13), text_color=color, width=180, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(box, text=note, font=ctk.CTkFont(size=12), text_color="gray60").pack(side="left", padx=10)

        # Discos
        ctk.CTkLabel(doc_frame, text="Espacio en Almacenamiento:", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(15, 5), padx=5)
        for drive in ("C:", "D:"):
            if os.path.exists(drive):
                try:
                    usage = shutil.disk_usage(drive)
                    free_gb = usage.free / (1024**3)
                    total_gb = usage.total / (1024**3)
                    pct = (usage.used / usage.total)

                    d_card = ctk.CTkFrame(doc_frame, corner_radius=10, fg_color=("gray90", "gray17"))
                    d_card.pack(fill="x", pady=4, padx=5)

                    ctk.CTkLabel(d_card, text=f"Unidad {drive}", font=ctk.CTkFont(weight="bold", size=13), width=100, anchor="w").pack(side="left", padx=15, pady=10)
                    pbar = ctk.CTkProgressBar(d_card, width=280)
                    pbar.set(pct)
                    pbar.pack(side="left", padx=10)
                    ctk.CTkLabel(d_card, text=f"{free_gb:.1f} GB libres de {total_gb:.1f} GB").pack(side="left", padx=10)
                except Exception:
                    pass

    def _toggle_theme(self):
        if self.theme_switch.get():
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")

    def _clean_cache(self):
        resp = messagebox.askyesno("Limpiar Temporales", "¿Deseas borrar los archivos temporales y binarios descargados en caché?")
        if resp:
            cdir = config.cache_dir()
            if cdir.exists():
                shutil.rmtree(cdir)
                cdir.mkdir(parents=True, exist_ok=True)
            messagebox.showinfo("Limpieza Completada", "La memoria caché se ha limpiado correctamente.")


def main():
    app = RecursosApp()
    app.mainloop()


if __name__ == "__main__":
    main()
