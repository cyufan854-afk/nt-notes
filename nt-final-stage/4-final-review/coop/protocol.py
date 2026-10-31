"""Model-authored metadata is JSON; mathematical bodies are never JSON-decoded."""
import json
import re

META = '<<<COOP_META>>>'
BODY = '<<<COOP_BODY>>>'
END = '<<<COOP_END>>>'
ASSESSMENTS = {'false_positive', 'confirmed', 'fixed', 'unknown'}
VERDICTS = {'approve', 'approve_with_notes', 'revise', 'unresolved'}


def encode(meta, body):
    return META + '\n' + json.dumps(meta, ensure_ascii=False) + '\n' + BODY + '\n' + body + '\n' + END


def parse(raw, kind, issue_filter=None):
    if not isinstance(raw, str):
        raise ValueError('响应必须是文本')
    # Remove only whitespace outside the frame, never strip the mathematical body.
    raw = raw.strip()
    if not raw.startswith(META + '\n') or not raw.endswith('\n' + END):
        raise ValueError('缺少 COOP 元数据/正文边界；不接受正文嵌入 JSON 的旧协议')
    content = raw[len(META) + 1:-(len(END) + 1)]
    marker = '\n' + BODY + '\n'
    if content.count(marker) != 1:
        raise ValueError('COOP_BODY 边界必须恰好一个')
    header, body = content.split(marker, 1)
    if any(line in (META, END) for line in body.splitlines()):
        raise ValueError('正文中不能出现独立的协议边界行')
    meta = json.loads(header)
    if not isinstance(meta, dict) or meta.get('kind') != kind:
        raise ValueError('元数据 kind 与岗位不匹配')
    def check_controls(value):
        if isinstance(value, str) and any(ord(c) < 32 for c in value):
            raise ValueError('元数据含控制字符，疑似 LaTeX 转义；数学内容必须移入 Markdown 正文')
        if isinstance(value, dict):
            for key, item in value.items():
                check_controls(key); check_controls(item)
        elif isinstance(value, list):
            for item in value:
                check_controls(item)
    check_controls(meta)
    if not body.strip():
        raise ValueError('正文不能为空')
    if any(ord(c) < 32 and c not in '\n\r\t' for c in body):
        raise ValueError('正文含异常控制字符；保留 raw.txt 供复查')
    if meta.get('assessment', 'unknown') not in ASSESSMENTS:
        raise ValueError('assessment 非法')
    for key in ('check', 'evidence_accepted'):
        if key in meta and type(meta[key]) is not bool:
            raise ValueError(key + ' 必须是布尔值')
    if 'evidence_ids' in meta:
        if not isinstance(meta['evidence_ids'], list) or not all(isinstance(x, str) for x in meta['evidence_ids']):
            raise ValueError('evidence_ids 必须为字符串列表')
    if issue_filter is not None:
        # Mode-specific normalisation (e.g. edit loop downgrades blockers without location)
        # runs before the generic verdict adjustment below.
        meta['issues'] = issue_filter(meta.get('issues', []))
    if kind == 'review':
        if meta.get('verdict') not in VERDICTS:
            raise ValueError('审查 verdict 非法')
        issues = meta.setdefault('issues', [])
        if not isinstance(issues, list):
            raise ValueError('issues 必须为列表')
        for issue in issues:
            if isinstance(issue, str):
                continue  # Legacy advisory strings are tolerated, never treated as blockers.
            if not isinstance(issue, dict) or not isinstance(issue.get('id'), str) or issue.get('severity') not in ('note', 'blocking'):
                raise ValueError('issue 需要 id 和 severity=note/blocking，解释放正文')
        if meta['verdict'] in ('approve', 'approve_with_notes'):
            if any(isinstance(x, dict) and x['severity'] == 'blocking' for x in issues):
                meta['verdict'] = 'revise'
            elif issues:
                meta['verdict'] = 'approve_with_notes'
    return {'meta': meta, 'body': body}


def check_script(response):
    if not response['meta'].get('check', False):
        return None
    matches = re.findall(r'^```python coop-check\r?\n(.*?)^```[ \t]*$', response['body'], flags=re.MULTILINE | re.DOTALL)
    if len(matches) != 1:
        raise ValueError('check=true 时必须有且仅有一个 python coop-check 代码块')
    script = matches[0]
    if len(script.encode()) > 100_000:
        raise ValueError('检查脚本超过 100 KB')
    if not script.strip():
        raise ValueError('检查脚本不能为空')
    return script


def instruction(kind):
    meta = {'kind': kind}
    if kind == 'analysis':
        meta.update(assessment='unknown', check=False)
    elif kind == 'review':
        meta.update(verdict='approve', assessment='unknown', issues=[], evidence_accepted=False, evidence_ids=[])
    return ('严格使用以下帧格式；JSON 只放控制元数据，正文/数学公式/解释不得放进 JSON。'
            'verdict 可选 approve/approve_with_notes/revise/unresolved；assessment 可选 '
            'false_positive/confirmed/fixed/unknown。issues 使用 {"id":"I1","severity":"note"}，'
            '严重问题 severity=blocking，解释写在正文。元数据示例的值不是预定结论。\n' +
            encode(meta, '这里直接写 Markdown 与 LaTeX，反斜杠保持原样。') + '\n'
            '如需计算，在 analysis 元数据设 check=true，并在正文提供且只提供一个 '
            '```python coop-check 代码块。只用 Python 标准库，明确输入范围，输出检查对象与结果；'
            '不要声称已运行。代码由调度器在无网络容器中执行。'
            'review 只审查当前 branch；只可根据 execution 中真实记录判断执行证据，'
            'evidence_ids 引用实际记录 id。脚本能运行不代表证明成立；核对它检查了什么。')
