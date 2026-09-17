from dataclasses import dataclass
from typing import Callable
from pydantic import BaseModel, Field, ConfigDict
from . import files, terminal
from .. import database as db

class Params(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class FilePath(Params):
    path: str = Field(default='.', max_length=500)
    root: int = Field(default=0, ge=0)

class WritePath(FilePath):
    content: str = Field(max_length=100000)

class SourceDestination(Params):
    source: str = Field(max_length=500)
    destination: str = Field(max_length=500)
    root: int = Field(default=0, ge=0)

class SearchPath(FilePath):
    query: str = Field(min_length=1, max_length=200)

class Command(Params):
    command: str = Field(min_length=1, max_length=6000)

@dataclass
class Tool:
    name: str
    description: str
    parameters: type[BaseModel]
    permission: str
    function: Callable
    group: str = 'Archivos'

    def schema(self):
        return {'type': 'function', 'function': {'name': self.name, 'description': self.description,
                                                'parameters': self.parameters.model_json_schema()}}

registry = {}

def register(tool):
    if tool.name in registry:
        raise ValueError('Herramienta duplicada: ' + tool.name)
    registry[tool.name] = tool

for spec in [
    Tool('listar_archivos', 'Lista hasta 200 entradas de una carpeta autorizada. Rutas relativas.', FilePath, 'read', files.list_files),
    Tool('leer_archivo', 'Lee un archivo UTF-8 dentro de una carpeta autorizada (máximo 100 KB).', FilePath, 'read', files.read_file),
    Tool('buscar_archivos', 'Busca nombres de archivos, con límites de recorrido.', SearchPath, 'read', files.search_files),
    Tool('escribir_archivo', 'Crea o reemplaza un archivo UTF-8. Mostrar contenido antes de aprobar.', WritePath, 'write', files.write_file),
    Tool('crear_carpeta', 'Crea una carpeta dentro del espacio autorizado.', FilePath, 'write', files.make_directory),
    Tool('copiar_archivo', 'Copia un archivo sin sobrescribir el destino.', SourceDestination, 'write', files.copy_file),
    Tool('mover_archivo', 'Mueve un archivo sin sobrescribir el destino.', SourceDestination, 'write', files.move_file),
    Tool('powershell', 'Ejecuta PowerShell con privilegios del usuario. Siempre requiere aprobación; no está aislado a las carpetas autorizadas.', Command, 'always', terminal.powershell, 'Terminal'),
]:
    register(spec)

def initialize():
    for tool in registry.values():
        db.execute('INSERT OR IGNORE INTO tools VALUES (?,?,?)', (tool.name, tool.permission == 'read', tool.permission))

def enabled_tools():
    enabled = {r['name'] for r in db.rows('SELECT name FROM tools WHERE enabled=1')}
    return [t for t in registry.values() if t.name in enabled]
