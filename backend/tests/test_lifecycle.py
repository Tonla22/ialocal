import asyncio
import pytest
from app.agent import agent, Run
from app import database as db
from app.providers.ollama import provider

def test_stop_while_provider_is_loading(client, monkeypatch):
    async def slow_capabilities(model):
        await asyncio.sleep(30)
        return ['tools']
    monkeypatch.setattr(provider,'capabilities',slow_capabilities)
    async def scenario():
        cid=db.conversation()
        db.message(cid,'user','test')
        run=Run(cid,'slow','chat','session')
        agent.current=run
        run.task=asyncio.create_task(agent.generate(run,[]))
        await asyncio.sleep(.02)
        await asyncio.wait_for(agent.stop(),1)
        assert agent.current is None
        assert db.rows('SELECT status FROM messages ORDER BY id DESC')[0]['status']=='stopped'
    asyncio.run(scenario())

def test_approval_id_and_session_binding(client):
    run=Run('test','model','agent','different-session')
    run.approval={'id':'one-time','tool':'escribir_archivo','arguments':{'path':'test.txt','content':'hello'}}
    agent.current=run
    assert client.post('/api/approvals/one-time',json={'approved':True}).status_code==409
    assert client.post('/api/approvals/unknown',json={'approved':True}).status_code==409
    agent.current=None

def test_actual_powershell_requires_and_honors_approval(client):
    async def scenario():
        run=Run('test','model','agent','session')
        db.execute('UPDATE tools SET enabled=1 WHERE name=?',('powershell',))
        task=asyncio.create_task(agent.execute_tool(run,'powershell',{'command':"Write-Output 'nexo-terminal-ok'"}))
        await asyncio.sleep(.02)
        assert run.approval and run.approval['tool']=='powershell'
        run.decision.set_result(True)
        result=await task
        assert result['exit_code']==0
        assert 'nexo-terminal-ok' in result['output']
    asyncio.run(scenario())
