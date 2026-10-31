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
    'gemini': {'entry': 'Gemini CLI / Sign in with Google', 'login_argv': [], 'model_picker': 'gemini → /model', 'install_url': 'https://geminicli.com/docs/get-started/installation/', 'auth_url': 'https://geminicli.com/docs/get-started/authentication/'},
    'kimi': {'entry': 'Kimi Code CLI / Kimi Code login', 'login_argv': ['login'], 'model_picker': 'kimi → /model', 'install_url': 'https://www.kimi.com/code/docs/en/kimi-code-cli/guides/getting-started.html', 'auth_url': 'https://www.kimi.com/code/docs/en/kimi-code-cli/reference/kimi-command.html'},
    'api': {'entry': 'OpenAI-compatible Chat Completions API', 'auth_url': 'https://api-docs.deepseek.com/', 'model_picker': 'models NAME --fetch (requires API key)'},
}
# Subscription mode removes only known provider routing/credential overrides.
# OS HOME, keychain, CLI storage paths, proxy and CA settings remain intact.
PREFIXES = {
    'claude': ('ANTHROPIC_', 'CLAUDE_CODE_USE_', 'CLAUDE_CODE_OAUTH_TOKEN'),
    'codex': ('OPENAI_', 'CODEX_API_KEY', 'CODEX_ACCESS_TOKEN'),
    'gemini': ('GEMINI_API_KEY', 'GOOGLE_API_KEY', 'GOOGLE_GENAI_USE_VERTEXAI', 'GOOGLE_GENAI_USE_GCA', 'GOOGLE_GEMINI_BASE_URL'),
    'kimi': ('KIMI_MODEL', 'KIMI_BASE_URL', 'KIMI_API_KEY', 'KIMI_CODE_API_KEY', 'MOONSHOT_API_KEY'),
}


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


def classify_error(message):
    s = str(message).lower()
    rules = [
        ('cli_version', ('unknown option', 'unrecognized argument', 'no such option'), '更新官方 CLI；查看其 --help，检查当前适配参数。'),
        ('rate_limit', ('429', 'rate limit', 'quota', 'usage limit', '额度'), '等待额度恢复，或选择你已配置的其他模型。不会自动购买或切换付费入口。'),
        ('authentication', ('401', 'unauthorized', 'not logged', 'authentication', 'login', '登录', '环境变量'), '运行 login NAME，或设置 API 所需的环境变量。'),
        ('model', ('model not found', 'invalid model', 'model_not_found', 'model_not_supported'), '用官方 CLI /model 或 models NAME --fetch 查询，配置准确模型 ID。'),
        ('permission', ('403', 'forbidden', 'permission denied'), '检查账户权限、可用地区和所选模型；403 不一定是密钥错误。'),
        ('timeout', ('timed out', 'timeout', '超时'), '检查网络，或增加配置 timeout 后新建任务。'),
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
        binary = spec.get('executable', kind) if kind != 'command' else spec['argv'][0]
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
    clean = environment_for(spec)
    result['ignored_environment_names'] = sorted(set(os.environ) - set(clean))
    result['authentication_verified'] = False
    return result


def configure(path, name, model=None, executable=None, auth_mode=None, reset_model=False):
    from .core import validate_config
    path = Path(path)
    cfg = json.loads(path.read_text(encoding='utf-8'))
    if name not in cfg['providers']:
        raise ValueError('未知 provider: ' + name)
    spec = cfg['providers'][name]
    if model is not None:
        if not model.strip():
            raise ValueError('model 不能为空')
        spec['model'] = model.strip()
    if reset_model:
        if spec['kind'] == 'api':
            raise ValueError('API 必须指定模型')
        spec['model'] = None
    if executable is not None:
        if spec['kind'] not in ('codex', 'claude', 'gemini', 'kimi'):
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
    binary = shutil.which(spec.get('executable', kind))
    if not binary:
        raise ValueError('找不到程序，安装地址：' + CATALOG[kind]['install_url'])
    argv = [binary, *CATALOG[kind]['login_argv']]
    print('正在启动官方登录入口。Gemini 请选 Sign in with Google，完成后 /quit 返回。', file=sys.stderr)
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
    if spec['kind'] != 'api':
        raise ValueError('CLI 未假设统一模型列表接口，请使用返回的原生模型选择入口')
    from .providers import invoke, reset_cancel
    folder = Path(root) / 'checks' / ('models-' + uuid.uuid4().hex[:12]); folder.mkdir(parents=True)
    reset_cancel()
    body = json.loads(invoke(spec, '', '__models__', folder, timeout))
    result['models'] = body['data']
    return result
