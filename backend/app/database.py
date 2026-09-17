import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from .config import config

@contextmanager
def connect():
    db = sqlite3.connect(config.path(config.database_path), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db
        db.commit()
    finally:
        db.close()

def init():
    config.path(config.database_path).parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY CHECK(id=1), password TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, csrf TEXT NOT NULL, expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, title TEXT NOT NULL, updated REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE, role TEXT, content TEXT, model TEXT, status TEXT, created REAL);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tools (name TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 0, permission TEXT NOT NULL DEFAULT 'ask');
        CREATE TABLE IF NOT EXISTS models (name TEXT PRIMARY KEY, details TEXT NOT NULL, updated REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, created REAL, run_id TEXT, tool TEXT, state TEXT, detail TEXT);
        CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, content TEXT NOT NULL, created REAL NOT NULL);
        ''')

def rows(sql, params=()):
    with connect() as db:
        return [dict(row) for row in db.execute(sql, params)]

def execute(sql, params=()):
    with connect() as db:
        return db.execute(sql, params).lastrowid

def setting(key, default=None):
    result = rows('SELECT value FROM settings WHERE key=?', (key,))
    return json.loads(result[0]['value']) if result else default

def set_setting(key, value):
    execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, json.dumps(value)))

def conversation():
    cid = uuid.uuid4().hex
    execute('INSERT INTO conversations VALUES (?,?,?)', (cid, 'Nueva conversación', time.time()))
    return cid

def message(cid, role, content, model='', status='complete'):
    execute('INSERT INTO messages (conversation_id,role,content,model,status,created) VALUES (?,?,?,?,?,?)',
            (cid, role, content, model, status, time.time()))
    execute('UPDATE conversations SET updated=? WHERE id=?', (time.time(), cid))

def audit(run_id, tool, state, detail):
    execute('INSERT INTO audit (created,run_id,tool,state,detail) VALUES (?,?,?,?,?)',
            (time.time(), run_id, tool, state, str(detail)[:12000]))
