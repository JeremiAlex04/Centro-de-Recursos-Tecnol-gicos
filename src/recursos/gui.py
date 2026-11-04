"""Interfaz Grafica de Usuario (GUI) Moderna, Ligera y Cloud-First.

Optimizada para acceso en la nube sin saturar el almacenamiento local.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from tkinter import messagebox, filedialog
from typing import Optional

import customtkinter as ctk

from recursos import __version__, config
from recursos.catalog import filter_tools, load_catalog, search
from recursos.doctor import run_doctor
from recursos.models import Category, Risk, SourceType, Tool
from recursos.offline import export_offline_bundle

# Configuracion de apariencia inicial
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Enlaces web oficiales para herramientas que son recursos en la nube
CLOUD_WEB_LINKS = {
    "ninite": "https://ninite.com/",
    "zofti-impresoras": "https://zofti.com/",
    "adb-appcontrol": "https://adbappcontrol.com/en/",
    "sql-antiguos": "https://zonasql.com/descargar-versiones-antiguas-de-sql-server",
    "driver-booster": "https://www.iobit.com/es/driver-booster.php",
    "revo-uninstaller": "https://www.revouninstaller.com/es/products/revo-uninstaller-pro/",
    "vmware-workstation": "https://www.vmware.com/products/desktop-hypervisors/workstation-pro",
    "mas": "https://massgrave.dev/",
    "winutil": "https://christitus.com/windows-tool/",
    "gpedit": "https://www.mediafire.com/file/wvq07imzsmfli6e/Group_Policy.bat/file",
}

CATEGORY_CONFIG = {
    Category.sistema: ("🖥️ Sistema", "#0ea5e9"),
    Category.software: ("📦 Software", "#10b981"),
    Category.drivers: ("🔧 Drivers", "#f59e0b"),
    Category.almacenamiento: ("💾 Almacenamiento", "#8b5cf6"),
    Category.moviles: ("📱 Móviles", "#10b981"),
    Category.activacion: ("🔑 Activación", "#ef4444"),
    Category.virtualizacion: ("🗄️ Virtualización", "#6366f1"),
}

SOURCE_BADGES = {
    SourceType.url: ("☁️ En la Nube", "#0284c7"),
    SourceType.script: ("⚡ Script Nube", "#8b5cf6"),
    SourceType.native_command: ("🛠️ Nativo Windows", "#059669"),
    SourceType.local_file: ("☁️ Nube / Portal", "#d97706"),
    SourceType.guide: ("📖 Guía Paso a Paso", "#4b5563"),
}

RISK_BADGES = {
    Risk.low: ("Bajo", "#16a34a"),
    Risk.medium: ("Medio", "#d97706"),
    Risk.high: ("Alto", "#dc2626"),
}


class ToolDetailDialog(ctk.CTkToplevel):
    """Ventana modal de detalles claros y pasos de uso."""

    def __init__(self, parent, tool: Tool, on_action):
        super().__init__(parent)
        self.tool = tool
        self.on_action = on_action

        self.title(f"{tool.name} — Información y Guía")
        self.geometry("640x560")
        self.minsize(500, 420)
        self.grab_set()

        # Banner superior
        banner = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=0)
        banner.pack(fill="x", padx=0, pady=0)

        title_lbl = ctk.CTkLabel(
            banner,
            text=tool.name,
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
        )
        title_lbl.pack(fill="x", padx=20, pady=(15, 6))

        # Badges
        pills_frame = ctk.CTkFrame(banner, fg_color="transparent")
        pills_frame.pack(fill="x", padx=20, pady=(0, 15))

        cat_title, cat_color = CATEGORY_CONFIG.get(tool.category, (tool.category.value, "#3b82f6"))
        self._pill(pills_frame, cat_title, cat_color)

        src_title, src_color = SOURCE_BADGES.get(tool.source.type, ("Nube", "#0284c7"))
        self._pill(pills_frame, src_title, src_color)

        risk_title, risk_color = RISK_BADGES.get(tool.risk, ("Riesgo", "#d97706"))
        self._pill(pills_frame, f"Riesgo {risk_title}", risk_color)

        if tool.requires_admin:
            self._pill(pills_frame, "🛡️ Requiere Admin", "#475569")

        # Contenido scrollable
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=10)

        # Resumen
        self._section_title(scroll, "📌 Resumen")
        ctk.CTkLabel(scroll, text=tool.summary, wraplength=560, justify="left", anchor="w", font=ctk.CTkFont(size=13)).pack(fill="x", pady=(0, 10))

        # Contexto
        if tool.context:
            self._section_title(scroll, "💡 Contexto de Aplicación")
            ctk.CTkLabel(scroll, text=tool.context, wraplength=560, justify="left", anchor="w", font=ctk.CTkFont(size=12)).pack(fill="x", pady=(0, 10))

        # Para que sirve
        if tool.purpose:
            self._section_title(scroll, "🎯 ¿Para qué sirve?")
            for p in tool.purpose:
                ctk.CTkLabel(scroll, text=f"  •  {p}", wraplength=550, justify="left", anchor="w", font=ctk.CTkFont(size=12)).pack(fill="x", pady=1)

        # Pasos de aplicacion
        if tool.steps:
            self._section_title(scroll, "📋 Pasos de Uso")
            for i, s in enumerate(tool.steps, 1):
                ctk.CTkLabel(scroll, text=f"  {i}. {s}", wraplength=550, justify="left", anchor="w", font=ctk.CTkFont(size=12)).pack(fill="x", pady=2)

        # Advertencias
        if tool.warnings:
            self._section_title(scroll, "⚠️ Advertencias Importantes", color="#ef4444")
            for w in tool.warnings:
                ctk.CTkLabel(scroll, text=f"  ! {w}", wraplength=550, justify="left", text_color=("#b91c1c", "#fca5a5"), anchor="w", font=ctk.CTkFont(size=12, weight="bold")).pack(fill="x", pady=1)

        # Barra inferior de acciones
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=15)

        close_btn = ctk.CTkButton(
            footer,
            text="Cerrar",
            fg_color=("gray75", "#334155"),
            text_color=("black", "white"),
            hover_color=("gray65", "#475569"),
            width=90,
            command=self.destroy,
        )
        close_btn.pack(side="left")

        # Boton de ejecucion / apertura
        action_btn = ctk.CTkButton(
            footer,
            text="⚡ Abrir Recurso / Ejecutar",
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(weight="bold"),
            command=lambda: [self.destroy(), self.on_action(self.tool)],
        )
        action_btn.pack(side="right")

    def _pill(self, parent, text, color):
        lbl = ctk.CTkLabel(
            parent,
            text=text,
            fg_color=color,
            text_color="#ffffff",
            corner_radius=5,
            padx=8,
            pady=2,
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        lbl.pack(side="left", padx=(0, 6))

    def _section_title(self, parent, text, color=None):
        lbl = ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=color,
            anchor="w",
        )
        lbl.pack(fill="x", pady=(10, 3))


class RecursosDesktopApp(ctk.CTk):
    """Aplicacion de escritorio visual, optimizada y ligera."""

    def __init__(self):
        super().__init__()

        self.title("Centro de Recursos Tecnológicos")
        self.geometry("1080x680")
        self.minsize(820, 560)

        # Cargar herramientas
        try:
            self.tools = load_catalog()
        except Exception:
            self.tools = []

        self.selected_category: Optional[Category] = None
        self.search_query = ""

        # Layout principal: Sidebar fijo + Contenedor de contenido
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_view()
        self._render_tools()

    def _build_sidebar(self):
        # Panel lateral con ancho limpio
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=("gray95", "#0f172a"))
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(2, weight=1)

        # 1. Cabecera del sidebar
        top_header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        top_header.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")

        logo = ctk.CTkLabel(
            top_header,
            text="🧰 Recursos TI",
            font=ctk.CTkFont(size=19, weight="bold"),
            text_color=("#0284c7", "#38bdf8"),
        )
        logo.pack(anchor="w")

        cloud_tag = ctk.CTkLabel(
            top_header,
            text="☁️ Recursos en la nube",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
        )
        cloud_tag.pack(anchor="w")

        # 2. Categorias (Scrollable compacto para que nunca se corte ninguna)
        self.cat_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.cat_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)

        self.cat_buttons = {}

        # Boton 'Todas'
        btn_all = ctk.CTkButton(
            self.cat_frame,
            text=f"📂 Todas ({len(self.tools)})",
            anchor="w",
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284c7",
            text_color="#ffffff",
            command=lambda: self._filter_by_category(None),
        )
        btn_all.pack(fill="x", pady=2)
        self.cat_buttons["all"] = btn_all

        for cat in Category:
            name, _ = CATEGORY_CONFIG.get(cat, (cat.value, "#3b82f6"))
            count = len([t for t in self.tools if t.category == cat])
            btn = ctk.CTkButton(
                self.cat_frame,
                text=f"{name} ({count})",
                anchor="w",
                height=30,
                font=ctk.CTkFont(size=12),
                fg_color="transparent",
                text_color=("gray20", "gray85"),
                hover_color=("gray85", "#1e293b"),
                command=lambda c=cat: self._filter_by_category(c),
            )
            btn.pack(fill="x", pady=1)
            self.cat_buttons[cat.value] = btn

        # 3. Acciones rapidas (Fijas en la parte inferior)
        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.grid(row=3, column=0, padx=12, pady=10, sticky="ew")

        ctk.CTkLabel(
            footer,
            text="HERRAMIENTAS",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("gray50", "gray50"),
            anchor="w",
        ).pack(fill="x", padx=4, pady=(5, 3))

        self._action_button(footer, "🩺 Asistente Diagnóstico", self._open_diagnose)
        self._action_button(footer, "🔍 Salud del Equipo (Doctor)", self._open_doctor)
        self._action_button(footer, "💾 Exportar a USB", self._export_usb)

        # Switch de tema
        self.theme_switch = ctk.CTkSwitch(
            footer,
            text="Modo Oscuro",
            font=ctk.CTkFont(size=11),
            command=self._toggle_theme,
        )
        self.theme_switch.select()
        self.theme_switch.pack(anchor="w", padx=6, pady=(10, 5))

    def _action_button(self, parent, text, cmd):
        btn = ctk.CTkButton(
            parent,
            text=text,
            anchor="w",
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=("gray85", "#1e293b"),
            text_color=("black", "white"),
            hover_color=("gray75", "#334155"),
            command=cmd,
        )
        btn.pack(fill="x", pady=2)

    def _build_main_view(self):
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=16, pady=14)
        self.main_area.grid_rowconfigure(1, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        # Barra superior con buscador y contador
        search_bar = ctk.CTkFrame(self.main_area, fg_color="transparent")
        search_bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        search_bar.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            search_bar,
            placeholder_text="🔍 Buscar herramienta o síntoma (ej.: wifi, sonido, usb, formateo, bloatware, licencia)...",
            height=36,
            font=ctk.CTkFont(size=13),
            corner_radius=8,
            border_width=1,
            border_color=("gray70", "#334155"),
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", self._on_search)

        self.counter_badge = ctk.CTkLabel(
            search_bar,
            text=f"{len(self.tools)} recursos",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("gray85", "#1e293b"),
            corner_radius=6,
            padx=12,
            height=36,
        )
        self.counter_badge.grid(row=0, column=1)

        # Area scrollable para tarjetas de herramientas
        self.cards_scroll = ctk.CTkScrollableFrame(self.main_area, fg_color="transparent")
        self.cards_scroll.grid(row=1, column=0, sticky="nsew")
        self.cards_scroll.grid_columnconfigure((0, 1), weight=1)

    def _filter_by_category(self, cat: Optional[Category]):
        self.selected_category = cat
        for key, btn in self.cat_buttons.items():
            if (cat is None and key == "all") or (cat and key == cat.value):
                btn.configure(fg_color="#0284c7", text_color="#ffffff", font=ctk.CTkFont(size=12, weight="bold"))
            else:
                btn.configure(fg_color="transparent", text_color=("gray20", "gray85"), font=ctk.CTkFont(size=12))
        self._render_tools()

    def _on_search(self, event):
        self.search_query = self.search_entry.get().strip()
        self._render_tools()

    def _render_tools(self):
        for child in self.cards_scroll.winfo_children():
            child.destroy()

        filtered = self.tools
        if self.selected_category:
            filtered = filter_tools(filtered, category=self.selected_category)
        if self.search_query:
            filtered = search(filtered, self.search_query)

        self.counter_badge.configure(text=f"{len(filtered)} disponibles")

        if not filtered:
            msg = ctk.CTkLabel(
                self.cards_scroll,
                text="No se encontraron herramientas con esos criterios de búsqueda.",
                font=ctk.CTkFont(size=14),
                text_color="gray",
            )
            msg.grid(row=0, column=0, columnspan=2, pady=50)
            return

        for idx, tool in enumerate(filtered):
            self._render_card(tool, row=idx // 2, col=idx % 2)

    def _render_card(self, tool: Tool, row: int, col: int):
        # Tarjeta limpia con contraste definido
        card = ctk.CTkFrame(
            self.cards_scroll,
            corner_radius=10,
            fg_color=("white", "#1e293b"),
            border_width=1,
            border_color=("gray85", "#334155"),
        )
        card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        # Fila superior de la tarjeta: Titulo y badge de riesgo
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=12, pady=(10, 2))

        title = ctk.CTkLabel(
            top_row,
            text=tool.name,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
            wraplength=310,
        )
        title.pack(side="left", fill="x", expand=True)

        r_text, r_color = RISK_BADGES.get(tool.risk, ("Riesgo", "#d97706"))
        risk_pill = ctk.CTkLabel(
            top_row,
            text=r_text,
            fg_color=r_color,
            text_color="#ffffff",
            corner_radius=4,
            padx=6,
            pady=1,
            font=ctk.CTkFont(size=10, weight="bold"),
        )
        risk_pill.pack(side="right")

        # Subtitulo con tipo de recurso (en la nube / nativo)
        sub_row = ctk.CTkFrame(card, fg_color="transparent")
        sub_row.pack(fill="x", padx=12, pady=(0, 4))

        src_text, src_color = SOURCE_BADGES.get(tool.source.type, ("Nube", "#0284c7"))
        badge = ctk.CTkLabel(
            sub_row,
            text=src_text,
            fg_color=src_color,
            text_color="#ffffff",
            corner_radius=4,
            padx=5,
            font=ctk.CTkFont(size=10, weight="bold"),
        )
        badge.pack(side="left")

        cat_name, _ = CATEGORY_CONFIG.get(tool.category, (tool.category.value, "#3b82f6"))
        cat_lbl = ctk.CTkLabel(
            sub_row,
            text=f"  {cat_name}",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
        )
        cat_lbl.pack(side="left")

        # Resumen breve
        summary = ctk.CTkLabel(
            card,
            text=tool.summary,
            font=ctk.CTkFont(size=12),
            wraplength=350,
            justify="left",
            anchor="w",
            text_color=("gray25", "gray80"),
            height=34,
        )
        summary.pack(fill="x", padx=12, pady=(0, 8))

        # Botones inferiores con alto contraste
        action_row = ctk.CTkFrame(card, fg_color="transparent")
        action_row.pack(fill="x", padx=12, pady=(0, 10))

        # Boton "Ver Guía / Info" con texto legible
        detalles_btn = ctk.CTkButton(
            action_row,
            text="📖 Guía / Pasos",
            width=100,
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("gray90", "#334155"),
            text_color=("#1f2937", "#f1f5f9"),
            hover_color=("gray80", "#475569"),
            command=lambda t=tool: ToolDetailDialog(self, t, self._execute_cloud_action),
        )
        detalles_btn.pack(side="left")

        # Boton primario segun tipo de recurso
        btn_label = "🌐 Abrir Web" if tool.source.type in (SourceType.url, SourceType.local_file) else "⚡ Ejecutar"
        exec_btn = ctk.CTkButton(
            action_row,
            text=btn_label,
            width=100,
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            text_color="#ffffff",
            command=lambda t=tool: self._execute_cloud_action(t),
        )
        exec_btn.pack(side="right")

    def _execute_cloud_action(self, tool: Tool):
        """Ejecucion Cloud-First: abre en la nube o ejecuta en memoria sin descargar gigabytes."""
        # 1. Herramientas de Activacion requieren confirmacion
        if tool.category is Category.activacion and not config.plugin_enabled("activation"):
            confirm = messagebox.askyesno(
                "Aviso de Licenciamiento",
                "Las herramientas de activación no son oficiales de Microsoft.\n\n"
                "¿Deseas habilitar y ejecutar esta herramienta bajo tu responsabilidad?",
            )
            if not confirm:
                return
            config.set_plugin("activation", True)

        # 2. Si es recurso Web o enlace Cloud
        cloud_url = CLOUD_WEB_LINKS.get(tool.id) or tool.source.url
        if cloud_url and (tool.source.type in (SourceType.url, SourceType.local_file)):
            webbrowser.open(cloud_url)
            return

        # 3. Si es script cloud (WinUtil, MAS, etc.) -> Ejecutar directamente en PowerShell sin almacenar en disco
        if tool.source.type is SourceType.script:
            script_url = tool.source.url
            if script_url:
                ps_cmd = f"irm {script_url} | iex"
                # Abrir una ventana de PowerShell limpia con el comando listo
                subprocess.Popen(["powershell", "-NoExit", "-Command", ps_cmd])
                return

        # 4. Si es comando nativo de Windows (diskpart, msiexec)
        if tool.source.type is SourceType.native_command:
            cmd = tool.source.command
            if cmd:
                subprocess.Popen(["cmd.exe", "/c", f"start {cmd}"])
                return

        # 5. Para guias o cualquier otro caso
        ToolDetailDialog(self, tool, lambda t: None)

    def _open_diagnose(self):
        """Asistente de diagnostico interactivo modal."""
        diag_win = ctk.CTkToplevel(self)
        diag_win.title("🩺 Asistente de Diagnóstico Rápido")
        diag_win.geometry("580x480")
        diag_win.grab_set()

        ctk.CTkLabel(
            diag_win,
            text="🩺 Asistente de Diagnóstico",
            font=ctk.CTkFont(size=17, weight="bold"),
        ).pack(padx=20, pady=(15, 4), anchor="w")

        ctk.CTkLabel(
            diag_win,
            text="Haz clic en el síntoma que tiene el equipo para abrir la solución:",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        ).pack(padx=20, pady=(0, 10), anchor="w")

        scroll = ctk.CTkScrollableFrame(diag_win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        from recursos.diagnose import DIAGNOSTIC_TREE
        for group in DIAGNOSTIC_TREE:
            g_title = ctk.CTkLabel(scroll, text=group["title"], font=ctk.CTkFont(size=12, weight="bold"), anchor="w", text_color=("#0284c7", "#38bdf8"))
            g_title.pack(fill="x", pady=(8, 2))

            for label, tool_id in group["options"]:
                btn = ctk.CTkButton(
                    scroll,
                    text=f"•  {label}",
                    anchor="w",
                    height=28,
                    fg_color=("gray90", "#1e293b"),
                    text_color=("black", "white"),
                    hover_color="#0284c7",
                    command=lambda tid=tool_id: [
                        diag_win.destroy(),
                        self._open_tool_by_id(tid),
                    ],
                )
                btn.pack(fill="x", pady=2, padx=4)

    def _open_tool_by_id(self, tool_id: str):
        target = next((t for t in self.tools if t.id == tool_id), None)
        if target:
            ToolDetailDialog(self, target, self._execute_cloud_action)

    def _open_doctor(self):
        """Diagnostico del entorno del PC."""
        doc_win = ctk.CTkToplevel(self)
        doc_win.title("🔍 Salud del Equipo (Doctor)")
        doc_win.geometry("560x380")
        doc_win.grab_set()

        ctk.CTkLabel(
            doc_win,
            text="🔍 Estado y Salud del Equipo",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(padx=20, pady=(15, 8), anchor="w")

        txt = ctk.CTkTextbox(doc_win, font=ctk.CTkFont(family="Consolas", size=11))
        txt.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        class LogCapture:
            def print(self, *args, **kwargs):
                import re
                s = " ".join(str(a) for a in args)
                clean = re.sub(r"\[/?.*?\]", "", s)
                txt.insert("end", clean + "\n")
                txt.see("end")

        threading.Thread(target=lambda: run_doctor(LogCapture()), daemon=True).start()

    def _export_usb(self):
        folder = filedialog.askdirectory(title="Selecciona la memoria USB o carpeta de destino")
        if folder:
            try:
                class QuietLog:
                    def print(self, *args, **kwargs):
                        pass
                export_offline_bundle(Path(folder), QuietLog())
                messagebox.showinfo("Exportación Completada", f"Recursos exportados correctamente a:\n{folder}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo exportar a USB: {e}")

    def _toggle_theme(self):
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")


def launch_gui():
    app = RecursosDesktopApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
