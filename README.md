# Centro de Recursos Tecnológicos

Colección organizada de guías, herramientas y recursos para mantenimiento, reparación, activación y soporte informático.

> 🧰 **[Ver el Catálogo interactivo de herramientas](CATALOGO-HERRAMIENTAS.md)** — clasificadas por categoría, con contexto, utilidad y pasos de uso.

---

## ⚡ CLI `recursos-jeremialex04` (Acceso instantáneo en cualquier PC)

Puedes acceder a todas estas herramientas desde cualquier computadora con Windows ejecutando una sola línea en PowerShell:

```powershell
irm https://raw.githubusercontent.com/JeremiAlex04/Centro-de-Recursos-Tecnol-gicos/master/bootstrap.ps1 | iex
```

Una vez ejecutado, el comando queda registrado permanentemente en el sistema. Puedes escribir en cualquier terminal:
```powershell
recursos-jeremialex04
# o simplemente:
recursos
```

### Comandos principales

| Comando | Descripción |
|---|---|
| `recursos list` | Lista todas las herramientas con su categoría, nivel de riesgo y requisitos |
| `recursos list -c drivers` | Filtra por categoría (`sistema`, `software`, `drivers`, `almacenamiento`, etc.) |
| `recursos search "wifi"` | Búsqueda por síntomas o palabras clave (ignora tildes y mayúsculas) |
| `recursos info <id>` | Muestra ficha técnica, contexto, para qué sirve y pasos de uso detallados |
| `recursos run <id>` | Ejecuta la herramienta seleccionada con verificación de integridad SHA-256 |
| `recursos install <id>` | Descarga o instala un programa de soporte |
| `recursos diagnose` | **Asistente interactivo:** te guía según la falla del equipo y sugiere la solución |
| `recursos doctor` | Revisa privilegios de administrador, PowerShell, conexión y espacio en disco |
| `recursos docs --build` | Regenera automáticamente el archivo `CATALOGO-HERRAMIENTAS.md` desde los YAML |
| `recursos export-offline E:\` | Exporta todo el catálogo y binarios a un pendrive USB para emergencias sin internet |
| `recursos clean` | Limpia los binarios y archivos temporales descargados en caché |
| `recursos plugin list` | Gestiona módulos opcionales (ej.: activación de Windows/Office) |


---

## 🖥️ Aplicación de Escritorio Gráfica

Si prefieres una interfaz visual con ventanas, tarjetas interactivas y botones:

1. Haz doble clic en el archivo **Iniciar_Centro_Recursos.bat** (en la raíz del repositorio).
2. O escribe en la terminal: ecursos gui (o ecursos-gui).

### Características de la App de Escritorio:
- **Tarjetas visuales** con descripción clara de **cuándo y cómo aplicar** cada herramienta en soporte técnico.
- **Búsqueda en tiempo real**: filtra por síntomas (ej.: *wifi, lentitud, formateo, desinstalar*).
- **Asistente de diagnóstico integrado**: haz clic en el problema y te sugiere la herramienta exacta.
- **Evaluación de salud del PC (Doctor)**: monitorea memoria, discos C: y D:, internet y permisos de administrador.
- **Modo Oscuro / Claro** con diseño moderno nativo para Windows.
- **Ejecución y visor de guías** en ventana emergente con consola de progreso en vivo.

---

## Estructura

- [catalog/](catalog/) - Manifiestos YAML de cada herramienta (fuente única de verdad)
- [src/recursos/](src/recursos/) - Código fuente del sistema CLI en Python
- [Herramientas/](Herramientas/) - Utilidades y herramientas organizadas por categoría
- [Guia/](Guia/) - Guías paso a paso
- [Recursos/](Recursos/) - Enlaces/recursos complementarios
- [PC/](PC/) - Recursos originales relacionados con PC (ejecutables, paquetes, guías)
- [CELULARES/](CELULARES/) - Recursos para dispositivos móviles
- [OTROS/](OTROS/) - Otros recursos
- [public/](public/) - Recursos web (fuentes, etc.)

## Índice rápido

### Herramientas
- [ADB AppControl (Android)](Herramientas/Celulares/ADB-AppControl/README.md)
- [Drivers de impresoras (Zofti)](Herramientas/Impresoras/Drivers-Impresoras-Zofti/README.md)
- [IObit Driver Booster](Herramientas/Sistemas/Driver-Booster/README.md)
- [Chris Titus Tech Windows Utility](Herramientas/Sistemas/ChrisTitus-Tech-Utility/README.md)
- [Ninite](Herramientas/Sistemas/Ninite/README.md)
- [Microsoft Activation Script (MAS)](Herramientas/Activacion/Microsoft-Activation-Script-MAS/README.md)
- [Revo Uninstaller](Herramientas/Desinstalacion/Revo-Uninstaller/README.md)
- [KMS Lite (info)](Herramientas/Desbloquear/KMS-Lite-Info/README.md)

### Guías
- [Habilitar gpedit.msc](Guia/Sistema/Habilitar-GPEDIT-Local/README.md)
- [USB doble partición / diskpart](Guia/Almacenamiento/USB-Doble-Partition/README.md)

### Recursos
- [Versiones antiguas de SQL Server](Recursos/SQL/Versiones-SQL-Server-Antiguas/README.md)

### Otros (originales)
- [PC/](PC/) - Contiene ejecutables (Driver Booster, RevoUninProSetup), carpetas de desbloqueo/activación, guías .txt originales
- [OTROS/](OTROS/) - Drivers enlace, máquinas virtuales (.exe LFS), versiones SQL Server
- [CELULARES/](CELULARES/) - Guía ADB AppControl
- [public/fonts/](public/fonts/README.md)

## Notas de Seguridad y Uso
- Los binarios locales se verifican automáticamente mediante **checksum SHA-256**.
- Los plugins de activación están desactivados por defecto y requieren confirmación explícita del usuario (`recursos plugin enable activation`).
- Las modificaciones al sistema cuentan con advertencias de riesgo clasificadas (Bajo, Medio, Alto).
