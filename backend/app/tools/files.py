import os
import shutil
from pathlib import Path
from ..config import config

def safe_path(value: str, root: int = 0):
    if root < 0 or root >= len(config.roots):
        raise ValueError('Carpeta autorizada inexistente.')
    base = config.roots[root]
    raw = Path(value)
    if raw.is_absolute() or '..' in raw.parts or ':' in value or value.startswith(('\\', '/')):
        raise ValueError('Usá una ruta relativa dentro de la carpeta autorizada.')
    # Reject symlinks, Windows junctions and other reparse points before resolving.
    current = base
    for component in [base, *[base.joinpath(*raw.parts[:i]) for i in range(1, len(raw.parts)+1)]]:
        if component.exists() or component.is_symlink():
            st = component.lstat()
            if component.is_symlink() or getattr(st, 'st_file_attributes', 0) & 0x400:
                raise ValueError('No se permiten enlaces o puntos de reanálisis.')
    path = (base / raw).resolve()
    if not path.is_relative_to(base):
        raise ValueError('Ruta fuera de la carpeta autorizada.')
    if path.exists() and path.is_file() and path.stat().st_nlink > 1:
        raise ValueError('No se permiten enlaces duros.')
    return path

def list_files(path='.', root=0):
    base = safe_path(path, root)
    if not base.is_dir():
        raise ValueError('No es una carpeta.')
    result = []
    for item in sorted(base.iterdir(), key=lambda p: p.name.lower()):
        if len(result) >= 200:
            break
        try:
            checked = safe_path(str(item.relative_to(config.roots[root])), root)
            result.append({'name': item.name, 'directory': checked.is_dir(), 'bytes': checked.stat().st_size})
        except (ValueError, OSError):
            continue
    return {'entries': result, 'limit': 200}

def read_file(path, root=0):
    file = safe_path(path, root)
    with file.open('rb') as stream:
        content = stream.read(100001)
    if len(content) > 100000:
        raise ValueError('Archivo demasiado grande. Máximo 100 KB.')
    if b'\x00' in content:
        raise ValueError('Solo se pueden leer archivos de texto.')
    return {'path': path, 'content': content.decode('utf-8')}

def write_file(path, content, root=0):
    if len(content.encode('utf-8')) > 100000:
        raise ValueError('Máximo 100 KB por escritura.')
    file = safe_path(path, root)
    file.write_text(content, encoding='utf-8')
    return {'written': path}

def make_directory(path, root=0):
    safe_path(path, root).mkdir(parents=True, exist_ok=True)
    return {'created': path}

def copy_file(source, destination, root=0):
    src, dst = safe_path(source, root), safe_path(destination, root)
    if dst.exists():
        raise ValueError('El destino ya existe; no se sobrescribe.')
    if not src.is_file() or src.stat().st_size > 10_000_000:
        raise ValueError('Solo archivos de hasta 10 MB.')
    shutil.copyfile(src, dst)
    return {'copied': destination}

def move_file(source, destination, root=0):
    src, dst = safe_path(source, root), safe_path(destination, root)
    if not src.is_file() or dst.exists():
        raise ValueError('Solo archivos; el destino debe ser nuevo.')
    src.rename(dst)
    return {'moved': destination}

def search_files(query, path='.', root=0):
    base = safe_path(path, root)
    results = []
    visited = 0
    for parent, directories, names in os.walk(base, followlinks=False):
        valid_dirs = []
        for name in directories:
            try:
                safe_path(str((Path(parent)/name).relative_to(config.roots[root])), root)
                valid_dirs.append(name)
            except (ValueError, OSError):
                pass
        directories[:] = valid_dirs
        for name in names:
            visited += 1
            if query.casefold() in name.casefold():
                relative = str((Path(parent)/name).relative_to(config.roots[root]))
                try:
                    safe_path(relative, root)
                    results.append(relative)
                except (ValueError, OSError):
                    pass
            if len(results) >= 100 or visited >= 5000:
                return {'paths': results, 'truncated': True}
    return {'paths': results, 'truncated': False}
