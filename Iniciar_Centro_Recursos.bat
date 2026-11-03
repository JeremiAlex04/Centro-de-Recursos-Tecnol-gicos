@echo off
title Centro de Recursos Tecnologicos
chcp 65001 >nul
cd /d "%~dp0"

:: Verificar si existe el entorno virtual con las dependencias
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" -m recursos.gui.app
) else if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" -m recursos.gui.app
) else (
    echo Iniciando aplicacion de escritorio...
    python -m recursos.gui.app
)
