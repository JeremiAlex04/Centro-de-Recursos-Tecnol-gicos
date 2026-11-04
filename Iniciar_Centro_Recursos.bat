@echo off
title Centro de Recursos Tecnologicos - GUI
chcp 65001 >nul

echo Iniciando interfaz grafica de escritorio...

if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\pythonw.exe" -m recursos.gui
) else (
    pythonw -m recursos.gui 2>nul || python -m recursos.gui
)

exit
