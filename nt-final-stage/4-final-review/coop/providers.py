"""Transport adapters. No SDK dependencies and no automatic credential discovery."""
import json
import os
import re
from pathlib import Path
import signal
import sys
import threading
import time
import subprocess
import urllib.request
import urllib.error
from urllib.parse import urlsplit, urlunsplit
try:
    from .access import environment_for, parse_kimi, classify_error
except ImportError:  # Direct execution in the isolated transport worker.
    from access import environment_for, parse_kimi, classify_error


def _invoke(spec, prompt, stage, folder, timeout):
    kind = spec['kind']
    if kind == 'demo':
        try:
            from .protocol import encode
        except ImportError:
            from protocol import encode
        if stage == '__probe__':
            return '{"ok":true}'
        if stage.startswith('edit-'):
            # Edit-loop stage keys look like edit-r2-exchange1; the kind is the third field.
            kind = re.sub(r'\d+$', '', stage.split('-')[2])
            meta = {'kind': kind, 'issues': [], 'done': True}
            if kind == 'review':
                meta['verdict'] = 'approve'
            return encode(meta, '模拟输出：未做真实数学判断，也不提出修改。')
        if stage == 'plan':
            return encode({'kind':'plan'}, '模拟规划：明确条件，独立分析，逐分支审查。')
        if stage.startswith('review'):
            return encode({'kind':'review','verdict':'approve','assessment':'unknown','issues':[],
                           'evidence_accepted':False,'evidence_ids':[]}, '模拟审查；未验证数学内容。')
        return encode({'kind':'analysis','assessment':'unknown','check':False}, '这是模拟正文，仅验证工作流。')
    if kind == 'api':
        key = os.environ.get(spec['key_env'])
        if not key:
            raise ValueError('未设置环境变量 ' + spec['key_env'])
        if not spec['url'].startswith('https://'):
            raise ValueError('API URL 必须使用 HTTPS')
        payload = {'model': spec['model'], 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': spec.get('max_tokens', 8192)}
        if stage == '__models__':
            parts = urlsplit(spec['url'])
            base = parts.path.removesuffix('/chat/completions').rstrip('/')
            url = spec.get('models_url') or urlunsplit((parts.scheme, parts.netloc, base + '/models', '', ''))
            if not url.startswith('https://') or urlsplit(url).netloc != parts.netloc:
                raise ValueError('models_url 必须与 API 同源并使用 HTTPS')
            req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + key})
        else:
            req = urllib.request.Request(spec['url'], data=json.dumps(payload).encode(), headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        # Do not forward credentials through redirects.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        try:
            with urllib.request.build_opener(NoRedirect()).open(req, timeout=timeout) as response:
                data = response.read(8_000_001)
            if len(data) > 8_000_000:
                raise ValueError('API 输出超过限制')
            body = json.loads(data)
            (folder / 'transport.json').write_text(json.dumps(body, ensure_ascii=False), encoding='utf-8')
            if stage == '__models__':
                if not isinstance(body.get('data'), list):
                    raise ValueError('模型列表响应缺少 data 数组')
                return json.dumps(body)
            choice = body['choices'][0]
            if choice.get('finish_reason') not in (None, 'stop'):
                raise ValueError('API finish_reason=' + str(choice.get('finish_reason')) + '，输出可能截断')
            return choice['message']['content']
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f'API HTTP {exc.code}，检查额度、模型名称和密钥') from None
    result_file = folder / 'answer.txt'
    model = spec.get('model')
    stdin = prompt
    env = environment_for(spec)
    executable = spec.get('executable', kind)
    if kind == 'codex':
        argv = [executable, 'exec', '--skip-git-repo-check', '--sandbox', 'read-only', '-o', str(result_file)]
        if spec.get('auth_mode') == 'subscription':
            argv += ['-c', 'model_provider="openai"']
        if model:
            argv += ['-m', model]
        argv += ['-']
    elif kind == 'claude':
        argv = [executable, '-p', '--output-format', 'json', '--tools', '', '--disallowedTools', 'mcp__*', '--no-session-persistence']
        if model:
            argv += ['--model', model]
    elif kind == 'gemini':
        argv = [executable, '-p', 'Follow the task supplied on stdin, including its exact response format.', '--output-format', 'json']
        if model:
            argv += ['--model', model]
    elif kind == 'kimi':
        # Kimi's -p text is an argument, not an assumed stdin protocol.
        if len(prompt.encode()) > 60000:
            raise ValueError('Kimi 提示超过 60 KB；缩小输入或改用 API')
        agent = folder / 'text-only.md'
        agent.write_text('---\nname: coop-text\ndescription: Text-only research collaborator\ntools: []\nsubagents: []\n---\nFollow the supplied task, including its exact response format.\n', encoding='utf-8')
        argv = [executable, '-p', prompt, '--output-format', 'stream-json', '--agent-file', str(agent)]
        if model:
            argv += ['--model', model]
        stdin = ''
    elif kind == 'command':
        argv = spec['argv']
    else:
        raise ValueError('未知 provider kind: ' + kind)
    if spec.get('auth_mode') == 'subscription' and kind in ('codex', 'claude'):
        # Check via native CLI; never open token/keychain files ourselves.
        auth_cmd = [executable, 'login', 'status'] if kind == 'codex' else [executable, 'auth', 'status']
        auth_path = folder / 'auth-status.log'
        with auth_path.open('wb') as capture:
            auth = subprocess.run(auth_cmd, stdout=capture, stderr=capture, env=env, cwd=folder, timeout=min(timeout, 15))
        status = auth_path.read_text(encoding='utf-8')
        if auth.returncode:
            raise RuntimeError('authentication: 请通过官方 CLI 登录订阅账户')
        if kind == 'codex':
            matched = 'chatgpt' in status.lower()
        else:
            matched = json.loads(status).get('authMethod') in ('claude.ai', 'oauth_token')
        if not matched:
            raise RuntimeError('authentication: 当前 CLI 未确认使用订阅登录；拒绝自动切换为 API')
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
        raise ValueError('argv 必须为非空字符串数组')
    # Logs are files so CLI output does not accumulate in process memory.
    with (folder / 'stdout.log').open('wb') as out, (folder / 'stderr.log').open('wb') as err:
        proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=out, stderr=err, cwd=folder, env=env)
        try:
            proc.communicate(stdin.encode(), timeout=timeout)
        except BaseException:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            proc.wait()
            raise
    if proc.returncode:
        diagnostic = (folder / 'stderr.log').read_text(encoding='utf-8', errors='replace')
        # Some CLIs report structured errors on stdout instead of stderr.
        diagnostic += (folder / 'stdout.log').read_text(encoding='utf-8', errors='replace')
        error = classify_error(diagnostic)
        raise RuntimeError(f'{kind} 退出码 {proc.returncode}; {error["category"]}: {error["hint"]}; 查看 {folder / "stderr.log"}')
    path = result_file if kind == 'codex' else folder / 'stdout.log'
    if path.stat().st_size > 8_000_000:
        raise ValueError('CLI 输出超过 8 MB')
    raw = path.read_text(encoding='utf-8')
    if kind == 'kimi':
        raw = parse_kimi(raw)
    if kind in ('claude', 'gemini'):
        envelope = json.loads(raw)
        if envelope.get('is_error') or envelope.get('error'):
            raise RuntimeError(f'{kind} 返回错误，查看 stdout.log')
        raw = envelope['result' if kind == 'claude' else 'response']
    return raw


