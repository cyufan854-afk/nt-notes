#!/usr/bin/env python3
"""StartLux 27B 的 MCP-Universe 原始日志 -> 训练 notebook 读的轨迹 JSONL（一次任务运行一行）。只用标准库。

    python3 convert_mcp_universe.py <01_mcp_universe 目录> --out startlux_mcp_universe_runs.jsonl

<01_mcp_universe 目录> 里要有 organized/tasks_index.jsonl，以及解开的原始日志 startlux-27b-260804/（解压
startlux-27b-260804.original_logs.tar.xz 得到）。

每次运行重建一段标准的多轮对话：
- 第一条用户消息（任务说明）；
- 每次模型调用一个助手回合：思考（reasoning_content）、正文、工具调用，取自这次调用的 API 响应；
- 工具返回取自“下一次调用的请求历史”，也就是模型实际看到的文字。网页搜索和浏览器自动化里，框架会先让模型把原始返回
  改写一遍再放进上下文，这里用的就是改写后的版本；
- 框架在每一步之后插入的 “You have N steps remaining. Please continue.” 默认不保留（--keep-reminders 保留）：
  去掉后，所有助手回合都在最后一条用户消息之后，Qwen 的 chat template 会保留每一步的思考。

工具定义没有记在日志里，按领域把所有运行中出现过的调用汇总成最简定义（参数名和 JSON 类型，没有说明文字）。
每一行带 passed（历史评分）、domain、task、run、round 和来源文件的 SHA-256，训练 notebook 默认只用 passed=true 的。
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import sys

REMINDER = re.compile(r'^You have \d+ steps? remaining\. Please continue\.\s*$')


def load_documents(path):
    """A trace file may hold several JSON documents written one after another."""
    text = Path(path).read_text(encoding='utf-8')
    dec, docs, i = json.JSONDecoder(), [], 0
    while i < len(text):
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text):
            break
        obj, i = dec.raw_decode(text, i)
        docs.append(obj)
    return docs


def model_calls(docs, trace_ids):
    """The agent's model calls of these traces in time order: (request messages, response message, finish reason)."""
    calls = []
    for doc in docs:
        for span in doc if isinstance(doc, list) else [doc]:
            if trace_ids and span.get('trace_id') not in trace_ids:
                continue
            for rec in span.get('records', []):
                d = rec.get('data') or {}
                resp = d.get('response')
                if d.get('type') != 'llm' or not d.get('messages') or not isinstance(resp, dict) or not resp.get('choices'):
                    continue
                choice = resp['choices'][0]
                calls.append((rec.get('timestamp', span.get('timestamp', 0)), d['messages'], choice['message'], choice.get('finish_reason')))
    calls.sort(key=lambda c: c[0])
    return [c[1:] for c in calls]


def text_of(content):
    if content is None:
        return ''
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ''.join(str(p.get('text', '')) if isinstance(p, dict) else str(p) for p in content)
    return json.dumps(content, ensure_ascii=False)


def assistant_turn(message):
    out = {'role': 'assistant', 'content': message.get('content') or ''}
    if message.get('reasoning_content'):
        out['reasoning_content'] = message['reasoning_content']
    calls = message.get('tool_calls') or []
    if calls:
        out['tool_calls'] = [{'id': c.get('id'), 'type': 'function',
                              'function': {'name': c['function']['name'], 'arguments': c['function'].get('arguments') or '{}'}}
                             for c in calls]
    return out


def rebuild(calls, keep_reminders=False):
    """Standard messages from the model calls of one run. Raises ValueError when the request histories do not line up
    with the responses (then the run is skipped and reported)."""
    if not calls:
        raise ValueError('没有模型调用')
    first = calls[0][0]
    if not first or first[0].get('role') != 'user':
        raise ValueError('第一次调用的请求不是以用户消息开头')
    messages = [{'role': 'user', 'content': text_of(first[0].get('content'))}]
    for k, (request, response, _) in enumerate(calls):
        turn = assistant_turn(response)
        messages.append(turn)
        if k + 1 == len(calls):
            break
        # what the next call saw after this turn: the tool results (and the framework's reminder)
        nxt = calls[k + 1][0]
        ids = [c['id'] for c in turn.get('tool_calls', [])]
        found = {}
        tail = []
        for m in nxt[len(request):]:
            if m.get('role') == 'tool':
                found[m.get('tool_call_id')] = text_of(m.get('content'))
            elif m.get('role') == 'user':
                tail.append(text_of(m.get('content')))
        missing = [i for i in ids if i not in found]
        if missing:
            raise ValueError(f'第 {k + 1} 步的工具调用在下一次请求里没有返回：{missing[:3]}')
        extra = set(found) - set(ids)
        if extra:
            raise ValueError(f'第 {k + 1} 步之后出现了不属于这一步的工具返回：{sorted(extra)[:3]}')
        for i in ids:
            messages.append({'role': 'tool', 'tool_call_id': i, 'content': found[i]})
        for text in tail:
            if keep_reminders or not REMINDER.match(text):
                messages.append({'role': 'user', 'content': text})
        if not ids and not tail:
            raise ValueError(f'第 {k + 1} 步既没有工具调用也没有后续用户消息，下一次调用却继续了')
    return messages


