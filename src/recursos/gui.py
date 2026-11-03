"""Interfaz Grafica de Usuario (GUI) para el Centro de Recursos Tecnologicos."""

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, filedialog
from typing import Optional

import customtkinter as ctk

from recursos import __version__, config
from recursos.catalog import filter_tools, load_catalog, search
from recursos.doctor import run_doctor
from recursos.models import Category, Risk, Tool
from recursos.offline import export_offline_bundle
from recursos.runner import RunError, SecurityError, execute

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CATEGORY_NAMES = {
    Category.sistema: "🖥️ Sistema",
    Category.software: "📦 Software",
    Category.drivers: "🔧 Drivers",
    Category.almacenamiento: "💾 Almacenamiento",
    Category.moviles: "📱 Móviles",
    Category.activacion: "🔑 Activación",
    Category.virtualizacion: "🗄️ Virtualización",
}

RISK_COLORS = {
    Risk.low: "#2EA44F",
    Risk.medium: "#E3B341",
    Risk.high: "#F85149",
}

RISK_TEXT = {
    Risk.low: "Riesgo Bajo",
    Risk.medium: "Riesgo Medio",
    Risk.high: "Riesgo Alto",
}


class ConsoleEmitter:
    """Emulador de consola Rich para capturar logs en la ventana GUI."""

    def __init__(self, callback):
        self.callback = callback

    def print(self, *args, **kwargs):
        text = " ".join(str(a) for a in args)
        # Limpiar tags simples de markup de rich
        import re
        clean_text = re.sub(r"\[/?.*?\]", "", text)
        self.callback(clean_text + "\n")