_ACTIVE = set()
_MUTEX = threading.Lock()
_CANCEL = threading.Event()


def _kill(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def reset_cancel():
    _CANCEL.clear()


def cancel_all():
    _CANCEL.set()
    with _MUTEX:
        for proc in list(_ACTIVE):
            _kill(proc)


def invoke(spec, prompt, stage, folder, timeout):
    """One isolated process group per call; hard deadline and bounded log files."""
    if spec['kind'] == 'demo':
        return _invoke(spec, prompt, stage, folder, timeout)
    folder = Path(folder).resolve()
    request_file = folder / 'transport-input.json'
    request_file.write_text(json.dumps({'spec': spec, 'prompt': prompt, 'stage': stage, 'timeout': timeout}), encoding='utf-8')
    argv = [sys.executable, str(Path(__file__).resolve()), '--worker', str(request_file)]
    proc = None
    started = time.monotonic()
    limit = spec.get('max_output_bytes', 8_000_000)
    log_names = ('stdout.log', 'stderr.log', 'worker.log', 'worker-error.log', 'answer.txt', 'transport-result.json', 'transport.json', 'auth-status.log')
    with (folder / 'worker.log').open('wb') as out, (folder / 'worker-error.log').open('wb') as err:
        try:
            with _MUTEX:
                if _CANCEL.is_set():
                    raise RuntimeError('调用已取消')
                proc = subprocess.Popen(argv, stdout=out, stderr=err, start_new_session=True)
                _ACTIVE.add(proc)
            while True:
                size = sum((folder / n).stat().st_size for n in log_names if (folder / n).exists())
                if size > limit:
                    raise RuntimeError('调用日志/输出超过大小限制')
                if _CANCEL.is_set():
                    raise RuntimeError('调用已取消')
                if time.monotonic() - started >= timeout:
                    raise subprocess.TimeoutExpired(argv, timeout)
                if proc.poll() is not None:
                    break
                time.sleep(0.05)
            result_path = folder / 'transport-result.json'
            if not result_path.exists():
                raise RuntimeError('调用进程退出，检查 worker-error.log')
            result = json.loads(result_path.read_text(encoding='utf-8'))
            if 'error' in result:
                raise RuntimeError(result['error'])
            return result['raw']
        finally:
            if proc is not None:
                # Also kill any surviving descendants after normal CLI exit.
                _kill(proc)
                proc.wait()
                with _MUTEX:
                    _ACTIVE.discard(proc)


if __name__ == '__main__':
    request_path = Path(sys.argv[2])
    job = json.loads(request_path.read_text(encoding='utf-8'))
    try:
        result = {'raw': _invoke(job['spec'], job['prompt'], job['stage'], request_path.parent, job['timeout'])}
    except Exception as exc:
        result = {'error': str(exc)}
    (request_path.parent / 'transport-result.json').write_text(json.dumps(result), encoding='utf-8')
