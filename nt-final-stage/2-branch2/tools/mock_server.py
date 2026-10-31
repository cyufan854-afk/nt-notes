#!/usr/bin/env python3
"""A fake OpenAI-compatible server for testing nt27b end to end without a model.

    python3 tools/mock_server.py --port 8099
    python3 nt27b.py ask job --base-url http://127.0.0.1:8099/v1 --concurrency 8

Answers are deliberately mixed: good edits, edits that change a formula (must be rejected), quotes that are
not verbatim (must be flagged), and an occasional non-JSON first reply (must trigger a format retry).
It never says anything meaningful about the mathematics. Standard library only.
"""
import argparse
import hashlib
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SEEN = {}


def h(text):
    return int(hashlib.sha256(text.encode('utf-8')).hexdigest()[:8], 16)


def between(text, a, b):
    i = text.find(a)
    if i < 0:
        return ''
    i += len(a)
    j = text.find(b, i)
    return text[i:j if j >= 0 else len(text)]


def plain_spans(text):
    """Stretches of text without $, \\, braces: safe to quote and to edit."""
    return [m for m in re.finditer(r'[A-Za-z][A-Za-z ,;]{30,120}', text)]


def polish(user, n):
    block = between(user, '### Block to edit\n', '\n### End of block')
    spans = [m.group(0).strip() for m in plain_spans(block)]
    spans = [s for s in spans if block.count(s) == 1 and ' the ' in s]
    if not spans or n % 4 == 0:
        return {'verdict': 'keep', 'revisions': [], 'note_zh': '这一块没有需要改的英语问题。'}
    s = spans[0]
    revs = [{'original': s, 'revised': s.replace(' the ', ' this ', 1)}]
    if n % 5 == 1:
        m = re.search(r'\$[^$]{1,40}\$', block)
        if m and block.count(m.group(0)) == 1:
            revs.append({'original': m.group(0), 'revised': m.group(0).replace('$', '$\\,', 1)})
    if n % 7 == 2:
        revs.append({'original': 'This sentence is not in the block at all.', 'revised': 'Nor is this one.'})
    note = '改了冠词。' + ('数学疑点：这里的条件好像少了一个。' if n % 23 == 0 else '')
    return {'verdict': 'revise', 'revisions': revs, 'note_zh': note}


def triage(user, n):
    ctx = between(user, '### Context (current text of the book)\n', '\n### End of context')
    quote = between(user, 'Quoted text: ', '\nReported issue:').strip()
    spans = [m.group(0).strip() for m in plain_spans(ctx)]
    k = n % 5
    if k in (0, 1):
        ev = spans[0] if spans and k == 0 else 'The book clearly says so somewhere.'
        return {'verdict': 'resolved', 'evidence': ev, 'patch_original': '', 'patch_revised': '',
                'note_zh': '上下文已经说明。'}
    if k == 2:
        return {'verdict': 'obvious', 'evidence': '', 'patch_original': '', 'patch_revised': '',
                'note_zh': '读者自然会补上。'}
    if k == 3 and quote and quote in ctx:
        return {'verdict': 'real_gap', 'evidence': '', 'patch_original': quote,
                'patch_revised': quote + ' (with $x\\in\\mathbb{Z}$)', 'note_zh': '定义域没写明，补一句。'}
    return {'verdict': 'cannot_decide', 'evidence': '', 'patch_original': '', 'patch_revised': '',
            'note_zh': '需要看别处的定义。'}


def refs(user, n):
    cited = between(user, '### Cited statement', '\n### End')
    spans = [m.group(0).strip() for m in plain_spans(cited)]
    fact = spans[0] if spans else cited.split('\n', 1)[-1].strip()
    k = n % 6
    if k == 0:
        return {'verdict': 'hypotheses_unchecked', 'cited_fact': fact, 'missing_hypotheses': ['gcd(a, n) = 1'],
                'note_zh': '没有说明互素。'}
    if k == 1:
        return {'verdict': 'supports', 'cited_fact': 'a made-up quotation', 'missing_hypotheses': [],
                'note_zh': '支持。'}
    if k == 2:
        return {'verdict': 'mismatch', 'cited_fact': '', 'missing_hypotheses': [], 'note_zh': '引用的定理不给这个结论。'}
    return {'verdict': 'supports', 'cited_fact': fact, 'missing_hypotheses': [], 'note_zh': '支持。'}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.rstrip('/').endswith('/models'):
            return self.send({'data': [{'id': 'mock-27b'}]})
        self.send({'error': 'not found'}, 404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))).decode('utf-8'))
        msgs = body['messages']
        system, user = msgs[0]['content'], msgs[1]['content']
        task = re.search(r'\[task: (\w+)\]', system).group(1)
        n = h(user)
        key = hashlib.sha256(user.encode()).hexdigest()
        SEEN[key] = SEEN.get(key, 0) + 1
        if n % 17 == 3 and len(msgs) == 2:                 # first try: unusable reply
            text = 'Sure! Here is my answer: verdict revise, I changed some words.'
        else:
            answer = {'polish': polish, 'triage': triage, 'refs': refs}[task](user, n)
            text = json.dumps(answer, ensure_ascii=False)
            if n % 3 == 0:
                text = '```json\n' + text + '\n```'
        self.send({'model': body.get('model'), 'choices': [{'message': {'role': 'assistant', 'content': text},
                                                            'finish_reason': 'stop'}],
                   'usage': {'prompt_tokens': sum(len(m['content']) for m in msgs) // 3,
                             'completion_tokens': len(text) // 3}})


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--port', type=int, default=8099)
    a = p.parse_args()
    ThreadingHTTPServer(('127.0.0.1', a.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
