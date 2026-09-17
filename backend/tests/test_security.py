import asyncio
import json
import os
import sys
import pytest
from app import auth, database as db
from app.config import config
from app.tools import files
from app.tools.registry import initialize
from app.tools.process import run_process
from app.agent import agent, Run

def test_auth_origin_csrf_and_first_setup(environment):
    client, path = environment
    assert client.get('/api/settings').status_code == 401
    assert client.get('/api/auth/status').json()['setup_required']
    assert client.post('/api/auth/login',json={'password':'long-password'}).status_code == 403
    headers={'Origin':'http://127.0.0.1:8765','X-Local-App':'1'}
    assert client.post('/api/auth/login',headers=headers,json={'password':'long-password'}).status_code == 403
    response=client.post('/api/auth/login',headers=headers,json={'password':'long-password','setup_key':auth.SETUP_FILE.read_text()})
    assert response.status_code == 200
    assert not auth.SETUP_FILE.exists()
    assert 'HttpOnly' in response.headers['set-cookie']
    assert client.post('/api/conversations',headers=headers).status_code == 403
    headers['X-CSRF-Token']=response.json()['csrf']
    assert client.post('/api/conversations',headers=headers).status_code == 200
    headers['Origin']='https://evil.example'
    assert client.post('/api/conversations',headers=headers).status_code == 403
    assert client.get('/api/health',headers={'Host':'evil.example'}).status_code == 400

def test_logout_revokes_session(client):
    assert client.post('/api/auth/logout').status_code == 200
    assert client.get('/api/settings').status_code == 401

def test_password_is_hashed_and_login_throttled(environment):
    client, _ = environment
    stored=auth.password_hash('hello-world-123')
    assert 'hello-world' not in stored
    assert auth.verify('hello-world-123',stored)
    assert not auth.verify('hello-world-124',stored)
    headers={'Origin':'http://127.0.0.1:8765','X-Local-App':'1'}
    for _ in range(5):
        assert client.post('/api/auth/login',headers=headers,json={'password':'hello-world-123','setup_key':'wrong'}).status_code == 403
    assert client.post('/api/auth/login',headers=headers,json={'password':'hello-world-123'}).status_code == 429

def test_files_confined_and_limits(client, tmp_path):
    for path in ['../secret.txt','a/../../secret','C:\\Windows\\win.ini','/etc/passwd','file.txt:secret','\\\\server\\share']:
        with pytest.raises(ValueError): files.safe_path(path)
    files.write_file('hello.txt','hola')
    assert files.read_file('hello.txt')['content']=='hola'
    files.copy_file('hello.txt','copy.txt')
    with pytest.raises(ValueError): files.copy_file('hello.txt','copy.txt')
    files.move_file('copy.txt','moved.txt')
    assert files.search_files('moved')['paths']==['moved.txt']
    with pytest.raises(ValueError): files.write_file('huge.txt','x'*100001)
    with pytest.raises(ValueError): files.safe_path('.',99)
    secret=tmp_path/'outside.txt';secret.write_text('secret')
    try:
        os.link(secret,config.roots[0]/'linked.txt')
    except OSError:
        pytest.skip('Filesystem does not support hardlinks')
    with pytest.raises(ValueError): files.read_file('linked.txt')

def test_approval_rejection_and_revocation(client):
    async def scenario():
        run=Run('test','model','agent','session')
        db.execute('UPDATE tools SET enabled=1 WHERE name=?',('escribir_archivo',))
        task=asyncio.create_task(agent.execute_tool(run,'escribir_archivo',{'path':'never.txt','content':'abc'}))
        await asyncio.sleep(.02)
        assert run.approval['arguments']['content']=='abc'
        assert not (config.roots[0]/'never.txt').exists()
        run.decision.set_result(False)
        assert 'error' in await task
        assert not (config.roots[0]/'never.txt').exists()
        task=asyncio.create_task(agent.execute_tool(run,'escribir_archivo',{'path':'never.txt','content':'abc'}))
        await asyncio.sleep(.02)
        db.set_setting('tools_disabled',True)
        run.decision.set_result(True)
        with pytest.raises(ValueError): await task
        assert not (config.roots[0]/'never.txt').exists()
    asyncio.run(scenario())

def test_approval_success_strict_args_and_terminal_always_asks(client):
    async def scenario():
        run=Run('test','model','agent','session')
        db.execute('UPDATE tools SET enabled=1 WHERE name IN (?,?)',('escribir_archivo','powershell'))
        task=asyncio.create_task(agent.execute_tool(run,'escribir_archivo',{'path':'yes.txt','content':'approved'}))
        await asyncio.sleep(.02)
        run.decision.set_result(True)
        assert (await task)['written']=='yes.txt'
        assert files.read_file('yes.txt')['content']=='approved'
        with pytest.raises(ValueError): await agent.execute_tool(run,'leer_archivo',{'path':'yes.txt','unknown':True})
        db.set_setting('confirm_writes',False)
        task=asyncio.create_task(agent.execute_tool(run,'powershell',{'command':'Get-Date'}))
        await asyncio.sleep(.02)
        assert run.approval['tool']=='powershell'
        run.decision.set_result(False)
        await task
    asyncio.run(scenario())

def test_process_timeout_and_cancel(tmp_path):
    async def scenario():
        result=await run_process([sys.executable,'-c','print("ok")'],tmp_path)
        assert result['exit_code']==0 and 'ok' in result['output']
        with pytest.raises(asyncio.TimeoutError):
            await run_process([sys.executable,'-c','import time; time.sleep(30)'],tmp_path,timeout=.2)
        task=asyncio.create_task(run_process([sys.executable,'-c','import time; time.sleep(30)'],tmp_path))
        await asyncio.sleep(.2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
    asyncio.run(scenario())

def test_sessions_expire(client):
    db.execute('UPDATE sessions SET expires=0')
    assert client.get('/api/conversations').status_code == 401

def test_unknown_tool_and_global_disable(client):
    async def scenario():
        run=Run('t','m','agent','s')
        with pytest.raises(ValueError): await agent.execute_tool(run,'invented',{})
        with pytest.raises(ValueError): await agent.execute_tool(run,'powershell',{'command':'Get-Date'})
        db.set_setting('tools_disabled',True)
        with pytest.raises(ValueError): await agent.execute_tool(run,'listar_archivos',{})
    asyncio.run(scenario())
