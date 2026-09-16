"""Docker launcher lives on the execution host only. No shell interpolation."""
import io
import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path
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
    input_dir = tempfile.TemporaryDirectory(prefix='graphlab-input-')
    output_dir = tempfile.TemporaryDirectory(prefix='graphlab-output-')
    input_file = Path(input_dir.name) / 'input.json'
    input_file.write_text(json.dumps({'runner':runner,'files':files,'fixture':fixture,'contract':contract}), encoding='utf-8')
    args = ['create','--name',name,'--hostname','graphlab','--add-host','graphlab:127.0.0.1','--label','graphlab.job=true','--runtime',runtime,
            '--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
            '--user','10001:10001','--pids-limit','256','--cpus',str(cpu),'--memory',memory,
            '--memory-swap',memory,'--ulimit','nofile=1024:1024',
            '--mount',f'type=bind,src={input_file},dst=/input.json,readonly',
            '--mount',f'type=bind,src={output_dir.name},dst=/output',
            '--tmpfs','/tmp:rw,nosuid,nodev,size=512m,mode=1777',
            '--tmpfs','/work:rw,nosuid,nodev,size=128m,mode=1777',image_for(runner)]
    created = False
    try:
        docker(args)
        created = True
        # Input arrives as a read-only bind mount. Learner containers never receive
        # the worker's Docker socket, hidden answers beyond their fixture, or host paths.
        # The mount must be present at container creation; docker cp cannot modify a read-only rootfs.
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
        # Output is persisted in a unique worker-owned directory, then parsed by the
        # trusted grader. It is bounded and never accepted as its own verdict.
        try:
            result_file = Path(output_dir.name) / 'result.json'
            raw = result_file.read_bytes()
        except OSError as exc:
            logs_result = subprocess.run(['docker','logs','--tail','40',name],capture_output=True)
            diagnostic = logs_result.stdout + logs_result.stderr
            detail = diagnostic.decode(errors='replace')[:2000] or str(exc)
            raise LearnerError('Execution did not produce a result: ' + detail) from exc
        if len(raw) > 2_000_000:
            raise LearnerError('Execution output exceeded the result limit')
        result = json.loads(raw)
        if 'error' in result:
            raise LearnerError(str(result['error'])[:3000])
        return result
    finally:
        if created:
            try:
                docker(['rm','-f',name])
            except RuntimeUnavailable:
                pass  # Scheduled reaper retries cleanup of stopped job containers.
        input_dir.cleanup()
        output_dir.cleanup()
