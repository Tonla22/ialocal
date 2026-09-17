$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$expectedPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
$servers = Get-CimInstance Win32_Process | Where-Object {
    $_.ExecutablePath -eq $expectedPython -and
    $_.CommandLine -match 'uvicorn app\.main:app' -and
    $_.CommandLine -match '--port 8765'
}
if (-not $servers) { Write-Host 'No se encontro una instancia de Nexo en el puerto 8765.'; exit 0 }
foreach ($server in $servers) { & taskkill.exe /PID $server.ProcessId /T /F }
Write-Host 'Nexo detenido. Esto no deshace acciones ya ejecutadas. Usa STOP AGENT antes de cerrar si hay una accion activa.'
