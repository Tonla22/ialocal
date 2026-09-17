import json
import httpx
from ..config import config

class OllamaProvider:
    async def models(self):
        async with httpx.AsyncClient(timeout=8, trust_env=False) as client:
            response = await client.get(config.ollama_url.rstrip('/') + '/api/tags')
            response.raise_for_status()
            return response.json().get('models', [])

    async def capabilities(self, model):
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            response = await client.post(config.ollama_url.rstrip('/') + '/api/show', json={'model': model})
            response.raise_for_status()
            return response.json().get('capabilities', [])

    async def stream(self, model, messages, tools, capabilities):
        payload = {'model': model, 'messages': messages, 'stream': True,
                   'options': {'num_ctx': 8192, 'num_predict': 2048}, 'keep_alive': '5m'}
        if 'thinking' in capabilities:
            payload['think'] = False
        if tools:
            payload['tools'] = tools
        async with httpx.AsyncClient(timeout=httpx.Timeout(config.ollama_timeout, connect=8), trust_env=False) as client:
            async with client.stream('POST', config.ollama_url.rstrip('/') + '/api/chat', json=payload) as response:
                if response.is_error:
                    raw = await response.aread()
                    raise RuntimeError('Ollama: ' + raw.decode(errors='replace')[:600])
                async for line in response.aiter_lines():
                    if line:
                        chunk = json.loads(line)
                        if chunk.get('error'):
                            raise RuntimeError(chunk['error'])
                        yield chunk

provider = OllamaProvider()
