<#
.SYNOPSIS
  Instalador para Windows 10/11 de los selectores de fondos.

.DESCRIPTION
  - Comprueba Python (3.9 o superior; recomendado 3.12).
  - Crea un entorno virtual dentro del proyecto (.venv).
  - Instala las dependencias de requirements.txt.
  - Comprueba Wallpaper Engine y Lively Wallpaper.
  No necesita permisos de administrador y no cambia ninguna configuración
  del sistema.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\instalar_windows.ps1
  (la política Bypass vale solo para esta ejecución; no se cambia en el sistema)
#>
param([switch]$Yes)

$ErrorActionPreference = 'Continue'
$Raiz = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Raiz '.venv'
$Problemas = 0

function Ok($t)    { Write-Host "  [ OK ]   $t" -ForegroundColor Green }
function Aviso($t) { Write-Host "  [AVISO]  $t" -ForegroundColor Yellow }
function Falta($t) { Write-Host "  [FALTA]  $t" -ForegroundColor Red; $script:Problemas++ }
function Preguntar($t) {
    if ($Yes) { return $true }
    $r = Read-Host "$t [s/N]"
    return ($r -match '^(s|si|sí|y|yes)$')
}

Write-Host "== Selectores de fondos: instalación para Windows =="

# --- Python -------------------------------------------------------------
function Probar-Python($exe, $extra) {
    try {
        & $exe @extra -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

$PyExe = $null
$PyArgs = @()
if ((Get-Command py -ErrorAction SilentlyContinue) -and (Probar-Python 'py' @('-3'))) {
    $PyExe = 'py'; $PyArgs = @('-3')
} elseif ((Get-Command python -ErrorAction SilentlyContinue) -and (Probar-Python 'python' @())) {
    $PyExe = 'python'
}

if (-not $PyExe) {
    Falta "No se encontró Python 3.9 o superior."
    Write-Host "         Instálalo (recomendado 3.12) desde https://www.python.org/downloads/windows/"
    Write-Host "         y marca 'Add python.exe to PATH'. Luego vuelve a ejecutar este script."
    exit 1
}
$version = & $PyExe @PyArgs -c "import platform; print(platform.python_version())"
Ok "Python $version"

# --- Entorno virtual ---------------------------------------------------------
$PyVenv = Join-Path $Venv 'Scripts\python.exe'
if (Test-Path $PyVenv) {
    Ok "Entorno virtual existente: $Venv (se reutiliza)"
} else {
    if (Preguntar "¿Crear el entorno virtual en $Venv?") {
        & $PyExe @PyArgs -m venv $Venv
        if ($LASTEXITCODE -eq 0) { Ok "Entorno virtual creado" }
        else { Falta "No se pudo crear el entorno virtual"; exit 1 }
    } else {
        Write-Host "Cancelado. No se cambió nada."; exit 0
    }
}

if (Preguntar "¿Instalar/actualizar dependencias (requirements.txt)?") {
    & $PyVenv -m pip install -r (Join-Path $Raiz 'requirements.txt')
    if ($LASTEXITCODE -eq 0) { Ok "Dependencias instaladas" }
    else { Falta "Falló pip. Revisa tu conexión y vuelve a intentarlo." }
}

# --- ffmpeg (opcional) ------------------------------------------------------
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) { Ok "ffmpeg encontrado" }
else { Aviso "ffmpeg no encontrado: los vídeos mostrarán un cuadro gris en vez de su miniatura. Opcional: winget install Gyan.FFmpeg" }

# --- Wallpaper Engine / Lively ----------------------------------------------
$we = $null
$raicesSteam = @(
    "${env:ProgramFiles(x86)}\Steam",
    "$env:ProgramFiles\Steam"
)
try {
    $s = (Get-ItemProperty 'HKCU:\Software\Valve\Steam' -ErrorAction Stop).SteamPath
    if ($s) { $raicesSteam += ($s -replace '/', '\') }
} catch { }
foreach ($r in $raicesSteam) {
    foreach ($n in 'wallpaper64.exe', 'wallpaper32.exe') {
        $p = Join-Path $r "steamapps\common\wallpaper_engine\$n"
        if (-not $we -and (Test-Path $p)) { $we = $p }
    }
}
if ($we) { Ok "Wallpaper Engine: $we" }
else { Aviso "Wallpaper Engine no encontrado en las rutas habituales de Steam (puedes indicar la ruta en la configuración, tecla F2)." }

$lively = $null
foreach ($p in @("$env:LOCALAPPDATA\Programs\Lively Wallpaper\Lively.exe",
                 "$env:ProgramFiles\Lively Wallpaper\Lively.exe")) {
    if (-not $lively -and (Test-Path $p)) { $lively = $p }
}
if (-not $lively) {
    $c = Get-Command livelycu -ErrorAction SilentlyContinue
    if ($c) { $lively = $c.Source }
}
if ($lively) { Ok "Lively Wallpaper: $lively" }
else { Aviso "Lively Wallpaper no encontrado (alternativa gratuita: https://github.com/rocksdanister/lively)." }

if (-not $we -and -not $lively) {
    Falta "No hay ni Wallpaper Engine ni Lively: instala uno de los dos para poder aplicar fondos."
}

Write-Host ""
& $PyVenv (Join-Path $Raiz 'scripts\verificar_dependencias.py')

Write-Host ""
if ($Problemas -eq 0) { Write-Host "Listo. Para abrir un selector:" }
else { Write-Host "Hay $Problemas punto(s) por resolver (arriba). Después, para abrir un selector:" }
Write-Host "  $PyVenv $Raiz\src\main.py circular"
Write-Host "  $PyVenv $Raiz\src\main.py hexagonal"
