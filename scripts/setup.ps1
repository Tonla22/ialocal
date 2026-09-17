$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
Write-Host 'Instalando dependencias dentro del proyecto. No se cambia la configuracion de Windows.'
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno. Instala Python 3.12.' }
}
$requirements = if (Test-Path 'backend\requirements.lock.txt') { 'backend\requirements.lock.txt' } else { 'backend\requirements.txt' }
& '.\.venv\Scripts\python.exe' -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) { throw 'Fallo la instalacion de Python.' }
Push-Location frontend
try {
    if (Test-Path package-lock.json) { npm.cmd ci } else { npm.cmd install }
    if ($LASTEXITCODE -ne 0) { throw 'Fallo npm.' }
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la compilacion del frontend.' }
} finally { Pop-Location }
if (-not (Test-Path '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
Write-Host 'Listo. Ejecuta start.bat.'
