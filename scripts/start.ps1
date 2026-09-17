$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path '.venv\Scripts\python.exe') -or -not (Test-Path 'frontend\dist\index.html')) {
    Write-Host 'Primero ejecuta setup.bat para instalar y compilar.'
    exit 1
}
try {
    $existing = Invoke-RestMethod 'http://127.0.0.1:8765/api/health' -TimeoutSec 2
    if ($existing.service -eq 'nexo-local') { Write-Host 'Nexo ya esta iniciado: http://127.0.0.1:8765'; exit 0 }
} catch {}
Write-Host 'Nexo esta disponible en http://127.0.0.1:8765'
Write-Host 'Primera entrada: copia el codigo de data\setup-key.txt y crea tu contrasena.'
Write-Host 'Deja esta ventana abierta. Ctrl+C detiene el servidor.'
& '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8765 --no-proxy-headers
exit $LASTEXITCODE
