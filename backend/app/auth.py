import hashlib
import hmac
import secrets
import time
from fastapi import HTTPException, Request
from . import database as db
from .config import config, ROOT

SETUP_FILE = ROOT / 'data' / 'setup-key.txt'

def prepare_setup():
    if not db.rows('SELECT id FROM users') and not SETUP_FILE.exists():
        SETUP_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETUP_FILE.write_text(secrets.token_urlsafe(32), encoding='utf-8')

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return salt + ':' + digest

def verify(password, stored):
    return hmac.compare_digest(password_hash(password, stored.split(':')[0]), stored)

def fingerprint(token):
    return hashlib.sha256(token.encode()).hexdigest()

def create_session(response):
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    db.execute('DELETE FROM sessions WHERE expires < ?', (time.time(),))
    db.execute('INSERT INTO sessions VALUES (?,?,?)', (fingerprint(token), csrf, time.time() + config.session_hours * 3600))
    response.set_cookie('local_session', token, httponly=True, secure=config.session_secure,
                        samesite='strict', max_age=config.session_hours * 3600, path='/')
    return {'csrf': csrf}

def require_session(request: Request):
    token = request.cookies.get('local_session', '')
    found = db.rows('SELECT * FROM sessions WHERE token=? AND expires>?', (fingerprint(token), time.time()))
    if not found:
        raise HTTPException(401, 'Iniciá sesión para continuar.')
    session = found[0]
    if request.method not in ('GET', 'HEAD') and not hmac.compare_digest(request.headers.get('x-csrf-token', ''), session['csrf']):
        raise HTTPException(403, 'Token CSRF inválido.')
    return session
