import re
from ..config import config
from .process import run_process

def classify(command):
    # Classification is informational; arbitrary shell commands ALWAYS require approval.
    if re.search(r'(?i)\b(remove-item|del|erase|format|rmdir|clear-disk|reset)\b', command):
        return 'destructiva'
    if re.search(r'(?i)\b(install|winget|choco|scoop|pip|npm)\b', command):
        return 'instalación'
    return 'comando del sistema: confirmación obligatoria'

async def powershell(command):
    return await run_process(['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive', '-Command',
        '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; ' + command], config.roots[0])
