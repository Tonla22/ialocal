import asyncio
import os
import subprocess

async def kill_tree(process):
    if process.returncode is not None:
        return
    if os.name == 'nt':
        killer = await asyncio.create_subprocess_exec('taskkill', '/PID', str(process.pid), '/T', '/F',
                         stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
                         creationflags=subprocess.CREATE_NO_WINDOW)
        await killer.wait()
    else:
        import signal
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    await process.wait()

async def run_process(args, cwd, timeout=45):
    kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}
    process = await asyncio.create_subprocess_exec(*args, cwd=cwd, stdout=asyncio.subprocess.PIPE,
                                                  stderr=asyncio.subprocess.STDOUT, **kwargs)
    async def collect():
        parts, size = [], 0
        while block := await process.stdout.read(4096):
            if size < 24000:
                parts.append(block[:24000-size])
                size += len(parts[-1])
        await process.wait()
        return {'exit_code': process.returncode, 'output': b''.join(parts).decode('utf-8', errors='replace'),
                'output_limit': 24000}
    try:
        return await asyncio.wait_for(collect(), timeout)
    except BaseException:
        await asyncio.shield(kill_tree(process))
        raise