def json_type(value):
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, int):
        return 'integer'
    if isinstance(value, float):
        return 'number'
    if isinstance(value, list):
        return 'array'
    if isinstance(value, dict):
        return 'object'
    return 'string'


def domain_tools(runs):
    """{domain: [function schema]} from every call made in that domain (parameter names and JSON types seen;
    required = present in every call). The logs do not hold the real definitions, so there are no descriptions."""
    seen = collections.defaultdict(dict)
    for run in runs:
        for m in run['messages']:
            for c in m.get('tool_calls', []):
                f = c['function']
                try:
                    args = json.loads(f['arguments']) if isinstance(f['arguments'], str) else f['arguments']
                except ValueError:
                    args = {}
                entry = seen[run['domain']].setdefault(f['name'], {'calls': 0, 'params': {}})
                entry['calls'] += 1
                for key, value in (args or {}).items():
                    p = entry['params'].setdefault(key, {'types': set(), 'count': 0})
                    p['types'].add(json_type(value))
                    p['count'] += 1
    out = {}
    for domain, tools in seen.items():
        out[domain] = []
        for name in sorted(tools):
            e = tools[name]
            props = {k: {'type': sorted(p['types'])[0] if len(p['types']) == 1 else sorted(p['types'])} for k, p in sorted(e['params'].items())}
            out[domain].append({'type': 'function', 'function': {'name': name, 'description': '', 'parameters': {
                'type': 'object', 'properties': props, 'required': [k for k, p in sorted(e['params'].items()) if p['count'] == e['calls']]}}})
    return out


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('root', help='01_mcp_universe 目录')
    ap.add_argument('--out', default='startlux_mcp_universe_runs.jsonl')
    ap.add_argument('--keep-reminders', action='store_true', help='保留框架插入的“还剩 N 步”用户消息')
    a = ap.parse_args(argv)
    root = Path(a.root)
    index = [json.loads(line) for line in (root / 'organized' / 'tasks_index.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    runs, skipped = [], collections.Counter()
    problems = []
    for row in index:
        trace_files = [p for p in row['source_files'] if re.search(r'/trace_[0-9_]+\.json$', p)]
        if len(trace_files) != 1:
            skipped['trace 文件不是恰好一个'] += 1
            continue
        path = root / trace_files[0]
        try:
            calls = model_calls(load_documents(path), set(row.get('trace_ids') or []))
            messages = rebuild(calls, a.keep_reminders)
        except (ValueError, KeyError, OSError) as error:
            skipped[str(error).split('：')[0]] += 1
            problems.append(f"{row['run']} {row['task']}: {error}")
            continue
        if len(calls) != row.get('model_calls'):
            skipped['模型调用数与索引不符'] += 1
            problems.append(f"{row['run']} {row['task']}: 调用 {len(calls)}，索引 {row.get('model_calls')}")
            continue
        runs.append({'id': f"{row['run']}/{Path(row['task']).name}", 'task': row['task'], 'domain': row['domain'],
                     'run': row['run'], 'round': row.get('round'), 'passed': bool(row['passed']),
                     'last_finish_reason': row.get('last_finish_reason'), 'model': row.get('model'),
                     'model_calls': len(calls), 'messages': messages,
                     'source': {'trace_file': trace_files[0], 'sha256': sha256(path)}})
    tools = domain_tools(runs)
    with open(a.out, 'w', encoding='utf-8') as f:
        for run in runs:
            f.write(json.dumps({**run, 'tools': tools[run['domain']]}, ensure_ascii=False) + '\n')
    by = collections.Counter((r['domain'], r['passed']) for r in runs)
    report = {'runs_written': len(runs), 'passed': sum(r['passed'] for r in runs), 'skipped': dict(skipped),
              'by_domain': {d: {'passed': by[(d, True)], 'failed': by[(d, False)], 'tools': len(tools.get(d, []))}
                            for d in sorted({r['domain'] for r in runs})},
              'problems': problems[:20], 'reminders_kept': a.keep_reminders}
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if runs else 1


if __name__ == '__main__':
    sys.exit(main())
