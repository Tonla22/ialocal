"""Run locally with the server stopped. No password or history is printed."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app import database as db
db.init()
if input('Servidor detenido. ¿Eliminar cuenta y sesiones? Escribí REINICIAR: ') == 'REINICIAR':
    with db.connect() as connection:
        connection.execute('DELETE FROM sessions')
        connection.execute('DELETE FROM users')
    print('Cuenta reiniciada. Al iniciar se generará data/setup-key.txt. Historial conservado.')
