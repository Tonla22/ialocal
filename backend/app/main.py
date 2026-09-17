import asyncio
import base64
import io
import json
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from urllib.parse import urlsplit
from PIL import Image
from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field, ConfigDict
from .config import config, ROOT
from . import auth, database as db
from .agent import agent, Run
from .tools.registry import registry, initialize
from .providers.ollama import provider
from .voice import stt
from .computer_control import STATUS as COMPUTER_STATUS

@asynccontextmanager
async def lifespan(app):
    db.init()
    for root in config.roots:
        root.mkdir(parents=True, exist_ok=True)
    auth.prepare_setup()
    initialize()
    yield
    await agent.stop()

app = FastAPI(title='Nexo · IA local', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
hostname = urlsplit(config.app_origin).hostname
app.add_middleware(TrustedHostMiddleware, allowed_hosts=list({'localhost','127.0.0.1', hostname}))
origins = {config.app_origin, 'http://localhost:8765', 'http://127.0.0.1:8765'}

@app.middleware('http')
async def boundary(request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        if request.headers.get('origin') not in origins or request.headers.get('x-local-app') != '1':
            return JSONResponse({'detail': 'Origen no autorizado.'}, status_code=403)
    length = request.headers.get('content-length')
    if length and (not length.isdigit() or int(length) > 15_000_000):
        return JSONResponse({'detail': 'Solicitud demasiado grande.'}, status_code=413)
    # Enforce the same limit for chunked uploads before JSON/multipart parsing.
    received = 0
    original_receive = request._receive
    async def limited_receive():
        nonlocal received
        message = await original_receive()
        received += len(message.get('body', b''))
        if received > 15_000_000:
            raise HTTPException(413, 'Solicitud demasiado grande.')
        return message
    request._receive = limited_receive
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    if request.url.path.startswith('/api'):
        response.headers['Cache-Control'] = 'no-store'
    return response

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Credentials(StrictModel):
    password: str = Field(min_length=12, max_length=200)
    setup_key: str = Field(default='', max_length=200)

attempts = []

@app.get('/api/auth/status')
def auth_status():
    return {'setup_required': not bool(db.rows('SELECT id FROM users'))}

@app.post('/api/auth/login')
def login(body: Credentials, response: Response):
    now = time.time()
    attempts[:] = [x for x in attempts if now - x < 60]
    if len(attempts) >= 5:
        raise HTTPException(429, 'Esperá un minuto antes de volver a intentar.')
    attempts.append(now)
    users = db.rows('SELECT password FROM users WHERE id=1')
    if not users:
        if not auth.SETUP_FILE.exists() or not secrets.compare_digest(body.setup_key.strip(), auth.SETUP_FILE.read_text().strip()):
            raise HTTPException(403, 'Código de instalación incorrecto. Consultá data/setup-key.txt.')
        try:
            db.execute('INSERT INTO users VALUES (1, ?)', (auth.password_hash(body.password),))
        except Exception:
            raise HTTPException(409, 'La cuenta ya fue creada.')
        auth.SETUP_FILE.unlink(missing_ok=True)
    elif not auth.verify(body.password, users[0]['password']):
        raise HTTPException(401, 'Contraseña incorrecta.')
    attempts.clear()
    return auth.create_session(response)

@app.get('/api/auth/me')
def me(session=Depends(auth.require_session)):
    return {'csrf': session['csrf']}

@app.post('/api/auth/logout')
async def logout(response: Response, session=Depends(auth.require_session)):
    await agent.stop()
    db.execute('DELETE FROM sessions WHERE token=?', (session['token'],))
    response.delete_cookie('local_session', path='/')
    return {'ok': True}

@app.get('/api/health')
def health():
    return {'backend': True, 'service': 'nexo-local'}

@app.get('/api/models', dependencies=[Depends(auth.require_session)])
async def models():
    try:
        installed = await provider.models()
        for model in installed:
            db.execute('INSERT OR REPLACE INTO models VALUES (?,?,?)', (model['name'], json.dumps(model), time.time()))
        return {'online': True, 'models': installed}
    except Exception:
        return {'online': False, 'models': [], 'error': 'Ollama no responde en ' + config.ollama_url}

@app.get('/api/conversations', dependencies=[Depends(auth.require_session)])
def conversations():
    return db.rows('SELECT * FROM conversations ORDER BY updated DESC')

@app.post('/api/conversations', dependencies=[Depends(auth.require_session)])
def new_conversation():
    return {'id': db.conversation()}

@app.get('/api/conversations/{cid}/messages', dependencies=[Depends(auth.require_session)])
def messages(cid: str):
    return db.rows('SELECT * FROM messages WHERE conversation_id=? ORDER BY id', (cid,))

@app.delete('/api/conversations/{cid}', dependencies=[Depends(auth.require_session)])
def delete_conversation(cid: str):
    if agent.current and agent.current.cid == cid:
        raise HTTPException(409, 'Detené la generación antes de borrar esta conversación.')
    db.execute('DELETE FROM conversations WHERE id=?', (cid,))
    return {'ok': True}

class Settings(StrictModel):
    model: str = Field(max_length=200)
    max_iterations: int = Field(ge=1, le=12)
    confirm_writes: bool
    tools_disabled: bool
    auto_voice: bool

@app.get('/api/settings', dependencies=[Depends(auth.require_session)])
def settings():
    return {'model': db.setting('model', config.ollama_model), 'max_iterations': db.setting('max_iterations', config.max_iterations),
            'confirm_writes': db.setting('confirm_writes', True), 'tools_disabled': db.setting('tools_disabled', False),
            'auto_voice': db.setting('auto_voice', False), 'roots': [str(x) for x in config.roots],
            'vision': config.vision_enabled, 'stt': stt.available(), 'computer': COMPUTER_STATUS}

@app.put('/api/settings', dependencies=[Depends(auth.require_session)])
async def update_settings(body: Settings):
    if body.tools_disabled:
        await agent.stop()
    for key, value in body.model_dump().items():
        db.set_setting(key, value)
    return settings()

@app.get('/api/tools', dependencies=[Depends(auth.require_session)])
def tools():
    saved = {x['name']: x for x in db.rows('SELECT * FROM tools')}
    return [{'name': t.name, 'description': t.description, 'permission': t.permission, 'group': t.group,
             'parameters': t.parameters.model_json_schema(), 'enabled': bool(saved.get(t.name, {}).get('enabled'))} for t in registry.values()]

class Toggle(StrictModel):
    enabled: bool

@app.put('/api/tools/{name}', dependencies=[Depends(auth.require_session)])
async def toggle_tool(name: str, body: Toggle):
    if name not in registry:
        raise HTTPException(404, 'Herramienta desconocida.')
    if not body.enabled:
        await agent.stop()
    db.execute('UPDATE tools SET enabled=? WHERE name=?', (body.enabled, name))
    db.audit('', name, 'enabled' if body.enabled else 'disabled', 'Configuración del usuario')
    return {'ok': True}

@app.get('/api/system', dependencies=[Depends(auth.require_session)])
def system():
    current = agent.current
    return {'backend': True, 'agent': current.state if current else 'En espera', 'run_id': current.id if current else None,
            'active_model': current.model if current else db.setting('model', config.ollama_model),
            'approval': current.approval if current else None, 'logs': db.rows('SELECT * FROM audit ORDER BY id DESC LIMIT 80'),
            'computer': COMPUTER_STATUS, 'stt': stt.available()}

@app.post('/api/agent/stop', dependencies=[Depends(auth.require_session)])
async def stop():
    return await agent.stop()

class Decision(StrictModel):
    approved: bool

@app.post('/api/approvals/{approval_id}')
async def approve(approval_id: str, body: Decision, session=Depends(auth.require_session)):
    run = agent.current
    if not run or run.session != session['token'] or not run.approval or run.approval['id'] != approval_id or not run.decision or run.decision.done():
        raise HTTPException(409, 'La aprobación ya no está vigente o pertenece a otra sesión.')
    run.decision.set_result(body.approved)
    return {'ok': True}

class ChatRequest(StrictModel):
    conversation_id: str
    text: str = Field(min_length=1, max_length=16000)
    model: str = Field(min_length=1, max_length=200)
    mode: str = Field(pattern='^(chat|agent)$')
    images: list[str] = Field(default_factory=list, max_length=3)

def validate_images(images):
    if not images:
        return []
    if not config.vision_enabled:
        raise HTTPException(400, 'Visión deshabilitada.')
    output = []
    for encoded in images:
        try:
            data = base64.b64decode(encoded, validate=True)
            if len(data) > 4_000_000:
                raise ValueError('Máximo 4 MB por imagen.')
            with Image.open(io.BytesIO(data)) as im:
                if im.width * im.height > 20_000_000:
                    raise ValueError('Demasiados píxeles.')
                im.load()
                im = im.convert('RGB')
                im.thumbnail((1600,1600))
                target = io.BytesIO()
                im.save(target, format='JPEG', quality=85)
                output.append(base64.b64encode(target.getvalue()).decode())
        except Exception as exc:
            raise HTTPException(400, 'Imagen inválida: ' + str(exc)[:160])
    return output

@app.post('/api/chat')
async def chat(body: ChatRequest, session=Depends(auth.require_session)):
    if agent.current:
        raise HTTPException(409, 'Hay una ejecución activa. Detenela antes de iniciar otra.')
    if not db.rows('SELECT id FROM conversations WHERE id=?', (body.conversation_id,)):
        raise HTTPException(404, 'Conversación inexistente.')
    images = validate_images(body.images)
    run = Run(body.conversation_id, body.model, body.mode, session['token'])
    agent.current = run
    db.message(body.conversation_id, 'user', body.text, body.model)
    if len(db.rows('SELECT id FROM messages WHERE conversation_id=?', (body.conversation_id,))) == 1:
        db.execute('UPDATE conversations SET title=? WHERE id=?', (body.text[:70], body.conversation_id))
    run.task = asyncio.create_task(agent.generate(run, images))
    async def events():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(run.queue.get(), 12)
                except asyncio.TimeoutError:
                    yield ': heartbeat\n\n'
                    continue
                yield 'data: ' + json.dumps(event, ensure_ascii=False) + '\n\n'
                if event['event'] == 'done':
                    break
        finally:
            if agent.current is run:
                await agent.stop()
    return StreamingResponse(events(), media_type='text/event-stream', headers={'X-Accel-Buffering': 'no'})

class Memory(StrictModel):
    content: str = Field(min_length=1, max_length=1000)

@app.get('/api/memory', dependencies=[Depends(auth.require_session)])
def memories():
    return db.rows('SELECT * FROM memories ORDER BY id DESC')

@app.post('/api/memory', dependencies=[Depends(auth.require_session)])
def add_memory(body: Memory):
    if len(memories()) >= 30:
        raise HTTPException(400, 'Máximo 30 notas. Eliminá una antes de agregar otra.')
    db.execute('INSERT INTO memories (content,created) VALUES (?,?)', (body.content, time.time()))
    return {'ok': True}

@app.delete('/api/memory/{memory_id}', dependencies=[Depends(auth.require_session)])
def delete_memory(memory_id: int):
    db.execute('DELETE FROM memories WHERE id=?', (memory_id,))
    return {'ok': True}

@app.post('/api/voice/transcribe', dependencies=[Depends(auth.require_session)])
async def transcribe(audio: UploadFile):
    if not stt.available():
        raise HTTPException(503, 'STT pendiente de instalación. Consultá docs/voz.md.')
    content = await audio.read(10_000_001)
    if len(content) > 10_000_000:
        raise HTTPException(413, 'Audio demasiado grande (máximo 10 MB).')
    target = ROOT / 'data' / (uuid.uuid4().hex + '.webm')
    try:
        target.write_bytes(content)
        text = await asyncio.to_thread(stt.transcribe, target)
        return {'text': text}
    finally:
        target.unlink(missing_ok=True)

dist = ROOT / 'frontend' / 'dist'
if dist.exists():
    app.mount('/assets', StaticFiles(directory=dist/'assets'), name='assets')

@app.get('/')
def index():
    file = dist / 'index.html'
    if not file.exists():
        raise HTTPException(503, 'Compilá el frontend con scripts/setup.ps1.')
    return FileResponse(file)
