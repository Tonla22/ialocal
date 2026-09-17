import asyncio
import json
import base64
import io
from PIL import Image
from app import database as db
from app.agent import agent, Run
from app.providers.ollama import provider

def events(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]

def setup_model(monkeypatch, stream, capabilities=['tools']):
    async def caps(model): return capabilities
    monkeypatch.setattr(provider,'capabilities',caps)
    monkeypatch.setattr(provider,'stream',stream)

def test_stream_persists_and_no_thinking(client,monkeypatch):
    async def stream(*args):
        yield {'message':{'thinking':'PRIVATE SECRET','content':'Hola '}}
        yield {'message':{'content':'mundo'},'done':True}
    setup_model(monkeypatch,stream)
    cid=client.post('/api/conversations').json()['id']
    response=client.post('/api/chat',json={'conversation_id':cid,'text':'Hola','model':'test','mode':'chat'})
    assert response.status_code==200
    assert 'PRIVATE SECRET' not in response.text
    assert ''.join(e['text'] for e in events(response) if e['event']=='token')=='Hola mundo'
    messages=client.get(f'/api/conversations/{cid}/messages').json()
    assert [x['content'] for x in messages]==['Hola','Hola mundo']
    assert agent.current is None

def test_agent_tool_roundtrip(client,monkeypatch):
    calls=[]
    async def stream(model,messages,tools,capabilities):
        calls.append(messages.copy())
        if len(calls)==1:
            assert any(t['function']['name']=='listar_archivos' for t in tools)
            yield {'message':{'tool_calls':[{'function':{'name':'listar_archivos','arguments':{'path':'.'}}}]}}
        else:
            assert messages[-1]['role']=='tool'
            assert 'entries' in messages[-1]['content']
            yield {'message':{'content':'Carpeta consultada.'}}
    setup_model(monkeypatch,stream)
    cid=client.post('/api/conversations').json()['id']
    response=client.post('/api/chat',json={'conversation_id':cid,'text':'Listá archivos','model':'test','mode':'agent'})
    assert len(calls)==2
    assert any(e['event']=='tool_result' for e in events(response))
    assert db.rows("SELECT * FROM audit WHERE state='completed'")

def test_model_failure_saved_as_error(client,monkeypatch):
    async def stream(*args):
        raise RuntimeError('connect failed')
        yield
    setup_model(monkeypatch,stream)
    cid=client.post('/api/conversations').json()['id']
    response=client.post('/api/chat',json={'conversation_id':cid,'text':'Hola','model':'test','mode':'chat'})
    assert any(e['event']=='error' for e in events(response))
    assert client.get(f'/api/conversations/{cid}/messages').json()[-1]['status']=='error'
    assert agent.current is None

def test_iteration_limit(client,monkeypatch):
    async def stream(*args):
        yield {'message':{'tool_calls':[{'function':{'name':'listar_archivos','arguments':{}}}]}}
    setup_model(monkeypatch,stream)
    db.set_setting('max_iterations',2)
    cid=client.post('/api/conversations').json()['id']
    response=client.post('/api/chat',json={'conversation_id':cid,'text':'loop','model':'test','mode':'agent'})
    assert events(response)[-1]['status']=='limited'
    assert len([e for e in events(response) if e['event']=='tool_result'])==2

def test_stop_during_approval(client):
    async def scenario():
        cid=db.conversation()
        db.execute('UPDATE tools SET enabled=1 WHERE name=?',('escribir_archivo',))
        run=Run(cid,'test','agent','session');agent.current=run
        run.task=asyncio.create_task(agent.execute_tool(run,'escribir_archivo',{'path':'cancel.txt','content':'never'}))
        await asyncio.sleep(.02)
        assert run.approval
        await agent.stop()
        assert run.task.cancelled()
        from app.config import config
        assert not (config.roots[0]/'cancel.txt').exists()
    asyncio.run(scenario())
    agent.current=None

def test_vision_rejected_without_capability(client,monkeypatch):
    async def stream(*args): yield {'message':{'content':'ok'}}
    setup_model(monkeypatch,stream)
    target=io.BytesIO();Image.new('RGB',(4,4)).save(target,format='PNG')
    encoded=base64.b64encode(target.getvalue()).decode()
    cid=client.post('/api/conversations').json()['id']
    response=client.post('/api/chat',json={'conversation_id':cid,'text':'imagen','model':'test','mode':'chat','images':[encoded]})
    assert response.status_code==200
    assert any(e['event']=='error' and 'visión' in e['text'] for e in events(response))
    assert db.rows('SELECT * FROM messages')[-1]['status']=='error'

def test_images_transmitted_but_not_persisted(client,monkeypatch):
    async def stream(model,messages,*args):
        assert messages[-1]['images']
        yield {'message':{'content':'Imagen recibida'}}
    setup_model(monkeypatch,stream,['vision'])
    target=io.BytesIO();Image.new('RGB',(4,4)).save(target,format='PNG')
    cid=client.post('/api/conversations').json()['id']
    encoded=base64.b64encode(target.getvalue()).decode()
    response=client.post('/api/chat',json={'conversation_id':cid,'text':'imagen','model':'test','mode':'chat','images':[encoded]})
    assert response.status_code==200
    assert encoded not in json.dumps(db.rows('SELECT * FROM messages'))

def test_memory_lifecycle(client):
    assert client.post('/api/memory',json={'content':'Prefiero ejemplos'}).status_code==200
    note=client.get('/api/memory').json()[0]
    assert client.delete('/api/memory/'+str(note['id'])).status_code==200
    assert client.get('/api/memory').json()==[]
