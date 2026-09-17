"""Disposable review instance; never modifies the user's account/database."""
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend'))
from app.config import config
config.app_origin='http://127.0.0.1:8766'
config.database_path=str(root/'data'/'verification.sqlite3')
config.authorized_roots=str(root/'data'/'verification-workspace')
from app import auth, database as db
auth.SETUP_FILE=root/'data'/'verification-setup-key.txt'
db.init()
db.execute('INSERT OR IGNORE INTO users VALUES (1,?)',(auth.password_hash('Verification-local-2026!'),))
from app.main import app
import uvicorn
uvicorn.run(app,host='127.0.0.1',port=8766,proxy_headers=False)
