"""Generador del catalogo Markdown a partir del manifiesto."""

from __future__ import annotations

from recursos.models import Category, Risk, Tool

TITLES = {
    Category.sistema: "Sistema y configuracion de Windows",
    Category.software: "Instalacion y desinstalacion de software",
    Category.drivers: "Drivers y controladores",
    Category.almacenamiento: "Almacenamiento",
    Category.moviles: "Dispositivos moviles",
    Category.activacion: "Activacion y licenciamiento",
    Category.virtualizacion: "Bases de datos y virtualizacion",
}
RISK = {Risk.low: "bajo", Risk.medium: "medio", Risk.high: "alto"}


def build_markdown(tools: list[Tool]) -> str:
    out = [
        "# Catalogo de herramientas (generado)",
        "",
        "> Archivo generado con `recursos-jeremialex04 docs --build`. No editar a mano: "
        "modifica los YAML de `catalog/`.",
        "",
    ]
    for cat in Category:
        group = [t for t in tools if t.category is cat]
        if not group:
            continue
        out += [f"## {TITLES[cat]}", ""]
        for t in sorted(group, key=lambda x: x.name):
            out += [
                f"### {t.name}",
                "",
                f"`{t.id}` | riesgo **{RISK[t.risk]}** | admin: {'si' if t.requires_admin else 'no'} | "
                f"internet: {'si' if t.requires_internet else 'no'} | licencia: {t.license}",
                "",
                t.summary,
                "",
            ]
            if t.context:
                out += [f"**Contexto:** {t.context}", ""]
            if t.purpose:
                out += ["**Para que sirve:**"] + [f"- {p}" for p in t.purpose] + [""]
            if t.steps:
                out += ["**Como usarla:**"] + [f"{i}. {s}" for i, s in enumerate(t.steps, 1)] + [""]
            for w in t.warnings:
                out += [f"> **Aviso:** {w}", ""]
            out += [f"Uso: `recursos-jeremialex04 info {t.id}` · `recursos-jeremialex04 run {t.id}`", ""]
    return "\n".join(out)
