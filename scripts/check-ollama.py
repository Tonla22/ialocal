"""Real Ollama checks against the disposable instance on port 8766."""
import json
import time
from pathlib import Path
import httpx

root=Path(__file__).resolve().parents[1]
client=httpx.Client(base_url='http://127.0.0.1:8766',timeout=240,trust_env=False,
                    headers={'Origin':'http://127.0.0.1:8766','X-Local-App':'1'})
r=client.post('/api/auth/login',json={'password':'Verification-local-2026!'})
r.raise_for_status();client.headers['X-CSRF-Token']=r.json()['csrf']
models=client.get('/api/models').json()
assert models['online'] and models['models'],models
model='qwen3:8b'
report={'models':[m['name'] for m in models['models']], 'checks':[]}
for mode,prompt in [('chat','Respondé únicamente: Nexo funciona.'),('agent','Usá la herramienta listar_archivos con path="." y root=0. Después decime los archivos que encontraste. No escribas JSON como texto: llamá a la herramienta.')]:
    cid=client.post('/api/conversations').json()['id']
    start=time.monotonic();events=[]
    with client.stream('POST','/api/chat',json={'conversation_id':cid,'text':prompt,'model':model,'mode':mode}) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line.startswith('data: '):
                event=json.loads(line[6:]);events.append(event)
                if event['event'] in ('state','error','tool_result','done'): print(json.dumps(event,ensure_ascii=True),flush=True)
    assert not [e for e in events if e['event']=='error'],events
    assert any(e['event']=='token' for e in events),events
    if mode=='agent': assert any(e['event']=='tool_result' and e['tool']=='listar_archivos' for e in events),events
    history=client.get('/api/conversations/'+cid+'/messages').json()
    assert len(history)>=2 and history[-1]['content']
    report['checks'].append({'mode':mode,'seconds':round(time.monotonic()-start,2),'events':[e['event'] for e in events],
                             'answer':history[-1]['content']})
(root/'data'/'verification-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print('REAL OLLAMA CHECKS PASSED',flush=True)
