<#
.SYNOPSIS
    Instalador y lanzador instantaneo de recursos-jeremialex04 para Windows.
.DESCRIPTION
    Permite usar el comando 'recursos-jeremialex04' o 'recursos' en cualquier equipo
    con solo ejecutar:
        irm https://raw.githubusercontent.com/JeremiAlex04/Centro-de-Recursos-Tecnol-gicos/prueba/bootstrap.ps1 | iex
#>

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Repo = "JeremiAlex04/Centro-de-Recursos-Tecnol-gicos"
$AppName = "recursos-jeremialex04"
$InstallDir = Join-Path $env:LOCALAPPDATA $AppName
$ExePath = Join-Path $InstallDir "$AppName.exe"
$AliasPath = Join-Path $InstallDir "recursos.exe"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Centro de Recursos Tecnologicos (JeremiAlex04) " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Crear directorio de instalacion en LocalAppData (no requiere privilegios elevados)
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

# 2. Descarga del binario portable desde GitHub Releases
$ReleaseUrl = "https://github.com/$Repo/releases/latest/download/$AppName.exe"
$NeedsDownload = $true

if (Test-Path $ExePath) {
    Write-Host "[*] Binario existente encontrado en: $ExePath" -ForegroundColor Green
    $NeedsDownload = $false
}

if ($NeedsDownload) {
    Write-Host "[*] Descargando version portable de $AppName..." -ForegroundColor Cyan
    try {
        Invoke-WebRequest -Uri $ReleaseUrl -OutFile $ExePath -UseBasicParsing
        Write-Host "[+] Descarga completada." -ForegroundColor Green
    }
    catch {
        Write-Host "[-] No se encontro un ejecutable precompilado en Releases." -ForegroundColor Yellow
        Write-Host "[*] Verificando si Python esta disponible en este equipo..." -ForegroundColor Cyan
        
        $PythonCmd = (Get-Command python -ErrorAction SilentlyContinue)
        if ($PythonCmd) {
            Write-Host "[+] Python detectado. Instalando paquete con pip..." -ForegroundColor Green
            & python -m pip install --quiet --upgrade "git+https://github.com/$Repo.git@prueba"
            $InstalledExe = (Get-Command $AppName -ErrorAction SilentlyContinue)
            if ($InstalledExe) {
                $ExePath = $InstalledExe.Source
            }
        }
        else {
            Write-Error "No se pudo obtener el ejecutable y Python no esta instalado. Verifica tu conexion a Internet."
            return
        }
    }
}

# 3. Crear alias 'recursos' si existe el .exe
if ((Test-Path $ExePath) -and (-not (Test-Path $AliasPath))) {
    try {
        Copy-Item -Path $ExePath -Destination $AliasPath -Force
    } catch {}
}

# 4. Agregar al PATH del usuario para que quede operativo permanentemente
$CurrentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($CurrentPath -notlike "*$InstallDir*") {
    Write-Host "[*] Registrando '$AppName' en las variables de entorno de usuario..." -ForegroundColor Cyan
    $NewPath = "$InstallDir;$CurrentPath"
    [Environment]::SetEnvironmentVariable("PATH", $NewPath, "User")
    $env:PATH = "$InstallDir;$env:PATH"
    Write-Host "[+] Registrado en PATH. Ahora puedes abrir cualquier CMD o PowerShell y escribir: $AppName" -ForegroundColor Green
} else {
    $env:PATH = "$InstallDir;$env:PATH"
}

Write-Host "----------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "Listo! Iniciando $AppName..." -ForegroundColor Green
Write-Host "----------------------------------------------------------" -ForegroundColor DarkGray

# 5. Ejecutar la ayuda inicial
if (Test-Path $ExePath) {
    & $ExePath
} else {
    & $AppName
}
