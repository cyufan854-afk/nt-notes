"""Provider entry points, local configuration, and explicit connectivity probes."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

CATALOG = {
    'codex': {'entry': 'Codex CLI / ChatGPT login', 'login_argv': ['login'], 'model_picker': 'codex → /model', 'install_url': 'https://developers.openai.com/codex/cli', 'auth_url': 'https://learn.chatgpt.com/docs/auth'},
    'claude': {'entry': 'Claude Code / claude.ai login', 'login_argv': ['auth', 'login'], 'model_picker': 'claude → /model', 'install_url': 'https://code.claude.com/docs/en/setup', 'auth_url': 'https://code.claude.com/docs/en/authentication'},
    'gemini': {'entry': 'Gemini CLI（付费 API key 时使用；个人订阅已停止服务）', 'login_argv': [], 'model_picker': 'gemini → /model', 'install_url': 'https://geminicli.com/docs/get-started/installation/', 'auth_url': 'https://geminicli.com/docs/get-started/authentication/'},
    'antigravity': {'entry': 'Antigravity CLI（agy）/ Google AI Pro 订阅', 'login_argv': [], 'model_picker': 'agy models（或 models NAME --fetch）', 'install_url': 'https://antigravity.google/docs/cli', 'auth_url': 'https://antigravity.google/docs/cli/headless'},
    'kimi': {'entry': 'Kimi Code CLI / Kimi Code login', 'login_argv': ['login'], 'model_picker': 'kimi → /model', 'install_url': 'https://www.kimi.com/code/docs/en/kimi-code-cli/guides/getting-started.html', 'auth_url': 'https://www.kimi.com/code/docs/en/kimi-code-cli/reference/kimi-command.html'},
    'api': {'entry': 'OpenAI-compatible Chat Completions API', 'auth_url': 'https://api-docs.deepseek.com/', 'model_picker': 'models NAME --fetch (requires API key)'},
}
# Subscription mode removes only known provider routing/credential overrides.
# OS HOME, keychain, CLI storage paths, proxy and CA settings remain intact.
PREFIXES = {
    'claude': ('ANTHROPIC_', 'CLAUDE_CODE_USE_', 'CLAUDE_CODE_OAUTH_TOKEN'),
    'codex': ('OPENAI_', 'CODEX_API_KEY', 'CODEX_ACCESS_TOKEN'),
    'gemini': ('GEMINI_API_KEY', 'GOOGLE_API_KEY', 'GOOGLE_GENAI_USE_VERTEXAI', 'GOOGLE_GENAI_USE_GCA', 'GOOGLE_GEMINI_BASE_URL'),
    'antigravity': ('GEMINI_API_KEY', 'GOOGLE_API_KEY', 'GOOGLE_GENAI_USE_VERTEXAI', 'GOOGLE_GENAI_USE_GCA', 'GOOGLE_GEMINI_BASE_URL'),
    'kimi': ('KIMI_MODEL', 'KIMI_BASE_URL', 'KIMI_API_KEY', 'KIMI_CODE_API_KEY', 'MOONSHOT_API_KEY'),
}


EXECUTABLES = {'antigravity': 'agy'}


def default_executable(kind):
    return EXECUTABLES.get(kind, kind)


def environment_for(spec, source=None):
    env = dict(os.environ if source is None else source)
    if spec.get('auth_mode', 'native') == 'subscription':
        for key in list(env):
            if any(key.startswith(p) for p in PREFIXES.get(spec['kind'], ())):
                del env[key]
    return env


def parse_kimi(raw):
    """Normalize documented JSONL Assistant messages; never consume tool text."""
    answers = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError('Kimi JSONL event 必须为对象')
        if obj.get('type') == 'error' or obj.get('error'):
            raise ValueError('Kimi 返回错误事件，查看 stdout.log')
        message = obj.get('message', obj)
        if not isinstance(message, dict):
            continue
        role = message.get('role', obj.get('type'))
        if role != 'assistant' or message.get('tool_calls'):
            continue
        content = message.get('content')
        if isinstance(content, list):
            content = ''.join(part.get('text', '') for part in content if isinstance(part, dict) and part.get('type') == 'text')
        if isinstance(content, str) and content.strip():
            answers.append(content)
    if not answers:
        raise ValueError('Kimi 输出没有完整 assistant 文本；检查 CLI 版本')
    return answers[-1]


# ---------------------------------------------------------------- Antigravity CLI (agy)
#
# Headless use as documented at antigravity.google/docs/cli/headless (2026-10): `agy -p "<prompt>"` for one question;
# `--input-format stream-json` (one {"event":"user","message":{"content":...}} per line on stdin) requires
# `--output-format stream-json` (events init / step_update / result); `--output-format json` gives one envelope with
# status (SUCCESS on success), response, error, usage. `--print-timeout` defaults to 5 minutes, so coop always passes
# the role's timeout. The exact event shapes on the user's Mac are what counts: the parser below accepts the documented
# field names and a few close variants, never tool or step text, and fails loudly otherwise.

AGY_SETTINGS = Path('~/.gemini/antigravity-cli/settings.json')
AGY_INPUTS = ('stream-json', 'argv')
AGY_EFFORTS = ('low', 'medium', 'high')
AGY_TIMEOUT_UNITS = ('s', 'ms', 'duration')


def antigravity_print_timeout(seconds, unit='s'):
    """--print-timeout value a little below coop's own hard deadline, so that agy can still report the timeout."""
    value = max(60, int(seconds) - 15)
    if unit == 'ms':
        return str(value * 1000)
    if unit == 'duration':
        return f'{value}s'
    return str(value)


