"""Python checks run only in a constrained Docker container, never on the host."""
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import tempfile
import time
import uuid


def defaults():
    return {'enabled': True, 'backend': 'docker', 'executable': 'docker',
            'image': 'python:3.12-slim', 'timeout': 30, 'memory_mb': 256,
            'cpus': 1, 'pids': 32, 'max_output_bytes': 131072}


def validate(cfg):
    if cfg.get('backend') != 'docker':
        raise ValueError('执行仅支持 docker；无主机运行回退')
    if type(cfg.get('enabled')) is not bool:
        raise ValueError('execution.enabled 必须为 bool')
    for key in ('timeout', 'memory_mb', 'cpus', 'pids', 'max_output_bytes'):
        if not isinstance(cfg.get(key), (int, float)) or isinstance(cfg[key], bool) or cfg[key] <= 0:
            raise ValueError('execution.' + key + ' 必须为正数')
    if not isinstance(cfg.get('image'), str) or not cfg['image'] or cfg['image'].startswith('-'):
        raise ValueError('execution.image 非法')
    return cfg


def container_command(binary, name, cfg):
    return [binary, 'run', '--rm', '--name', name, '--pull', 'never',
            '--network', 'none', '--read-only', '--user', '65534:65534',
            '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true',
            '--pids-limit', str(cfg['pids']), '--memory', str(cfg['memory_mb']) + 'm',
            '--memory-swap', str(cfg['memory_mb']) + 'm', '--cpus', str(cfg['cpus']),
            '--ulimit', 'cpu=' + str(max(1, int(cfg['timeout']))) + ':' + str(max(1, int(cfg['timeout']))),
            '--tmpfs', '/work:rw,noexec,nosuid,size=32m,mode=1777', '--workdir', '/work',
            '--log-driver', 'none', '-i', cfg['image'], 'python', '-I', '-u', '-']


def run_check(script, folder, cfg):
    cfg = validate({**defaults(), **cfg})
    folder = Path(folder).resolve(); folder.mkdir(parents=True, exist_ok=True)
    code_hash = hashlib.sha256(script.encode()).hexdigest()
    result = {'id': uuid.uuid4().hex[:16], 'code_sha256': code_hash, 'status': 'unavailable',
              'stdout': '', 'stderr': '', 'returncode': None, 'cleanup_ok': True,
              'backend': 'docker', 'network': 'none', 'image': cfg['image']}
    (folder / 'check.py').write_text(script, encoding='utf-8')
    (folder / 'stdout.txt').write_text('', encoding='utf-8')
    (folder / 'stderr.txt').write_text('', encoding='utf-8')
    started = time.monotonic()
    def finish():
        result['duration_seconds'] = round(time.monotonic() - started, 4)
        (folder / 'execution.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        return result
    if not cfg['enabled']:
        result.update(status='disabled', reason='执行已关闭；不运行检查脚本')
        return finish()
    binary = shutil.which(cfg['executable'])
    if not binary:
        result['reason'] = '找不到 Docker；请安装并启动本机 Docker，预先拉取配置镜像后 resume'
        return finish()
    try:
        info = subprocess.run([binary, 'image', 'inspect', '--format', '{{.Id}}', cfg['image']], capture_output=True, text=True, timeout=10)
        if info.returncode or not info.stdout.strip():
            result['reason'] = 'Docker daemon 不可用或镜像未预先拉取；不会自动联网拉取'
            return finish()
    except (OSError, subprocess.TimeoutExpired):
        result['reason'] = 'Docker 预检查失败或超时'
        return finish()
    result['image_id'] = info.stdout.strip()
    # Freeze the inspected local image; a mutable tag cannot change mid-check.
    cfg['image'] = result['image_id']
    name = 'coop-check-' + uuid.uuid4().hex
    result['container_name'] = name
    argv = container_command(binary, name, cfg)
    (folder / 'command.json').write_text(json.dumps(argv), encoding='utf-8')
    proc = None
    captured = {'stdout': bytearray(), 'stderr': bytearray()}
    result['status'] = 'error'
    try:
        # Host staging is temporary. It is never mounted inside the container.
        with tempfile.TemporaryDirectory(prefix='coop-check-') as tmp:
            source = Path(tmp) / 'input.py'; source.write_text(script, encoding='utf-8')
            with source.open('rb') as inp, selectors.DefaultSelector() as selector:
                proc = subprocess.Popen(argv, stdin=inp, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
                for stream, key in ((proc.stdout, 'stdout'), (proc.stderr, 'stderr')):
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, key)
                deadline = time.monotonic() + cfg['timeout']
                exceeded = False
                while selector.get_map() or proc.poll() is None:
                    if time.monotonic() >= deadline:
                        result['status'] = 'timeout'; break
                    for event, _ in selector.select(timeout=min(0.05, max(0, deadline - time.monotonic()))):
                        chunk = os.read(event.fd, 65536)
                        if not chunk:
                            selector.unregister(event.fileobj); event.fileobj.close(); continue
                        room = int(cfg['max_output_bytes']) - sum(len(x) for x in captured.values())
                        captured[event.data].extend(chunk[:max(0, room)])
                        if len(chunk) > room:
                            exceeded = True; break
                    if exceeded:
                        result['status'] = 'output_limit'; break
                else:
                    result['returncode'] = proc.wait()
                    result['status'] = 'completed' if proc.returncode == 0 else 'error'
    except KeyboardInterrupt:
        result['status'] = 'interrupted'
        raise
    except Exception as exc:
        result.update(status='error', reason=type(exc).__name__ + ': ' + str(exc))
    finally:
        if proc is not None:
            if proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            proc.wait()
            result['returncode'] = proc.returncode
            for stream in (proc.stdout, proc.stderr):
                if stream and not stream.closed:
                    stream.close()
        # Killing a Docker client alone does not stop its container.
        try:
            cleanup = subprocess.run([binary, 'rm', '-f', name], capture_output=True, text=True, timeout=10)
            result['cleanup_ok'] = cleanup.returncode == 0 or 'no such container' in cleanup.stderr.lower()
        except (OSError, subprocess.TimeoutExpired):
            result['cleanup_ok'] = False
        for key, data in captured.items():
            (folder / (key + '.txt')).write_bytes(data)
            result[key] = data.decode('utf-8', errors='replace')
        if not result['cleanup_ok']:
            result['status'] = 'cleanup_failed'
            result['reason'] = '无法确认容器停止；在本机执行 docker rm -f ' + name
        finish()
    return result
