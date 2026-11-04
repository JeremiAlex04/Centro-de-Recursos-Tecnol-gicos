<#
.SYNOPSIS
    Instalador y lanzador instantaneo de recursos-jeremialex04 para Windows.
.DESCRIPTION
    Permite usar el comando 'recursos-jeremialex04' o 'recursos' en cualquier equipo
    con solo ejecutar:
        irm https://raw.githubusercontent.com/JeremiAlex04/Centro-de-Recursos-Tecnol-gicos/prueba/bootstrap.ps1 | iex
#>

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ErrorActionPreference = "Stop"

$Repo = "JeremiAlex04/Centro-de-Recursos-Tecnol-gicos"
$AppName = "recursos-jeremialex04"
$InstallDir = Join-Path $env:LOCALAPPDATA $AppName
$ExePath = Join-Path $InstallDir "$AppName.exe"
$AliasPath = Join-Path $InstallDir "recursos.exe"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Centro de Recursos Tecnologicos (JeremiAlex04) " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Crear directorio de instalacion en LocalAppData
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

# 2. Descarga del binario portable
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
        Write-Host "[+] Descarga completada con exito." -ForegroundColor Green
    }
    catch {
        Write-Host "[-] No se encontro el binario compilado en GitHub Releases aun." -ForegroundColor Yellow
        Write-Host "[*] Si estas ejecutando localmente en tu proyecto, usando copia local..." -ForegroundColor Cyan
        
        $LocalBuild = Join-Path $PSScriptRoot "dist\$AppName.exe"
        if (Test-Path $LocalBuild) {
            Copy-Item -Path $LocalBuild -Destination $ExePath -Force
            Write-Host "[+] Copiado ejecutable local de dist\ a $InstallDir" -ForegroundColor Green
        } else {
            Write-Host "[!] El release en GitHub se esta procesando. Puedes iniciar la aplicacion localmente con:" -ForegroundColor Yellow
            Write-Host "    .\Iniciar_Centro_Recursos.bat" -ForegroundColor White
            return
        }
    }
}

# 3. Crear alias 'recursos.exe'
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
    Write-Host "[+] Registrado en PATH de Windows." -ForegroundColor Green
} else {
    $env:PATH = "$InstallDir;$env:PATH"
}

Write-Host "----------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "Iniciando Recursos Tecnologicos..." -ForegroundColor Green
Write-Host "----------------------------------------------------------" -ForegroundColor DarkGray

# 5. Iniciar la aplicacion
if (Test-Path $ExePath) {
    Start-Process -FilePath $ExePath
}