def antigravity_argv(executable, spec, prompt, timeout):
    mode = spec.get('input', 'stream-json')
    if mode not in AGY_INPUTS:
        raise ValueError('antigravity input 只能是 ' + ' / '.join(AGY_INPUTS))
    if mode == 'argv':
        argv = [executable, '-p', prompt, '--output-format', 'json']
    else:
        argv = [executable, '-p', '--input-format', 'stream-json', '--output-format', 'stream-json']
    argv += ['--model', spec['model'], '--print-timeout', antigravity_print_timeout(timeout, spec.get('print_timeout_unit', 's'))]
    if spec.get('effort'):
        if spec['effort'] not in AGY_EFFORTS:
            raise ValueError('antigravity effort 只能是 ' + ' / '.join(AGY_EFFORTS))
        argv += ['--effort', spec['effort']]
    if spec.get('disable_slash_commands', True):
        argv.append('--disable-slash-commands')
    if '--dangerously-skip-permissions' in argv + list(spec.get('extra_args', [])):
        raise ValueError('coop 不使用 --dangerously-skip-permissions')
    return argv + list(spec.get('extra_args', []))


def antigravity_stdin(spec, prompt):
    if spec.get('input', 'stream-json') == 'argv':
        return ''
    return json.dumps({'event': 'user', 'message': {'content': prompt}}, ensure_ascii=False) + '\n'


def _event_type(obj):
    for key in ('event', 'type', 'kind'):
        if isinstance(obj.get(key), str):
            return obj[key].lower()
    return ''