class ToolDetailDialog(ctk.CTkToplevel):
    def __init__(self, parent, tool: Tool, on_run):
        super().__init__(parent)
        self.tool = tool
        self.on_run = on_run

        self.title(f"{tool.name} - Detalles")
        self.geometry("680x600")
        self.minsize(550, 450)
        self.grab_set()

        # Encabezado
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text=tool.name,
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        )
        title_lbl.pack(fill="x")

        badges_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        badges_frame.pack(fill="x", pady=6)

        cat_badge = ctk.CTkLabel(
            badges_frame,
            text=CATEGORY_NAMES.get(tool.category, tool.category.value),
            fg_color="#1f6aa5",
            corner_radius=6,
            padx=10,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        cat_badge.pack(side="left", padx=(0, 8))

        risk_badge = ctk.CTkLabel(
            badges_frame,
            text=RISK_TEXT.get(tool.risk, tool.risk.value),
            fg_color=RISK_COLORS.get(tool.risk, "#888"),
            text_color="#ffffff",
            corner_radius=6,
            padx=10,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        risk_badge.pack(side="left", padx=(0, 8))

        if tool.requires_admin:
            admin_badge = ctk.CTkLabel(
                badges_frame,
                text="Requiere Admin",
                fg_color="#444444",
                corner_radius=6,
                padx=8,
                font=ctk.CTkFont(size=11),
            )
            admin_badge.pack(side="left", padx=(0, 8))

        # Contenido scrollable
        content_box = ctk.CTkScrollableFrame(self)
        content_box.pack(fill="both", expand=True, padx=20, pady=10)

        # Resumen
        res_title = ctk.CTkLabel(content_box, text="Resumen", font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
        res_title.pack(fill="x", pady=(5, 2))
        res_text = ctk.CTkLabel(content_box, text=tool.summary, wraplength=600, justify="left", anchor="w")
        res_text.pack(fill="x", pady=(0, 10))

        # Contexto
        if tool.context:
            ctx_title = ctk.CTkLabel(content_box, text="Contexto de uso", font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
            ctx_title.pack(fill="x", pady=(5, 2))
            ctx_text = ctk.CTkLabel(content_box, text=tool.context, wraplength=600, justify="left", anchor="w")
            ctx_text.pack(fill="x", pady=(0, 10))

        # Para que sirve
        if tool.purpose:
            purp_title = ctk.CTkLabel(content_box, text="¿Para qué sirve?", font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
            purp_title.pack(fill="x", pady=(5, 2))
            for item in tool.purpose:
                p_lbl = ctk.CTkLabel(content_box, text=f"• {item}", wraplength=580, justify="left", anchor="w")
                p_lbl.pack(fill="x", padx=10, pady=1)

        # Pasos
        if tool.steps:
            steps_title = ctk.CTkLabel(content_box, text="\nPasos de aplicación", font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
            steps_title.pack(fill="x", pady=(5, 2))
            for i, step in enumerate(tool.steps, 1):
                s_lbl = ctk.CTkLabel(content_box, text=f"{i}. {step}", wraplength=580, justify="left", anchor="w")
                s_lbl.pack(fill="x", padx=10, pady=2)

        # Advertencias
        if tool.warnings:
            warn_title = ctk.CTkLabel(content_box, text="\n⚠️ Advertencias importantes", font=ctk.CTkFont(size=14, weight="bold"), text_color="#F85149", anchor="w")
            warn_title.pack(fill="x", pady=(5, 2))
            for w in tool.warnings:
                w_lbl = ctk.CTkLabel(content_box, text=f"! {w}", wraplength=580, justify="left", text_color="#E3B341", anchor="w")
                w_lbl.pack(fill="x", padx=10, pady=1)

        # Botones de accion inferior
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)

        dry_btn = ctk.CTkButton(
            btn_frame,
            text="Simular (Dry-Run)",
            fg_color="#333333",
            hover_color="#444444",
            command=lambda: [self.destroy(), self.on_run(self.tool, dry_run=True)],
        )
        dry_btn.pack(side="left", padx=5)

        run_btn = ctk.CTkButton(
            btn_frame,
            text="Ejecutar / Abrir",
            fg_color="#2EA44F",
            hover_color="#2c974b",
            font=ctk.CTkFont(weight="bold"),
            command=lambda: [self.destroy(), self.on_run(self.tool, dry_run=False)],
        )
        run_btn.pack(side="right", padx=5)


class RecursosDesktopApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Centro de Recursos Tecnológicos")
        self.geometry("1100x720")
        self.minsize(850, 600)

        # Carga del catalogo
        try:
            self.tools = load_catalog()
        except Exception as e:
            messagebox.showerror("Error de Catálogo", f"No se pudo cargar el catálogo: {e}")
            self.tools = []

        self.selected_category: Optional[Category] = None
        self.search_query = ""

        # Layout principal: Barra lateral + Contenedor central
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()
        self._refresh_tools_grid()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(9, weight=1)

        # Logo / Titulo
        logo_label = ctk.CTkLabel(
            self.sidebar,
            text="🧰 Recursos TI",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        sub_label = ctk.CTkLabel(
            self.sidebar,
            text=f"v{__version__} • JeremiAlex04",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        sub_label.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

        # Seccion Categorias
        cat_label = ctk.CTkLabel(self.sidebar, text="CATEGORÍAS", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray")
        cat_label.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="w")

        self.cat_buttons = {}
        row = 3

        btn_all = ctk.CTkButton(
            self.sidebar,
            text="📂 Todas las herramientas",
            anchor="w",
            fg_color="#1f6aa5",
            command=lambda: self._select_category(None),
        )
        btn_all.grid(row=row, column=0, padx=15, pady=3, sticky="ew")
        self.cat_buttons["all"] = btn_all
        row += 1

        for cat in Category:
            name = CATEGORY_NAMES.get(cat, cat.value)
            btn = ctk.CTkButton(
                self.sidebar,
                text=name,
                anchor="w",
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                command=lambda c=cat: self._select_category(c),
            )
            btn.grid(row=row, column=0, padx=15, pady=2, sticky="ew")
            self.cat_buttons[cat.value] = btn
            row += 1

        # Herramientas de utilidad en sidebar inferior
        util_label = ctk.CTkLabel(self.sidebar, text="ACCIONES RÁPIDAS", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray")
        util_label.grid(row=row, column=0, padx=20, pady=(20, 5), sticky="w")
        row += 1

        diag_btn = ctk.CTkButton(
            self.sidebar,
            text="🩺 Asistente Diagnóstico",
            anchor="w",
            fg_color="#2b3b4b",
            hover_color="#36495d",
            command=self._open_diagnose_dialog,
        )
        diag_btn.grid(row=row, column=0, padx=15, pady=3, sticky="ew")
        row += 1

        doctor_btn = ctk.CTkButton(
            self.sidebar,
            text="🔍 Doctor del Sistema",
            anchor="w",
            fg_color="#2b3b4b",
            hover_color="#36495d",
            command=self._open_doctor_dialog,
        )
        doctor_btn.grid(row=row, column=0, padx=15, pady=3, sticky="ew")
        row += 1

        usb_btn = ctk.CTkButton(
            self.sidebar,
            text="💾 Exportar a USB",
            anchor="w",
            fg_color="#2b3b4b",
            hover_color="#36495d",
            command=self._open_export_usb,
        )
        usb_btn.grid(row=row, column=0, padx=15, pady=3, sticky="ew")
        row += 1

        # Tema / Configuracion abajo
        self.theme_switch = ctk.CTkSwitch(
            self.sidebar,
            text="Modo Oscuro",
            command=self._toggle_theme,
        )
        self.theme_switch.select()
        self.theme_switch.grid(row=10, column=0, padx=20, pady=20, sticky="s")

    def _build_main_area(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_rowconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # Barra superior con Buscador y contador
        top_bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        top_bar.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            top_bar,
            placeholder_text="🔍 Buscar herramienta por nombre, síntoma (ej. 'wifi', 'lento', 'impresora')...",
            height=38,
            font=ctk.CTkFont(size=13),
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", self._on_search_key)

        self.count_badge = ctk.CTkLabel(
            top_bar,
            text=f"{len(self.tools)} recursos",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("gray80", "gray25"),
            corner_radius=6,
            padx=12,
            height=38,
        )
        self.count_badge.grid(row=0, column=1)

        # Panel scrollable para las tarjetas
        self.cards_scroll = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        self.cards_scroll.grid(row=1, column=0, sticky="nsew")
        self.cards_scroll.grid_columnconfigure((0, 1), weight=1)

    def _select_category(self, cat: Optional[Category]):
        self.selected_category = cat
        for key, btn in self.cat_buttons.items():
            if (cat is None and key == "all") or (cat and key == cat.value):
                btn.configure(fg_color="#1f6aa5", text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=("gray10", "gray90"))
        self._refresh_tools_grid()

    def _on_search_key(self, event):
        self.search_query = self.search_entry.get().strip()
        self._refresh_tools_grid()

    def _refresh_tools_grid(self):
        # Limpiar tarjetas existentes
        for child in self.cards_scroll.winfo_children():
            child.destroy()

        # Filtrar herramientas
        filtered = self.tools
        if self.selected_category:
            filtered = filter_tools(filtered, category=self.selected_category)
        if self.search_query:
            filtered = search(filtered, self.search_query)

        self.count_badge.configure(text=f"{len(filtered)} recursos")

        if not filtered:
            empty_lbl = ctk.CTkLabel(
                self.cards_scroll,
                text="No se encontraron herramientas con los filtros actuales.",
                font=ctk.CTkFont(size=14),
                text_color="gray",
            )
            empty_lbl.grid(row=0, column=0, columnspan=2, pady=40)
            return

        # Renderizar tarjetas en rejilla (2 columnas)
        for idx, tool in enumerate(filtered):
            r = idx // 2
            c = idx % 2
            self._create_tool_card(tool, r, c)

    def _create_tool_card(self, tool: Tool, row: int, col: int):
        card = ctk.CTkFrame(self.cards_scroll, corner_radius=10, fg_color=("gray85", "gray20"))
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        # Encabezado de la tarjeta
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 4))

        title = ctk.CTkLabel(
            header,
            text=tool.name,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
            wraplength=320,
        )
        title.pack(side="left", fill="x", expand=True)

        risk_pill = ctk.CTkLabel(
            header,
            text=RISK_TEXT.get(tool.risk, tool.risk.value),
            fg_color=RISK_COLORS.get(tool.risk, "#888"),
            text_color="#ffffff",
            corner_radius=6,
            padx=6,
            font=ctk.CTkFont(size=10, weight="bold"),
        )
        risk_pill.pack(side="right")

        # Categoria e ID
        cat_info = ctk.CTkLabel(
            card,
            text=f"{CATEGORY_NAMES.get(tool.category, tool.category.value)}  •  ID: {tool.id}",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w",
        )
        cat_info.pack(fill="x", padx=12, pady=(0, 6))

        # Resumen breve
        summary = ctk.CTkLabel(
            card,
            text=tool.summary,
            font=ctk.CTkFont(size=12),
            wraplength=340,
            justify="left",
            anchor="w",
            height=40,
        )
        summary.pack(fill="x", padx=12, pady=(0, 10))

        # Barra inferior con botones
        action_bar = ctk.CTkFrame(card, fg_color="transparent")
        action_bar.pack(fill="x", padx=12, pady=(0, 12))

        detalles_btn = ctk.CTkButton(
            action_bar,
            text="Ver Detalles",
            width=90,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray40"),
            command=lambda t=tool: self._open_tool_details(t),
        )
        detalles_btn.pack(side="left")

        ejecutar_btn = ctk.CTkButton(
            action_bar,
            text="Ejecutar",
            width=90,
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1f6aa5",
            hover_color="#144f7c",
            command=lambda t=tool: self._run_tool(t, dry_run=False),
        )
        ejecutar_btn.pack(side="right")

    def _open_tool_details(self, tool: Tool):
        ToolDetailDialog(self, tool, on_run=self._run_tool)

    def _run_tool(self, tool: Tool, dry_run: bool = False):
        # Validacion previa de plugins para activacion
        if tool.category is Category.activacion and not config.plugin_enabled("activation"):
            confirm = messagebox.askyesno(
                "Plugin Deshabilitado",
                "Las herramientas de activación están deshabilitadas por defecto.\n"
                "¿Deseas habilitar el plugin 'activation' bajo tu responsabilidad legal?",
            )
            if confirm:
                config.set_plugin("activation", True)
            else:
                return

        # Ventana de ejecucion / consola
        exec_win = ctk.CTkToplevel(self)
        exec_win.title(f"Ejecutando: {tool.name}")
        exec_win.geometry("640x400")
        exec_win.grab_set()

        lbl = ctk.CTkLabel(
            exec_win,
            text=f"Salida de ejecución ({'Simulación Dry-Run' if dry_run else 'En proceso'})",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        lbl.pack(padx=15, pady=(15, 5), anchor="w")

        log_box = ctk.CTkTextbox(exec_win, font=ctk.CTkFont(family="Consolas", size=11))
        log_box.pack(fill="both", expand=True, padx=15, pady=10)

        def append_log(txt):
            log_box.insert("end", txt)
            log_box.see("end")

        emitter = ConsoleEmitter(append_log)

        def worker():
            try:
                execute(tool, dry_run=dry_run, assume_yes=True, console=emitter)
                append_log("\n[OK] Operación finalizada con éxito.")
            except (RunError, SecurityError) as e:
                append_log(f"\n[ERROR] {e}")
            except Exception as e:
                append_log(f"\n[ERROR INESPERADO] {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _open_diagnose_dialog(self):
        diag_win = ctk.CTkToplevel(self)
        diag_win.title("Asistente de Diagnóstico Técnico")
        diag_win.geometry("620x520")
        diag_win.grab_set()

        title = ctk.CTkLabel(
            diag_win,
            text="🩺 Asistente de Diagnóstico",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.pack(padx=20, pady=(20, 5), anchor="w")

        desc = ctk.CTkLabel(
            diag_win,
            text="Selecciona el problema principal que presenta el equipo informático:",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        desc.pack(padx=20, pady=(0, 15), anchor="w")

        scroll = ctk.CTkScrollableFrame(diag_win)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        from recursos.diagnose import DIAGNOSTIC_TREE
        from recursos.catalog import get_tool

        for group in DIAGNOSTIC_TREE:
            g_title = ctk.CTkLabel(scroll, text=group["title"], font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
            g_title.pack(fill="x", pady=(10, 4))

            for label, tool_id in group["options"]:
                btn = ctk.CTkButton(
                    scroll,
                    text=f"• {label}",
                    anchor="w",
                    fg_color=("gray85", "gray25"),
                    text_color=("black", "white"),
                    hover_color="#1f6aa5",
                    command=lambda tid=tool_id: [
                        diag_win.destroy(),
                        self._show_diagnose_result(tid),
                    ],
                )
                btn.pack(fill="x", pady=2, padx=5)

    def _show_diagnose_result(self, tool_id: str):
        tool = next((t for t in self.tools if t.id == tool_id), None)
        if tool:
            self._open_tool_details(tool)

    def _open_doctor_dialog(self):
        doc_win = ctk.CTkToplevel(self)
        doc_win.title("Doctor del Sistema")
        doc_win.geometry("600x420")
        doc_win.grab_set()

        lbl = ctk.CTkLabel(
            doc_win,
            text="🔍 Diagnóstico de Entorno y Sistema",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        lbl.pack(padx=20, pady=(20, 10), anchor="w")

        txt = ctk.CTkTextbox(doc_win, font=ctk.CTkFont(family="Consolas", size=12))
        txt.pack(fill="both", expand=True, padx=20, pady=10)

        emitter = ConsoleEmitter(lambda s: txt.insert("end", s))
        threading.Thread(target=lambda: run_doctor(emitter), daemon=True).start()

    def _open_export_usb(self):
        folder = filedialog.askdirectory(title="Selecciona la memoria USB o carpeta de destino")
        if folder:
            dest = Path(folder)
            try:
                export_offline_bundle(dest, ConsoleEmitter(print))
                messagebox.showinfo("Exportación Completada", f"Recursos exportados correctamente a:\n{dest}")
            except Exception as e:
                messagebox.showerror("Error de Exportación", f"No se pudo completar la exportación:\n{e}")

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
