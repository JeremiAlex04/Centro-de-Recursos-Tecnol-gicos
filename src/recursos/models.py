"""Esquema del manifiesto de herramientas (fuente unica de verdad)."""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Category(str, Enum):
    sistema = "sistema"
    software = "software"
    drivers = "drivers"
    almacenamiento = "almacenamiento"
    moviles = "moviles"
    activacion = "activacion"
    virtualizacion = "virtualizacion"


class Risk(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class SourceType(str, Enum):
    local_file = "local_file"      # archivo del repositorio (verificado con SHA-256)
    url = "url"                    # sitio web: solo se abre en el navegador
    script = "script"              # script remoto: descargar -> revisar -> confirmar
    native_command = "native_command"  # comando nativo de Windows
    guide = "guide"                # solo pasos informativos


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: SourceType
    path: Optional[str] = None
    url: Optional[str] = None
    command: Optional[str] = None
    sha256: Optional[str] = None

    @model_validator(mode="after")
    def _check(self) -> "Source":
        if self.type is SourceType.local_file:
            if not self.path:
                raise ValueError("local_file requiere 'path'")
            if not self.sha256 or not re.fullmatch(r"[0-9a-fA-F]{64}", self.sha256):
                raise ValueError("local_file requiere un 'sha256' valido (64 hex)")
        if self.type in (SourceType.url, SourceType.script) and not (self.url or "").startswith(
            "https://"
        ):
            raise ValueError(f"{self.type.value} requiere 'url' con https://")
        if self.type is SourceType.native_command and not self.command:
            raise ValueError("native_command requiere 'command'")
        return self


class Tool(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str
    category: Category
    summary: str
    context: str = ""
    purpose: list[str] = []
    tags: list[str] = []
    symptoms: list[str] = []
    risk: Risk
    requires_admin: bool = False
    requires_internet: bool = False
    license: str = "free"
    source: Source
    steps: list[str] = []
    warnings: list[str] = []
    docs: Optional[str] = None
