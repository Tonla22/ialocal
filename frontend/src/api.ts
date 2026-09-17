export let csrf = '';
export function setCsrf(value: string) { csrf = value; }
export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch('/api' + path, {
    ...options, credentials: 'same-origin',
    headers: {'Content-Type': 'application/json', 'X-Local-App': '1', 'X-CSRF-Token': csrf, ...options.headers},
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    if(response.status === 401 && !path.startsWith('/auth')) window.dispatchEvent(new Event('session-expired'));
    throw new Error(typeof error.detail === 'string' ? error.detail : `Error ${response.status}`);
  }
  return response.json();
}
export async function streamChat(body: unknown, signal: AbortSignal, onEvent: (event: any) => void) {
  const response = await fetch('/api/chat', {method:'POST',credentials:'same-origin',signal,
    headers:{'Content-Type':'application/json','X-Local-App':'1','X-CSRF-Token':csrf},body:JSON.stringify(body)});
  if(!response.ok) {
    const error = await response.json().catch(()=>({}));
    throw new Error(typeof error.detail === 'string' ? error.detail : `Error ${response.status}`);
  }
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while(true) {
    const {value, done} = await reader.read();
    if(done) break;
    buffer += decoder.decode(value,{stream:true});
    let boundary;
    while((boundary = buffer.indexOf('\n\n')) >= 0) {
      const block = buffer.slice(0,boundary);
      buffer = buffer.slice(boundary+2);
      for(const line of block.split('\n')) if(line.startsWith('data: ')) onEvent(JSON.parse(line.slice(6)));
    }
  }
}