def _text_of(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ('text', 'content', 'response', 'result'):
            if key in value:
                text = _text_of(value[key])
                if text is not None:
                    return text
        return None
    if isinstance(value, list):
        parts = [p.get('text') for p in value if isinstance(p, dict) and isinstance(p.get('text'), str)
                 and p.get('type', 'text') == 'text']
        return ''.join(parts) if parts else None
    return None


def _envelope(obj):
    """(status, response text or None, error text) of a json envelope or a result event."""
    inner = obj.get('result') if isinstance(obj.get('result'), dict) else obj
    status = inner.get('status', obj.get('status'))
    status = str(status).upper() if status is not None else ''
    response = None
    for key in ('response', 'result', 'message', 'output', 'text'):
        if key in inner and not (key == 'result' and inner is not obj):
            response = _text_of(inner[key])
            if response is not None:
                break
    error = inner.get('error', obj.get('error'))
    if isinstance(error, dict):
        error = error.get('message') or json.dumps(error, ensure_ascii=False)
    if not error and status and status != 'SUCCESS' and response:
        error, response = response, None   # e.g. {"status": "ERROR", "message": "..."}: the text is the error
    return status, response, (str(error) if error else '')


def parse_antigravity(raw, mode='stream-json'):
    """{'ok', 'status', 'response', 'error', 'usage', 'events'} from agy's stdout.

    stream-json: the last `result` event decides; init / step_update events (tool calls, thoughts, partial text) are
    never used as the answer. json: one envelope (a trailing log line before it is tolerated)."""
    usage = None
    if mode == 'argv':
        lines = [l for l in raw.splitlines() if l.strip()]
        candidates = [raw] + lines[::-1]
        obj = None
        for text in candidates:
            try:
                value = json.loads(text)
            except ValueError:
                continue
            if isinstance(value, dict):
                obj = value
                break
        if obj is None:
            raise ValueError('agy 的 json 输出不是 JSON 对象；检查 CLI 版本和 stdout.log')
        status, response, error = _envelope(obj)
        usage = obj.get('usage')
        events = ['json']
    else:
        events, result = [], None
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue  # a stray log line; the result event is required below
            if not isinstance(obj, dict):
                continue
            kind = _event_type(obj)
            events.append(kind or '?')
            if kind == 'result':
                result = obj
            elif kind in ('error', 'fatal') and result is None:
                result = {'status': 'ERROR', 'error': obj.get('error') or obj.get('message') or json.dumps(obj, ensure_ascii=False)}
        if result is None:
            raise ValueError('agy 的 stream-json 输出里没有 result 事件（输出不完整，或 CLI 的事件格式与适配不同）；'
                             '事件：' + ', '.join(events[-8:]))
        status, response, error = _envelope(result)
        usage = result.get('usage')
        if usage is None and isinstance(result.get('result'), dict):
            usage = result['result'].get('usage')
    ok = status == 'SUCCESS' and not error and isinstance(response, str) and bool(response.strip())
    if status == 'SUCCESS' and not error and not (isinstance(response, str) and response.strip()):
        error = 'agy 报告 SUCCESS 但没有 response 文本'
    return {'ok': ok, 'status': status or 'UNKNOWN', 'response': response if ok else None,
            'error': error or ('' if ok else 'status=' + (status or '缺失')), 'usage': usage, 'events': events[-20:]}


def _walk(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k, v
            yield from _walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from _walk(v)


def antigravity_billing(spec, environ=None):
    """Whether agy would bill an API key instead of the subscription, from its settings.json (key names only; values
    are never returned or printed)."""
    path = Path(spec.get('settings_path') or AGY_SETTINGS).expanduser()
    env = os.environ if environ is None else environ
    out = {'settings': str(path), 'exists': path.is_file(), 'model_provider': None, 'api_key_in_settings': False,
           'billing': 'subscription', 'note': ''}
    if not path.is_file():
        out['note'] = 'settings.json 不存在：按 agy 默认（登录的订阅账户）'
        return out
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        out.update(billing='unknown', note=f'settings.json 读不了（{type(exc).__name__}）；请在 agy 里确认计费来源')
        return out
    for key, value in _walk(data):
        if key == 'modelProvider' and isinstance(value, str):
            out['model_provider'] = value
        if key in ('GEMINI_API_KEY', 'GOOGLE_API_KEY', 'geminiApiKey', 'apiKey', 'api_key') and isinstance(value, str) and value.strip():
            out['api_key_in_settings'] = True
    provider = (out['model_provider'] or '').lower()
    env_key = spec.get('auth_mode') != 'subscription' and bool(env.get('GEMINI_API_KEY'))
    if provider == 'gemini' and (out['api_key_in_settings'] or env_key):
        out.update(billing='api', note='settings.json 设了 modelProvider: gemini 并配置了 GEMINI_API_KEY：agy 会走 Gemini API 按量计费，'
                                         '不是订阅额度。要用订阅，删掉这两项（或改回默认），再 check。')
    elif provider and provider not in ('antigravity', 'default', 'google'):
        out.update(billing='unknown', note=f'settings.json 的 modelProvider 是 {out["model_provider"]}：可能不走订阅，请在 agy 里确认')
    return out


_MODEL_LISTS = {}


def antigravity_models(spec, timeout=60, refresh=False):
    """The text of `agy models` (cached per executable for this process)."""
    exe = shutil.which(spec.get('executable') or default_executable('antigravity'))
    if not exe:
        raise RuntimeError('missing_executable: 找不到 agy；安装 Antigravity CLI，或 configure NAME --executable 指定绝对路径')
    if exe in _MODEL_LISTS and not refresh:
        return _MODEL_LISTS[exe]
    with tempfile.TemporaryDirectory() as d, tempfile.TemporaryFile() as capture:
        proc = subprocess.run([exe, 'models'], stdout=capture, stderr=subprocess.STDOUT, cwd=d, timeout=timeout,
                              env=environment_for(spec), stdin=subprocess.DEVNULL)
        capture.seek(0)
        text = capture.read(2_000_000).decode('utf-8', errors='replace')
    if proc.returncode:
        error = classify_error(text)
        raise RuntimeError(f'agy models 退出码 {proc.returncode}; {error["category"]}: {error["hint"]}; {text.strip()[:300]}')
    _MODEL_LISTS[exe] = text
    return text


def model_listed(slug, listing):
    """True when `slug` appears in the listing as a whole token (a JSON listing works as well as a table)."""
    return bool(slug) and re.search(r'(?<![\w.\-/])' + re.escape(slug) + r'(?![\w.\-/])', listing) is not None


def model_candidates(listing, word='argon'):
    tokens = re.findall(r'[\w][\w.\-/]*', listing)
    return sorted({t for t in tokens if word in t.lower()})


def check_antigravity_model(spec, timeout=60):
    """Raise unless the configured slug is in `agy models`: never fall back to another model."""
    slug = spec.get('model')
    if not slug:
        raise RuntimeError('model: antigravity provider 没有写模型 slug；用 configure NAME --model <agy models 里 Argon 的 slug>')
    listing = antigravity_models(spec, timeout)
    if not model_listed(slug, listing):
        found = model_candidates(listing)
        raise RuntimeError(f'model: 模型 slug {slug} 不在 agy models 列表里（not in agy models）；不会回退到其他模型。'
                           + (f'列表里含 argon 的有：{", ".join(found)}；用 configure NAME --model 改成其中正确的一项。' if found
                              else '列表里没有含 argon 的项，先在 agy 里确认账户能用 Argon。'))
    return {'model': slug, 'listed': True}


def preflight(cfg, names):
    """Before a run: every antigravity provider among `names` has its slug listed by `agy models`."""
    checked = {}
    for name in dict.fromkeys(names):
        spec = cfg['providers'].get(name)
        if spec and spec.get('kind') == 'antigravity':
            try:
                checked[name] = check_antigravity_model(spec)
            except RuntimeError as exc:
                raise ValueError(f'{name}：{exc}') from None
    return checked


def classify_error(message):
    s = str(message).lower()
    rules = [
        ('cli_version', ('unknown option', 'unrecognized argument', 'no such option'), '更新官方 CLI；查看其 --help，检查当前适配参数。'),
        ('billing', ('billing:', 'modelprovider'), '订阅模式下拒绝走 API 计费：检查 ~/.gemini/antigravity-cli/settings.json 的 modelProvider 与 API key，或明确改用 auth_mode native。'),
        ('rate_limit', ('429', 'rate limit', 'rate-limit', 'quota', 'usage limit', '额度', 'resource_exhausted', 'resource exhausted',
                        'too many requests', 'try again later', 'at capacity'), '等待额度恢复后 resume，或选择你已配置的其他模型。不会自动购买或切换付费入口。'),
        ('authentication', ('401', 'unauthorized', 'not logged', 'authentication', 'login', '登录', '环境变量', 'unauthenticated'), '运行 login NAME，或设置 API 所需的环境变量。'),
        ('model', ('model not found', 'invalid model', 'model_not_found', 'model_not_supported', 'unknown model', 'unrecognized model',
                   'unsupported model', 'no such model', 'not in agy models', '模型 slug'), '用官方 CLI /model、agy models 或 models NAME --fetch 查询，配置准确模型 ID；不会回退到其他模型。'),
        ('permission', ('403', 'forbidden', 'permission denied'), '检查账户权限、可用地区和所选模型；403 不一定是密钥错误。'),
        ('timeout', ('timed out', 'timeout', '超时', 'deadline exceeded'), '检查网络，或增加配置 timeout 后新建任务。'),
        ('missing_executable', ('no such file', 'not found', '找不到程序'), '安装 CLI 或通过 configure NAME --executable 指定绝对路径。'),
        ('network', ('connection', 'certificate', 'name resolution', 'urlopen', 'ssl'), '检查网络、代理与 CA 配置。'),
        ('protocol', ('json', '输出', 'finish_reason'), '查看本地原始输出，检查 CLI 版本及输出是否被截断。'),
    ]
    for category, markers, hint in rules:
        if category + ':' in s or any(m in s for m in markers):
            return {'category': category, 'hint': hint}
    return {'category': 'provider_error', 'hint': '查看该调用目录的 stderr.log 和原始响应；成功步骤会保留。'}


def inspect_provider(name, spec):
    kind = spec['kind']
    result = {'provider': name, 'kind': kind, 'model': spec.get('model') or 'CLI default', 'auth_mode': spec.get('auth_mode', 'native'), **CATALOG.get(kind, {})}
    if kind == 'api':
        result.update(key_env=spec['key_env'], key_present=bool(os.environ.get(spec['key_env'])), url=spec['url'])
    elif kind == 'demo':
        result['demo'] = True
    else:
        binary = spec.get('executable', default_executable(kind)) if kind != 'command' else spec['argv'][0]
        result['executable'] = shutil.which(binary)
        if kind in CATALOG and result['executable']:
            try:
                # --version is a local check, not a model request.
                with tempfile.TemporaryFile() as capture:
                    proc = subprocess.run([result['executable'], '--version'], stdout=capture, stderr=capture, timeout=5, env=environment_for(spec))
                    capture.seek(0)
                    result['version'] = capture.read(1000).decode('utf-8', errors='replace').strip()
                    result['version_exit_code'] = proc.returncode
            except (OSError, subprocess.TimeoutExpired):
                result['version'] = 'unavailable'
    if kind == 'antigravity':
        # Local only: settings.json decides whether agy bills the subscription or a Gemini API key.
        result['billing'] = antigravity_billing(spec)
        result['input'] = spec.get('input', 'stream-json')
        result['effort'] = spec.get('effort') or 'CLI default'
        if result['billing']['billing'] != 'subscription':
            result['warning'] = result['billing']['note']
        result['model_check'] = 'check NAME 或 models NAME --fetch 会运行 agy models 核对 slug'
    clean = environment_for(spec)
    result['ignored_environment_names'] = sorted(set(os.environ) - set(clean))
    result['authentication_verified'] = False
    return result


def configure(path, name, model=None, executable=None, auth_mode=None, reset_model=False, kind=None):
    from .core import validate_config
    path = Path(path)
    cfg = json.loads(path.read_text(encoding='utf-8'))
    if name not in cfg['providers']:
        raise ValueError('未知 provider: ' + name)
    spec = cfg['providers'][name]
    if kind is not None:
        # Only between the two Google entries: the Antigravity CLI (subscription) and the Gemini CLI (paid API key).
        if kind not in ('gemini', 'antigravity') or spec['kind'] not in ('gemini', 'antigravity'):
            raise ValueError('kind 只能在 gemini 与 antigravity 之间切换')
        if kind != spec['kind']:
            spec['kind'] = kind
            spec.pop('executable', None)
            if kind == 'antigravity' and model is None and not spec.get('model'):
                raise ValueError('切到 antigravity 时要同时给出 --model（agy models 里 Argon 的 slug）')
    if model is not None:
        if not model.strip():
            raise ValueError('model 不能为空')
        spec['model'] = model.strip()
    if reset_model:
        if spec['kind'] == 'api':
            raise ValueError('API 必须指定模型')
        spec['model'] = None
    if executable is not None:
        if spec['kind'] not in ('codex', 'claude', 'gemini', 'kimi', 'antigravity'):
            raise ValueError('executable 只适用于官方 CLI')
        if not Path(executable).expanduser().is_absolute():
            raise ValueError('executable 必须是绝对路径')
        spec['executable'] = str(Path(executable).expanduser())
    if auth_mode is not None:
        allowed = ('api',) if spec['kind'] == 'api' else ('subscription', 'native')
        if auth_mode not in allowed:
            raise ValueError('此 provider 不支持该 auth_mode')
        spec['auth_mode'] = auth_mode
    validate_config(cfg)
    # Atomic replacement, no partial JSON if interrupted during write.
    fd, tmp = tempfile.mkstemp(prefix='config-', suffix='.json', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)
    return {'provider': name, 'configuration': spec, 'applies_to': 'new jobs only'}


def login(name, spec):
    kind = spec['kind']
    if kind == 'api':
        return {'provider': name, 'key_env': spec['key_env'], 'instruction': '在本机终端设置该环境变量。不要把密钥发进聊天或写入 config.json。'}
    if kind not in CATALOG:
        raise ValueError('此 provider 没有官方登录入口')
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError('请在你 Mac 的交互终端运行 login；不接收聊天中的密码或验证码')
    binary = shutil.which(spec.get('executable', default_executable(kind)))
    if not binary:
        raise ValueError('找不到程序，安装地址：' + CATALOG[kind]['install_url'])
    argv = [binary, *CATALOG[kind]['login_argv']]
    print('正在启动官方登录入口。' + ('agy 没有 login 子命令：第一次交互运行时按提示用订阅所在的 Google 账户登录，完成后退出 agy。'
                                    if kind == 'antigravity' else 'Gemini 请选 Sign in with Google，完成后 /quit 返回。'), file=sys.stderr)
    # Preserve native TTY for browser/device-code login. No credential interception.
    result = subprocess.run(argv, env=environment_for(spec))
    return {'provider': name, 'native_exit_code': result.returncode, 'next': 'check ' + name, 'note': '退出码不代表额度或所选模型已验证'}


def probe(root, name, spec, timeout):
    from .providers import invoke, reset_cancel
    folder = Path(root) / 'checks' / (str(int(time.time())) + '-' + uuid.uuid4().hex[:8] + '-' + re.sub(r'[^a-zA-Z0-9_-]', '_', name))
    folder.mkdir(parents=True)
    result = {'provider': name, 'directory': str(folder), 'configured_model': spec.get('model'), 'is_real_request': spec['kind'] != 'demo'}
    reset_cancel()
    try:
        if spec['kind'] == 'antigravity':
            result['model_listed'] = check_antigravity_model(spec, min(timeout, 60))['listed']
        raw = invoke(spec, 'Connectivity check. Do not use any tools. Return ONLY this JSON object: {"ok":true}', '__probe__', folder, timeout)
        (folder / 'raw.txt').write_text(raw, encoding='utf-8')
        clean = raw.strip()
        if clean.startswith('```') and clean.endswith('```'):
            clean = clean.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        if json.loads(clean) != {'ok': True}:
            raise ValueError('JSON 未符合连通性检查约定')
        result['state'] = 'demo' if spec['kind'] == 'demo' else 'passed'
    except Exception as exc:
        result.update(state='failed', **classify_error(exc))
        # Details remain local; short summary avoids echoing arbitrary vendor errors.
        result['error_type'] = type(exc).__name__
    (folder / 'check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def model_info(root, name, spec, fetch=False, timeout=30):
    result = {'provider': name, 'configured_model': spec.get('model'), 'picker': CATALOG.get(spec['kind'], {}).get('model_picker', 'edit config.json')}
    if not fetch:
        return result
    if spec['kind'] == 'antigravity':
        listing = antigravity_models(spec, timeout, refresh=True)
        result['models_output'] = [l for l in listing.splitlines() if l.strip()][:200]
        result['argon_candidates'] = model_candidates(listing)
        result['configured_model_listed'] = model_listed(spec.get('model'), listing)
        return result
    if spec['kind'] != 'api':
        raise ValueError('CLI 未假设统一模型列表接口，请使用返回的原生模型选择入口')
    from .providers import invoke, reset_cancel
    folder = Path(root) / 'checks' / ('models-' + uuid.uuid4().hex[:12]); folder.mkdir(parents=True)
    reset_cancel()
    body = json.loads(invoke(spec, '', '__models__', folder, timeout))
    result['models'] = body['data']
    return result
