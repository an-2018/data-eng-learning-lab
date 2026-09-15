"""Docker launcher lives on the execution host only. No shell interpolation."""
import io
import json
import os
import subprocess
import tarfile
import time
from pathlib import PurePosixPath
from .config import LIMITS, PRODUCTION

class RuntimeUnavailable(Exception):
    pass

class ExecutionTimeout(Exception):
    pass

class ExecutionCanceled(Exception):
    pass

class LearnerError(Exception):
    pass

def image_for(runner):
    family = 'OWL' if runner == 'owl' else 'SPARK' if runner == 'spark' else 'JENA'
    return os.getenv(f'RUNTIME_{family}_IMAGE', f'graphlab-{family.lower()}:1')

def docker(args, **kwargs):
    try:
        result = subprocess.run(['docker', *args], capture_output=True, timeout=20, **kwargs)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise RuntimeUnavailable('The isolated execution service is unavailable') from exc
    if result.returncode:
        raise RuntimeUnavailable(result.stderr.decode(errors='replace')[:1000])
    return result.stdout

def execute(runner, files, fixture, contract, job_id, canceled=lambda: False):
    cpu, memory, deadline = LIMITS[runner]
    runtime = os.getenv('SANDBOX_RUNTIME', 'runsc')
    if PRODUCTION and runtime != 'runsc':
        raise RuntimeUnavailable('Production execution requires the runsc sandbox runtime')
    name = 'graphlab-' + job_id.replace('-','')[:32]
    args = ['create','--name',name,'--label','graphlab.job=true','--runtime',runtime,
            '--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
            '--user','10001:10001','--pids-limit','256','--cpus',str(cpu),'--memory',memory,
            '--memory-swap',memory,'--ulimit','nofile=1024:1024',
            '--tmpfs','/tmp:rw,nosuid,nodev,size=512m,mode=1777',
            '--tmpfs','/work:rw,nosuid,nodev,size=128m,mode=1777',image_for(runner)]
    created = False
    try:
        docker(args)
        created = True
        payload = {'runner':runner,'files':files,'fixture':fixture,'contract':contract}
        encoded = json.dumps(payload).encode()
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive,mode='w') as tar:
            info = tarfile.TarInfo('input.json')
            info.size, info.mode, info.uid, info.gid = len(encoded), 0o444, 10001, 10001
            tar.addfile(info,io.BytesIO(encoded))
        docker(['cp','-',f'{name}:/opt/input/'],input=archive.getvalue())
        docker(['start',name])
        start = time.monotonic()
        while True:
            if canceled():
                raise ExecutionCanceled()
            if time.monotonic() - start > deadline:
                raise ExecutionTimeout()
            state = json.loads(docker(['inspect','--format','{{json .State}}',name]))
            if not state['Running']:
                break
            time.sleep(.2)
        if state.get('OOMKilled'):
            raise LearnerError('The exercise exceeded its memory allowance. Reduce intermediate results or driver-side collection.')
        # Output is retrieved from a bounded tmpfs, never trusted as a test verdict.
        try:
            raw = docker(['cp',f'{name}:/work/result.json','-'])
        except RuntimeUnavailable as exc:
            raise LearnerError('Execution did not produce a result. Check syntax and the required output contract.') from exc
        with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
            members = tar.getmembers()
            if len(members) != 1 or not members[0].isfile() or members[0].size > 2_000_000:
                raise LearnerError('Execution output exceeded the result limit')
            result = json.load(tar.extractfile(members[0]))
        if 'error' in result:
            raise LearnerError(str(result['error'])[:3000])
        return result
    finally:
        if created:
            try:
                docker(['rm','-f',name])
            except RuntimeUnavailable:
                pass  # Scheduled reaper retries cleanup of stopped job containers.
