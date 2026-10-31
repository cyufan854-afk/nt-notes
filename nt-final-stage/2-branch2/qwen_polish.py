#!/usr/bin/env python3
"""Language polish for nt.tex with your 27B fine-tune (any OpenAI-compatible endpoint), AFTER the math audit,
and a quality test of that fine-tune.

Order (r6): the DeepSeek math audit runs first and its repairs go into nt.tex; the language list
(语言问题清单.txt, bundled next to this script) is then handed to the 27B fine-tune. Because the list was
written against the pre-audit manuscript, sentences that the math repairs rewrote are detected and
skipped (pass --pre-audit-tex to tell "rewritten by the audit" apart from "never matched").

Step 1 – ask:    one request per candidate of the list.
  Output: OUT/results.jsonl (one line per answer, resumable) and OUT/review.md, where every
          proposed change has a checkbox and an editable replacement.
Step 2 – decide: tick "- [x] 接受" in review.md; you may edit the text under "改为".
          Re-running step 1 keeps your ticks and edits.
Step 3 – apply:  write OUT/nt.polished.tex + OUT/polish.diff + OUT/apply-report.md.
          The input nt.tex is never modified. A change whose original text is missing,
          ambiguous or overlapping another change is skipped and listed, never guessed.
Quality test of the fine-tune:
  --report            OUT/quality-report.md (+ quality.json): format compliance, retries, math-token
                      changes, verbatim/locatable originals, edit size, your acceptance rate, speed.
  --compare OTHER_OUT blind A/B review against another run (e.g. the base model without the
                      fine-tune): OUT/compare-<OTHER>/blind.md to tick, result.md with the tally.

Examples
  # local MLX server with the fine-tune (mlx_lm.server, default port 8080); list defaults to the bundled one
  python3 qwen_polish.py --tex nt.tex --pre-audit-tex nt.before-audit.tex --out polish-27b
  # the same list on the base model, for comparison
  python3 qwen_polish.py --tex nt.tex --out polish-base --base-url http://127.0.0.1:8081/v1
  python3 qwen_polish.py --report --tex nt.tex --out polish-27b
  python3 qwen_polish.py --compare polish-base --out polish-27b
  # Hugging Face Inference Endpoint (vLLM engine), token in HF_TOKEN, 8 requests in flight
  python3 qwen_polish.py --tex nt.tex --concurrency 8 --json-schema \\
      --base-url https://XXXX.endpoints.huggingface.cloud/v1 --api-key-env HF_TOKEN
  # check parsing, what is still found in nt.tex, and the first prompt, without sending anything
  python3 qwen_polish.py --tex nt.tex --dry-run
  # after ticking review.md
  python3 qwen_polish.py --apply --tex nt.tex --out polish-27b

Standard library only; Python 3.9+.
"""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import difflib
import hashlib
import json
import os
import random
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

VERSION = '2.1.1'

SYSTEM_PROMPT = r"""You are a copy-editor for English mathematical writing in LaTeX (a number-theory textbook).
You receive ONE candidate: a quotation from an earlier version of the manuscript, a short description
of a suspected language problem (written in Chinese by another reviewer, who may be wrong), and the
corresponding passage of the CURRENT manuscript.

The mathematics has already been audited and corrected; it is out of scope for you. Never change it,
even if it looks wrong. If you notice a possible mathematical problem, leave the text as it is and say
so in note_zh, starting that sentence with "数学疑点：".
The current manuscript is authoritative: if it differs from the quotation, work on the current text.

Rules:
1. Improve only the English: grammar, idiom, flow, punctuation, consistency. Keep the register of a
   rigorous textbook.
2. Never change the mathematics: keep every formula, symbol, variable name, hypothesis, quantifier,
   \ref/\label/\cite, theorem number and the logical content exactly, in the same order. Do not add
   or remove claims.
3. Keep valid LaTeX and the author's macros (e.g. \leg, \ZmodUnits, \id). No Markdown.
4. Change as little as needed. If the text is already fine, or fixing it would require changing the
   mathematics, answer with verdict "keep" and explain.
5. Each "original" must be copied VERBATIM from the current manuscript text given to you (a complete
   sentence or clause, long enough to be unique), and "revised" is its full replacement.

Answer with ONE JSON object and nothing else:
{"verdict": "revise" or "keep",
 "revisions": [{"original": "...", "revised": "..."}],
 "note_zh": "一两句中文说明：改了什么、为什么；或为什么不改"}"""

ANSWER_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['verdict', 'revisions', 'note_zh'],
    'properties': {
        'verdict': {'type': 'string', 'enum': ['revise', 'keep']},
        'revisions': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False, 'required': ['original', 'revised'],
            'properties': {'original': {'type': 'string'}, 'revised': {'type': 'string'}}}},
        'note_zh': {'type': 'string'}}}

MATH_DOUBT = '数学疑点'
DEFAULT_LIST = Path(__file__).resolve().parent / '语言问题清单.txt'
BULLET = r'[*\-+]'
LOCATION = re.compile(r'^' + BULLET + r'\s+\*\*(.+?)\*\*\s*$')
FIELD = re.compile(r'^' + BULLET + r'\s+(原句|问题)\s*(\d*)\s*[：:]\s*(.*)$')
SECTION = re.compile(r'^#{2,4}\s+(.+?)\s*$')
SNIPPET = re.compile(r'(?<!`)`(?!`)(.+?)(?<!`)`(?!`)', re.S)
MATH_ENVS = r'(?:equation|align|alignat|gather|multline|flalign|eqnarray|math|displaymath|split|cases)'
REF_COMMANDS = (r'(?:ref|eqref|pageref|autoref|cref|Cref|crefrange|Crefrange|nameref|label|'
                r'cite|citet|citep|citeauthor|textcite|parencite)')
MATH = re.compile(
    r'\\begin\{(' + MATH_ENVS + r'\*?)\}.*?\\end\{\1\}'
    r'|\$\$.+?\$\$|\$(?:\\.|[^$\\])+\$|\\\[.+?\\\]|\\\(.+?\\\)'
    r'|\\' + REF_COMMANDS + r'\*?(?:\[[^\]]*\])*\{[^}]*\}', re.S)
ITEM_REF = re.compile(r'\b(?:Theorem|Lemma|Proposition|Corollary|Definition|Example|Remark|Exercise|'
                      r'Conjecture|Claim|Fact|Notation|Algorithm|Section|Subsection|Chapter)\s+'
                      r'(\d+(?:\.\d+)+)')
RETRY_STATUS = (408, 409, 425, 429, 500, 502, 503, 504)


def log(text):
    print(text, file=sys.stderr, flush=True)


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


# ---------------------------------------------------------------- parsing

def parse_candidates(text):
    """Return (candidates, warnings). One candidate per 原句/问题 pair of a location.

    Lines that continue a 原句/问题 (wrapped text, a quote broken over lines) are appended to it;
    any other unrecognised nonblank line is reported, never silently dropped.
    """
    out, warnings = [], []
    section, location, location_line, fields, last = '', None, 0, {}, None
    auto = [0]                     # > 0 while unnumbered pairs of one location are being auto-numbered

    def flush():
        for number, item in fields.items():
            label = location + (' · 第 %s 处' % number if number else '')
            if '原句' not in item or '问题' not in item:
                missing = '问题' if '原句' in item else '原句'
                warnings.append('第 %d 行起的「%s」缺少%s，已跳过' % (location_line, label, missing))
                continue
            original, problem = item['原句'].strip(), item['问题'].strip()
            ident = sha('\0'.join((section, location, number, original, problem)))[:16]
            out.append({'id': ident, 'section': section, 'location': label, 'original': original,
                        'problem': problem,
                        'snippets': [s.strip() for s in SNIPPET.findall(original) if s.strip()]})

    for number_line, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line == '---':
            continue
        m = SECTION.match(line)
        if m:
            if location: flush()
            section, location, fields, last = m.group(1), None, {}, None
            auto[0] = 0
            continue
        m = LOCATION.match(line)
        if m:
            if location: flush()
            location, location_line, fields, last = m.group(1), number_line, {}, None
            auto[0] = 0
            continue
        m = FIELD.match(line)
        if m and location:
            kind, number, body = m.group(1), m.group(2) or '', m.group(3).strip()
            if not number:
                if auto[0]:
                    if kind == '原句' and {'原句', '问题'} <= set(fields.get(str(auto[0]), {})):
                        auto[0] += 1
                    number = str(auto[0])
                elif kind == '原句' and {'原句', '问题'} <= set(fields.get('', {})):
                    # a second unnumbered 原句/问题 pair under one location: number both (第 1 处, 第 2 处, ...)
                    fields['1'] = fields.pop('')
                    auto[0], number = 2, '2'
            item = fields.setdefault(number, {})
            if kind in item:
                warnings.append('第 %d 行：「%s」的%s %s 重复出现，后一个覆盖前一个' % (number_line, location, kind, number))
            item[kind] = body
            last = (number, kind)
            continue
        if last is not None:                       # continuation of the previous field
            fields[last[0]][last[1]] += '\n' + line
            continue
        warnings.append('第 %d 行未识别，已忽略：%s' % (number_line, line[:80]))
    if location: flush()
    unique, seen = [], {}
    for c in out:
        if c['id'] in seen:
            warnings.append('「%s」与「%s」完全重复（同一节、位置、原句和问题），只处理一次'
                            % (c['location'], seen[c['id']]))
            continue
        seen[c['id']] = c['location']
        unique.append(c)
    return unique, warnings


# ---------------------------------------------------------------- nt.tex lookup

def _fragment_regex(fragment):
    """Match the fragment while ignoring all whitespace, so that line breaks and spacing in nt.tex
    (`=\\prod` vs `= \\prod`, `\\sqrt` + newline + `{d}`) do not matter."""
    chars = [re.escape(ch) for ch in fragment if not ch.isspace()]
    return re.compile(r'\s*'.join(chars)) if chars else None


def _fragments(snippet):
    pieces = re.split(r'\.\.\.|…|\\ldots|\\cdots', snippet)
    return sorted((p.strip(' ,;') for p in pieces if len(p.strip()) >= 12), key=len, reverse=True)


def anchors(tex, location):
    """Positions of \\label{<prefix>:x.y.z} for the items named in a location (any label prefix)."""
    out = []
    for number in ITEM_REF.findall(location or ''):
        for m in re.finditer(r'\\label\{[A-Za-z]+:' + re.escape(number) + r'\}', tex):
            out.append(m.start())
    return out


def _environment_spans(tex):
    """(start, end) spans of properly nested LaTeX environments."""
    stack, spans = [], []
    for match in re.finditer(r'\\(begin|end)\{([^{}]+)\}', tex):
        kind, name = match.group(1), match.group(2)
        if kind == 'begin':
            stack.append((name, match.start()))
        elif stack and stack[-1][0] == name:
            start = stack.pop()[1]
            spans.append((start, match.end()))
    return spans


def _location_hits(tex, hits, location):
    """Restrict hits to named statements and their proofs, never a neighbouring statement."""
    marks = anchors(tex, location)
    if not marks:
        return hits, []
    spans = _environment_spans(tex)
    statement_starts = sorted(
        start for start, _ in spans
        if re.match(r'\\begin\{(?:theorem|definition)\}', tex[start:start + 40]))
    proof_scopes = []
    if 'proof' in (location or '').lower():
        for start, end in spans:
            opening = re.match(r'\\begin\{(?:proof|altproof)\}(?:\[[^\]]*\])?', tex[start:end])
            if opening:
                proof_scopes.append((start, end, opening.group(0)))
    scopes = []
    for mark in marks:
        containing = [(start, end) for start, end in spans if start <= mark < end]
        if containing:
            start, _ = min(containing, key=lambda span: span[1] - span[0])
            # Doc attaches following proofs to the preceding statement. End at the next
            # theorem/definition so a missing quote can never select the next statement.
            later = [position for position in statement_starts if position > start]
            scopes.append((start, min(later) if later else len(tex)))
        label = re.match(r'\\label\{([^}]+)\}', tex[mark:])
        if label:
            reference = r'\ref{%s}' % label.group(1)
            # Alternative proofs can occur in later sections. Their explicit title reference
            # is a safe location anchor; an unrelated nearby statement is not.
            scopes.extend((start, end) for start, end, opening in proof_scopes if reference in opening)
    hits = [hit for hit in hits
            if any(start <= hit.start() and hit.end() <= end for start, end in scopes)]
    return hits, marks


def _closest(hits, marks):
    return min(hits, key=lambda h: min((h.start() < a, abs(h.start() - a)) for a in marks))


def locate(tex, snippet, location=''):
    """(start, end, hits) of the longest findable fragment of a snippet, or None.
    A theorem/definition named in the location restricts the search to that statement and its proofs."""
    for fragment in _fragments(snippet) or [snippet]:
        rx = _fragment_regex(fragment)
        if rx is None:
            continue
        hits = list(rx.finditer(tex))
        if hits:
            hits, marks = _location_hits(tex, hits, location)
        if hits:
            best = hits[0]
            if len(hits) > 1 and marks:
                best = _closest(hits, marks)
            return best.start(), best.end(), len(hits)
    return None


def context_spans(tex, candidate, limit=1800):
    """Merged (start, end) spans of nt.tex around the candidate's snippets, plus line info."""
    spans, lines = [], []
    for snippet in candidate['snippets'] or [candidate['original']]:
        found = locate(tex, snippet, candidate['location'])
        if not found:
            continue
        start, end, hits = found
        para_start = tex.rfind('\n\n', 0, start)
        para_end = tex.find('\n\n', end)
        para_start = 0 if para_start < 0 else para_start + 2
        para_end = len(tex) if para_end < 0 else para_end
        if para_end - para_start > limit:          # long paragraph: centre a window on the hit
            half = max(0, (limit - (end - start)) // 2)
            para_start, para_end = max(0, start - half), min(len(tex), end + half)
        spans.append((para_start, para_end))
        lines.append({'line': tex.count('\n', 0, start) + 1, 'matches': hits})
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return merged, lines


def context_for(tex, candidate, limit=1800):
    """Paragraph(s) of nt.tex around the snippets, plus line numbers, or ('', [])."""
    merged, lines = context_spans(tex, candidate, limit)
    if not merged:
        return '', []
    text = '\n[...]\n'.join(tex[s:e].strip() for s, e in merged)
    return text[: limit * 3], lines


def presence(tex, candidate, pre_tex=''):
    """Where the candidate's quoted text stands in the current nt.tex:
    'found' (every quote found), 'partial' (some), 'gone' (none; rewritten by the audit when it is
    still in the pre-audit copy), 'unmatched' (none, and not in the pre-audit copy either)."""
    snippets = candidate['snippets'] or [candidate['original']]
    hits = [bool(locate(tex, snippet, candidate['location'])) for snippet in snippets]
    if all(hits):
        return 'found'
    if any(hits):
        return 'partial'
    if pre_tex and not all(locate(pre_tex, snippet, candidate['location']) for snippet in snippets):
        return 'unmatched'
    return 'gone'


def find_all(haystack, needle):
    rx = _fragment_regex(needle)
    return list(rx.finditer(haystack)) if rx else []


def in_text(haystack, needle):
    rx = _fragment_regex(needle)
    return bool(rx and rx.search(haystack))


# ---------------------------------------------------------------- checks

def math_tokens(text):
    """Formulas and references in order, including significant whitespace."""
    return [m.group(0) for m in MATH.finditer(text)]


def syntax_tokens(text):
    """Keep command boundaries, grouping and comments stable across a replacement."""
    groups, comments, i = [], [], 0
    while i < len(text):
        ch = text[i]
        if ch == '\\' and i + 1 < len(text) and not text[i + 1].isalpha():
            i += 2
            continue
        if ch == '%':
            end = text.find('\n', i)
            end = len(text) if end < 0 else end
            comments.append(text[i:end])
            i = end
            continue
        if ch in '{}':
            groups.append(ch)
        i += 1
    return {'commands': re.findall(r'\\(?:[A-Za-z@]+\*?|[^A-Za-z@])', text),
            'groups': groups, 'comments': comments}


def invariants(tex):
    """LaTeX and mathematical invariants required of every published manuscript."""
    return dict(syntax_tokens(tex), **{
        'math': math_tokens(tex),
        'dollars': tex.count('$'),
        'labels': re.findall(r'\\label\{[^}]*\}', tex),
        'envs': re.findall(r'\\(?:begin|end)\{[^}]*\}', tex),
        'heads': re.findall(r'\\(?:section|subsection)\*?\{[^}]*\}', tex)})


def invariant_changes(before, after):
    return [key for key in before if before[key] != after[key]]


def logic_warning(old, new):
    """Flag changed logical qualifiers for human review; this is not a proof of equivalence."""
    terms = {
        'all', 'any', 'each', 'every', 'some', 'exists', 'exist', 'unique', 'uniquely',
        'not', 'no', 'nonzero', 'zero', 'positive', 'negative', 'nonnegative', 'nonpositive',
        'integer', 'integers', 'rational', 'irrational', 'real', 'complex', 'prime', 'composite',
        'distinct', 'only', 'iff', 'if', 'unless', 'when', 'whenever', 'provided', 'assuming',
        'assume', 'suppose', 'then', 'necessary', 'sufficient', 'respectively', 'both', 'either',
        'neither', 'least', 'most', 'exactly', 'finite', 'infinite', 'finitely', 'infinitely',
        'irreducible', 'reducible', 'coprime', 'divisible', 'invertible', 'injective', 'surjective',
    }
    def signature(text):
        words = re.findall(r'[A-Za-z]+', MATH.sub(' ', text).lower())
        return [word for word in words if word in terms]
    if signature(old) != signature(new):
        return '量词、条件或数学性质词发生变化，必须人工核对数学含义'
    return None


def math_warning(old, new, label):
    before, after = math_tokens(old), math_tokens(new)
    if before == after:
        return None
    if sorted(before) == sorted(after):
        return label + '公式/引用的先后顺序变了（可能交换了对象），务必核对数学含义'
    return label + '改动了公式或引用（$…$、数学环境、\\ref/\\cite 等），务必核对数学含义'


def check(result, candidate, context, tex):
    """Warnings (text) for the review; see check_codes for the machine-readable form."""
    return [message for _, message in check_codes(result, candidate, context, tex)]


def check_codes(result, candidate, context, tex):
    found = []
    add = lambda code, message: found.append((code, message))
    revisions = result.get('revisions') or []
    if result.get('verdict') == 'revise' and not revisions:
        add('empty_revise', 'verdict 为 revise 但没有给出修改')
    if result.get('verdict') == 'keep' and revisions:
        add('keep_with_revisions', 'verdict 为 keep 却给出了修改；仍列出供参考')
    if MATH_DOUBT in str(result.get('note_zh', '')):
        add('math_doubt', '模型提到数学疑点（文字未改），请对照数学审计结果核对')
    source_text = candidate['original'] + '\n' + context
    for i, rev in enumerate(revisions, 1):
        old, new = rev['original'], rev['revised']
        if not in_text(source_text, old):
            add('not_verbatim', '第 %d 条的 original 不是原文中的原样文字，需人工定位' % i)
        elif tex:
            hits = len(find_all(tex, old))
            if hits == 0:
                add('not_in_tex', '第 %d 条的 original 在 nt.tex 中找不到（可能取自清单里的旧引文）' % i)
            elif hits > 1 and anchors(tex, candidate['location']):
                add('multi_anchored', '第 %d 条的 original 在 nt.tex 中出现 %d 次；--apply 会改位置名所指标签后的那一处'
                    % (i, hits))
            elif hits > 1:
                add('ambiguous', '第 %d 条的 original 在 nt.tex 中出现 %d 次且位置名里没有可定位的标签；'
                    '--apply 会跳过，需要手工改' % (i, hits))
        warning = math_warning(old, new, '第 %d 条' % i)
        if warning:
            add('math_order' if '顺序' in warning else 'math_changed', warning)
        if old.strip() == new.strip():
            add('identical', '第 %d 条修改前后相同' % i)
    return found


# ---------------------------------------------------------------- model call

def build_messages(candidate, context):
    parts = ['Location: ' + candidate['location'],
             'Quoted text (from the candidate list, written before the math audit; '
             '"..." marks omitted parts):\n' + candidate['original'],
             'Suspected problem (Chinese, may be wrong):\n' + candidate['problem']]
    if context:
        parts.append('Current manuscript text around it (authoritative; take "original" from here):\n'
                     + context)
    else:
        parts.append('The quoted text was not found in the current manuscript; it may have been rewritten '
                     'during the math audit. Work on the quotation only.')
    parts.append('Return the JSON object now.')
    return [{'role': 'system', 'content': SYSTEM_PROMPT}, {'role': 'user', 'content': '\n\n'.join(parts)}]


def build_payload(args, model, messages):
    payload = {'model': model, 'messages': messages, 'max_tokens': args.max_tokens,
               'temperature': args.temperature, 'top_p': args.top_p, 'stream': False}
    if args.thinking != 'omit':
        payload['chat_template_kwargs'] = {'enable_thinking': args.thinking == 'on'}
    if args.top_k:
        payload['top_k'] = args.top_k
    if args.json_schema:
        payload['response_format'] = {'type': 'json_schema',
                                      'json_schema': {'name': 'polish_answer', 'schema': ANSWER_SCHEMA,
                                                      'strict': True}}
    return payload


def fingerprint(args, payload):
    """Everything that decides the answer: endpoint, model, sampling and the exact messages."""
    return sha(json.dumps({'base_url': args.base_url, 'payload': payload, 'prompt_version': VERSION},
                          ensure_ascii=False, sort_keys=True))


def http_json(url, payload, key, timeout):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    if key:
        headers['Authorization'] = 'Bearer ' + key
    req = urllib.request.Request(url, data=data, headers=headers, method='GET' if payload is None else 'POST')
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


def first_model(base, key, timeout):
    data = http_json(base + '/models', None, key, timeout)
    models = [m.get('id') for m in data.get('data', []) if m.get('id')]
    if not models:
        raise RuntimeError('/models returned no model; pass --model')
    return models[0]


def validate_answer(value):
    """Return the cleaned answer or raise ValueError naming what is wrong."""
    if not isinstance(value, dict):
        raise ValueError('the reply is not a JSON object')
    if value.get('verdict') not in ('revise', 'keep'):
        raise ValueError('"verdict" must be "revise" or "keep"')
    revisions = value.get('revisions', [])
    if not isinstance(revisions, list):
        raise ValueError('"revisions" must be a list')
    clean = []
    for i, rev in enumerate(revisions, 1):
        if not isinstance(rev, dict):
            raise ValueError('revision %d must be an object with "original" and "revised"' % i)
        old, new = rev.get('original'), rev.get('revised')
        if not isinstance(old, str) or not isinstance(new, str) or not old.strip() or not new.strip():
            raise ValueError('revision %d needs nonempty text in both "original" and "revised"' % i)
        clean.append({'original': old, 'revised': new})
    note = value.get('note_zh', '')
    if not isinstance(note, str):
        raise ValueError('"note_zh" must be text')
    return {'verdict': value['verdict'], 'revisions': clean, 'note_zh': note}


def parse_answer(text):
    text = text or ''
    if '</think>' in text:                         # thinking block, with or without the opening tag
        text = text.rsplit('</think>', 1)[1]
    text = text.strip()
    fence = re.fullmatch(r'```(?:json)?\s*(.*?)\s*```', text, re.S | re.I)
    if fence:
        text = fence.group(1)
    error = None
    try:
        return validate_answer(json.loads(text))
    except json.JSONDecodeError:
        error = 'no JSON object in the reply'
    except ValueError as exc:
        error = str(exc)
    # prose or LaTeX braces around the object: try every '{' and keep the last valid object
    decoder, found = json.JSONDecoder(), None
    for start in (i for i, ch in enumerate(text) if ch == '{'):
        try:
            candidate, _ = decoder.raw_decode(text, start)
            found = validate_answer(candidate)
        except ValueError:
            continue
    if found is None:
        raise ValueError(error)
    return found


def ask(args, key, model, messages):
    payload = build_payload(args, model, messages)
    url = args.base_url + '/chat/completions'
    delay, last = float(os.environ.get('QWEN_POLISH_RETRY_DELAY', 5)), None
    started, format_retries = time.monotonic(), 0
    for attempt in range(1, args.max_retries + 2):
        try:
            raw = http_json(url, payload, key, args.timeout)
            if not isinstance(raw, dict):
                raise ValueError('backend response is not a JSON object')
            choices = raw.get('choices')
            if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
                raise ValueError('backend response has no valid choices[0]')
            choice = choices[0]
            message = choice.get('message')
            if not isinstance(message, dict):
                raise ValueError('backend response has no valid choices[0].message')
            text = message.get('content') or ''
            if not isinstance(text, str):
                raise ValueError('backend response message content is not text')
            if not text.strip() and choice.get('finish_reason') == 'length':
                return None, {'error': 'reply cut off before any answer (finish_reason=length); '
                                       'raise --max-tokens', 'finish_reason': 'length'}
            try:
                answer = parse_answer(text)
            except ValueError as exc:
                last = 'unusable reply: %s' % exc
                format_retries += 1
                if attempt <= args.max_retries:
                    payload = dict(payload, messages=messages + [
                        {'role': 'assistant', 'content': text[-4000:]},
                        {'role': 'user', 'content': 'That reply could not be used (%s). Reply again with only '
                                                    'the JSON object in the required format.' % exc}])
                    continue
                return None, {'error': last, 'raw_reply': text, 'finish_reason': choice.get('finish_reason'),
                              'attempts': attempt}
            return answer, {'attempts': attempt, 'format_retries': format_retries,
                            'seconds': round(time.monotonic() - started, 1), 'usage': raw.get('usage'),
                            'finish_reason': choice.get('finish_reason'), 'raw_reply': text,
                            'served_model': raw.get('model')}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode('utf-8', 'replace')[:500]
            last = 'HTTP %d: %s' % (exc.code, body)
            if exc.code not in RETRY_STATUS:
                break                              # bad request / auth: retrying will not help
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, KeyError, IndexError,
                TypeError, ValueError) as exc:
            last = '%s: %s' % (type(exc).__name__, exc)
        if attempt <= args.max_retries:
            log('    retry %d in %ds (%s)' % (attempt, delay, last[:120]))
            time.sleep(delay)
            delay = min(delay * 2, 60)             # covers a scaled-to-zero endpoint waking up
    return None, {'error': last, 'attempts': attempt}


# ---------------------------------------------------------------- results file

def load_done(path):
    """Latest row per candidate id. A torn LAST line (interrupted write) is backed up and cut off;
    a damaged line in the middle stops the program instead of guessing."""
    done = {}
    if not path.exists():
        return done
    data = path.read_bytes()
    lines = data.split(b'\n')
    good_bytes = 0
    for index, line in enumerate(lines):
        if not line.strip():
            good_bytes += len(line) + (1 if index < len(lines) - 1 else 0)
            continue
        try:
            row = json.loads(line.decode('utf-8'))
            if not isinstance(row, dict) or 'id' not in row:
                raise ValueError('not a result row')
        except (ValueError, UnicodeDecodeError):
            rest = [l for l in lines[index + 1:] if l.strip()]
            if rest:
                raise SystemExit('%s 第 %d 行损坏且后面还有记录；请手工修复（不会自动删除中间记录）。'
                                 % (path, index + 1))
            backup = path.with_name(path.name + '.torn-' + time.strftime('%Y%m%dT%H%M%S'))
            shutil.copy2(path, backup)
            with open(path, 'r+b') as handle:
                handle.truncate(good_bytes)
            log('results.jsonl 最后一行不完整（多半是写入时被中断）：已备份到 %s 并截掉该行。' % backup.name)
            break
        done[row['id']] = row
        good_bytes += len(line) + (1 if index < len(lines) - 1 else 0)
    return done


def compact(path, done):
    """Rewrite results.jsonl with only the latest row per id (atomic)."""
    temp = path.with_name(path.name + '.tmp')
    with open(temp, 'w', encoding='utf-8') as handle:
        for row in done.values():
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


# ---------------------------------------------------------------- review.md

FENCE_OPEN = re.compile(r'^(~{3,})latex\s*$')
HEADING = re.compile(r'^#### 修改 (\d+) · `([0-9a-f]+#\d+)` · `([0-9a-f]+)`\s*$')
CHECKBOX = re.compile(r'^- \[( |x|X)\] 接受\s*$')


def _fence(text):
    longest = max([len(m) for m in re.findall(r'^~{3,}', text, re.M)] or [0])
    return '~' * max(3, longest + 1)


def revision_key(row, i):
    return '%s#%d' % (row['id'], i)


def revision_stamp(rev):
    return sha(rev['original'] + '\0' + rev['revised'])[:12]


def read_decisions(path):
    """{key: {'stamp', 'accepted', 'revised'}} from an existing review.md (your ticks and edits)."""
    if not path.exists():
        return {}
    decisions, lines, i = {}, path.read_text(encoding='utf-8').splitlines(), 0
    while i < len(lines):
        m = HEADING.match(lines[i])
        if not m:
            i += 1
            continue
        key, stamp = m.group(2), m.group(3)
        accepted, blocks, j = False, [], i + 1
        while j < len(lines) and not lines[j].startswith('#'):
            box = CHECKBOX.match(lines[j])
            if box:
                accepted = box.group(1).lower() == 'x'
            fence = FENCE_OPEN.match(lines[j])
            if fence:
                close, body, j = fence.group(1), [], j + 1
                while j < len(lines) and lines[j] != close:
                    body.append(lines[j]); j += 1
                blocks.append('\n'.join(body))
            j += 1
        if len(blocks) == 2:
            decisions[key] = {'stamp': stamp, 'accepted': accepted, 'revised': blocks[1]}
        i = j
    return decisions


GONE_TEXT = {'gone': '原句已不在当前稿（多半被数学修复改写），未发送',
             'unmatched': '清单引文在当前稿和审计前原稿里都找不到，未发送；请核对清单'}


def write_review(path, candidates, done, model, parse_warnings, gone=None):
    gone = gone or {}
    previous = read_decisions(path)
    out = ['# 语言润色建议', '',
           '模型：`%s`。nt.tex 未被修改。在要采用的修改下把 `- [ ]` 改成 `- [x]`；可以直接改“改为”框里的文字。'
           '改完运行 `python3 qwen_polish.py --apply --tex nt.tex --out %s`。重跑提问步骤会保留你的勾选和改动。'
           % (model, path.parent), '']
    counts = {'revise': 0, 'keep': 0, 'error': 0, 'pending': 0, 'gone': 0}
    reset, doubts = 0, []
    body, section = [], None
    for c in candidates:
        row = done.get(c['id'])
        if c['section'] != section:
            section = c['section']
            body += ['', '## ' + section, '']
        if c['id'] in gone and (row is None or row.get('error')):
            counts['gone'] += 1
            body += ['### %s（跳过）' % c['location'], '', '- 问题：' + c['problem'], '- 原句：' + c['original'],
                     '- ' + GONE_TEXT[gone[c['id']]], '']
            continue
        status = 'pending' if row is None else ('error' if row.get('error') else row['answer']['verdict'])
        counts[status] += 1
        tag = {'revise': '建议修改', 'keep': '建议不改', 'error': '出错', 'pending': '未处理'}[status]
        body += ['### %s（%s）' % (c['location'], tag), '', '- 问题：' + c['problem']]
        if c['id'] in gone:
            body.append('- ⚠️ 这条回答针对旧稿；' + GONE_TEXT[gone[c['id']]].split('，')[0])
        if row and row.get('tex_lines'):
            body.append('- nt.tex 位置：' + '，'.join('第 %d 行%s' % (l['line'], '（%d 处匹配）' % l['matches']
                                                        if l['matches'] > 1 else '') for l in row['tex_lines']))
        if row and row.get('model'):
            body.append('- 回答来自：`%s`%s' % (row['model'], '（与本次模型不同）' if row['model'] != model else ''))
        if row is None or row.get('error'):
            body += ['- 原句：' + c['original']] + (['- 错误：' + row['error']] if row else []) + ['']
            continue
        answer = row['answer']
        if answer.get('note_zh'):
            body.append('- 模型说明：' + str(answer['note_zh']))
            if MATH_DOUBT in answer['note_zh']:
                doubts.append((c['location'], answer['note_zh']))
        for w in row.get('warnings', []):
            body.append('- ⚠️ ' + w)
        for i, rev in enumerate(answer.get('revisions') or [], 1):
            key, stamp = revision_key(row, i), revision_stamp(rev)
            mine = previous.get(key)
            if mine and mine['stamp'] != stamp:
                reset += 1
                mine = None
            accepted = bool(mine and mine['accepted'])
            revised = mine['revised'] if mine else rev['revised']
            fence = _fence(rev['original'] + '\n' + revised)
            body += ['', '#### 修改 %d · `%s` · `%s`' % (i, key, stamp), '',
                     '- [%s] 接受' % ('x' if accepted else ' '), '', '原文：', fence + 'latex',
                     rev['original'], fence, '改为（可直接编辑）：', fence + 'latex', revised, fence]
        if not answer.get('revisions'):
            body += ['- 原句：' + c['original']]
        body.append('')
    head = '共 %d 条：建议修改 %d，建议不改 %d，出错 %d，未处理 %d，原句已不在当前稿 %d。' % (
        len(candidates), counts['revise'], counts['keep'], counts['error'], counts['pending'], counts['gone'])
    out.insert(3, head)
    if reset:
        out += ['> %d 处修改的模型回答已更新，原来的勾选和改动不再适用，已重置。' % reset, '']
    if parse_warnings:
        out += ['## 清单解析警告', ''] + ['- ' + w for w in parse_warnings] + ['']
    if doubts:
        out += ['## 模型提到的数学疑点（文字未改；请对照数学审计结果核对）', '']
        out += ['- **%s**：%s' % (loc, note) for loc, note in doubts] + ['']
    temp = path.with_name(path.name + '.tmp')
    temp.write_text('\n'.join(out + body) + '\n', encoding='utf-8')
    os.replace(temp, path)
    return head


# ---------------------------------------------------------------- apply

def apply_changes(tex_path, out_dir):
    tex = tex_path.read_text(encoding='utf-8')
    done = load_done(out_dir / 'results.jsonl')
    decisions = read_decisions(out_dir / 'review.md')
    rows = {row['id']: row for row in done.values() if row.get('answer')}
    inv_old = invariants(tex)
    planned, skipped = [], []
    for key, decision in decisions.items():
        if not decision['accepted']:
            continue
        ident, number = key.rsplit('#', 1)
        row = rows.get(ident)
        revisions = (row or {}).get('answer', {}).get('revisions') or []
        if row is None or not 1 <= int(number) <= len(revisions):
            skipped.append((key, '?', 'results.jsonl 里没有这条回答；先重跑提问步骤'))
            continue
        rev = revisions[int(number) - 1]
        if revision_stamp(rev) != decision['stamp']:
            skipped.append((key, row['location'], '模型回答已变，勾选不适用；请在新 review.md 里重新勾选'))
            continue
        # Applying a revision is deliberately stricter than locating a candidate: no whitespace folding.
        hits = list(re.finditer(re.escape(rev['original']), tex)) if rev['original'] else []
        marks = []
        if hits:
            hits, marks = _location_hits(tex, hits, row['location'])
        if len(hits) > 1 and marks:
            # Only occurrences inside the named item's own environment are eligible.
            hits = [_closest(hits, marks)]
        if not hits:
            skipped.append((key, row['location'], '原文在 nt.tex 中找不到（精确匹配，且限定在位置名所指环境）'))
            continue
        if len(hits) > 1:
            lines = '、'.join(str(tex.count('\n', 0, h.start()) + 1) for h in hits[:6])
            skipped.append((key, row['location'], '原文在 nt.tex 中出现 %d 次（第 %s 行），无法确定改哪一处'
                            % (len(hits), lines)))
            continue
        hit = hits[0]
        revised = decision['revised']
        composed = tex[:hit.start()] + revised + tex[hit.end():]
        broken = invariant_changes(inv_old, invariants(composed))
        if broken:
            skipped.append((key, row['location'], '最终替换未通过严格 LaTeX 检查：' + '、'.join(broken)))
            continue
        warning = math_warning(rev['original'], revised, '')
        planned.append({'key': key, 'location': row['location'], 'start': hit.start(), 'end': hit.end(),
                        'revised': revised, 'warning': warning,
                        'edited': revised != rev['revised']})
    planned.sort(key=lambda p: p['start'])
    applied, last_end = [], -1
    for p in planned:
        if p['start'] < last_end:
            skipped.append((p['key'], p['location'], '与前一处已应用的修改重叠'))
            continue
        applied.append(p)
        last_end = p['end']
    new = tex
    for p in reversed(applied):
        new = new[:p['start']] + p['revised'] + new[p['end']:]
    broken = invariant_changes(inv_old, invariants(new))
    failed = bool(broken)
    polished = out_dir / (tex_path.stem + '.polished' + tex_path.suffix)
    candidate = (out_dir / (tex_path.stem + '.failed' + tex_path.suffix)) if failed else polished
    candidate_tmp = candidate.with_name(candidate.name + '.tmp')
    candidate_tmp.write_text(new, encoding='utf-8')
    os.replace(candidate_tmp, candidate)
    diff = difflib.unified_diff(tex.splitlines(keepends=True), new.splitlines(keepends=True),
                                fromfile=tex_path.name, tofile=candidate.name, n=2)
    (out_dir / 'polish.diff').write_text(''.join(diff), encoding='utf-8')
    report = ['# 应用润色', '', '原稿：`%s`（未修改，SHA-256 `%s`）' % (tex_path, sha(tex)[:16]),
              ('失败候选稿' if failed else '新稿') + '：`%s`' % candidate,
              'diff：`%s`' % (out_dir / 'polish.diff'), '',
              '已应用 %d 处，跳过 %d 处。' % (len(applied), len(skipped)),
              '全文不变量（公式与引用、命令边界、花括号、注释、标签、环境、章节标题）：'
              + ('全部一致' if not broken else '❌ 变了：' + '、'.join(broken))]
    if failed:
        report.append('验证失败，未更新正式的 .polished.tex 文件；失败候选稿仅供排查。')
    report.append('')
    if applied:
        report += ['## 已应用', '']
        for p in applied:
            note = []
            if p['edited']: note.append('用了你改过的文字')
            if p['warning']: note.append('⚠️ ' + p['warning'])
            report.append('- 第 %d 行 · %s · `%s`%s' % (tex.count('\n', 0, p['start']) + 1, p['location'], p['key'],
                                                    ('：' + '；'.join(note)) if note else ''))
        report.append('')
    if skipped:
        report += ['## 跳过（未改动）', ''] + ['- %s · `%s`：%s' % (loc, key, why) for key, loc, why in skipped] + ['']
    (out_dir / 'apply-report.md').write_text('\n'.join(report), encoding='utf-8')
    print('已应用 %d 处，跳过 %d 处 → %s\n报告：%s' % (len(applied), len(skipped), candidate,
                                                  out_dir / 'apply-report.md'))
    if failed:
        return 4
    return 0 if not skipped else 3



# ---------------------------------------------------------------- quality test of the fine-tune

def _similarity(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def _ratio(n, d):
    return None if not d else round(n / d, 3)


def _pct(value):
    return '—' if value is None else '%.1f%%' % (100 * value)


def run_metrics(out_dir, candidates=None, gone=None):
    """Automatic and human-review metrics of one run directory, as a dict."""
    done = load_done(out_dir / 'results.jsonl')
    decisions = read_decisions(out_dir / 'review.md')
    gone = gone or {}
    rows = list(done.values())
    answered = [r for r in rows if r.get('answer')]
    m = {'run': str(out_dir), 'models': sorted({r.get('served_model') or r.get('model') or '?' for r in answered}),
         'candidates': len(candidates) if candidates is not None else len(rows),
         'skipped_gone': sum(1 for i in gone if i not in done or not done[i].get('answer')),
         'asked': len(rows), 'answered': len(answered), 'errors': len(rows) - len(answered),
         'first_try_format_ok': sum(1 for r in answered if not r.get('format_retries')),
         'needed_format_retry': sum(1 for r in answered if r.get('format_retries')),
         'revise': sum(1 for r in answered if r['answer']['verdict'] == 'revise'),
         'keep': sum(1 for r in answered if r['answer']['verdict'] == 'keep'),
         'math_doubt_notes': sum(1 for r in answered if MATH_DOUBT in r['answer'].get('note_zh', ''))}
    codes = {}
    for r in answered:
        for code in r.get('warning_codes') or []:
            codes[code] = codes.get(code, 0) + 1
    m['warning_counts'] = codes
    revisions, kept_ratio, accepted, edited, final_ratio = 0, [], 0, 0, []
    for r in answered:
        for i, rev in enumerate(r['answer'].get('revisions') or [], 1):
            revisions += 1
            kept_ratio.append(_similarity(rev['original'], rev['revised']))
            mine = decisions.get(revision_key(r, i))
            if mine and mine['stamp'] == revision_stamp(rev) and mine['accepted']:
                accepted += 1
                if mine['revised'].strip() != rev['revised'].strip():
                    edited += 1
                    final_ratio.append(_similarity(rev['revised'], mine['revised']))
    m.update({'revisions': revisions, 'accepted': accepted, 'accepted_as_is': accepted - edited,
              'accepted_after_edit': edited, 'not_ticked': revisions - accepted,
              'mean_text_kept': round(sum(kept_ratio) / len(kept_ratio), 3) if kept_ratio else None,
              'heavy_rewrites': sum(1 for x in kept_ratio if x < 0.6),
              'mean_model_text_kept_in_your_edit': (round(sum(final_ratio) / len(final_ratio), 3)
                                                    if final_ratio else None)})
    seconds = [r['seconds'] for r in answered if isinstance(r.get('seconds'), (int, float))]
    out_tokens = [((r.get('usage') or {}).get('completion_tokens')) for r in answered]
    out_tokens = [t for t in out_tokens if isinstance(t, int)]
    m['mean_seconds'] = round(sum(seconds) / len(seconds), 1) if seconds else None
    m['mean_output_tokens'] = round(sum(out_tokens) / len(out_tokens)) if out_tokens else None
    return m


METRIC_ROWS = [
    ('回答成功', lambda m: '%d / %d' % (m['answered'], m['asked'])),
    ('第一次就是合格 JSON', lambda m: _pct(_ratio(m['first_try_format_ok'], m['answered']))),
    ('建议修改 / 建议不改', lambda m: '%d / %d' % (m['revise'], m['keep'])),
    ('修改条数', lambda m: str(m['revisions'])),
    ('改动了公式或引用 ⚠️', lambda m: str(m['warning_counts'].get('math_changed', 0)
                                     + m['warning_counts'].get('math_order', 0))),
    ('original 不是原样文字', lambda m: str(m['warning_counts'].get('not_verbatim', 0))),
    ('original 在 nt.tex 找不到', lambda m: str(m['warning_counts'].get('not_in_tex', 0))),
    ('original 多处匹配无法定位', lambda m: str(m['warning_counts'].get('ambiguous', 0))),
    ('修改前后相同 / revise 却没修改', lambda m: '%d / %d' % (m['warning_counts'].get('identical', 0),
                                                       m['warning_counts'].get('empty_revise', 0))),
    ('提到数学疑点', lambda m: str(m['math_doubt_notes'])),
    ('平均保留原文比例（越高改得越少）', lambda m: _pct(m['mean_text_kept'])),
    ('大改（保留 < 60%）', lambda m: str(m['heavy_rewrites'])),
    ('你接受的修改', lambda m: '%d（%s）' % (m['accepted'], _pct(_ratio(m['accepted'], m['revisions'])))),
    ('  其中原样接受 / 改过再接受', lambda m: '%d / %d' % (m['accepted_as_is'], m['accepted_after_edit'])),
    ('  改过的那些保留了模型文字', lambda m: _pct(m['mean_model_text_kept_in_your_edit'])),
    ('平均每条耗时（秒）', lambda m: '—' if m['mean_seconds'] is None else str(m['mean_seconds'])),
    ('平均输出 token', lambda m: '—' if m['mean_output_tokens'] is None else str(m['mean_output_tokens'])),
]


def quality_report(out_dir, candidates, tex, gone):
    if not (out_dir / 'results.jsonl').exists():
        log('%s 里没有 results.jsonl：先跑提问步骤。' % out_dir)
        return 2
    m = run_metrics(out_dir, candidates, gone)
    done = load_done(out_dir / 'results.jsonl')
    lines = ['# 微调质量报告', '', '运行目录：`%s`；模型：%s' % (out_dir, '、'.join('`%s`' % x for x in m['models']) or '—'),
             '清单 %d 条；原句已不在当前稿而跳过 %d 条；已问 %d 条。' % (m['candidates'], m['skipped_gone'], m['asked']), '',
             '| 指标 | 数值 |', '|---|---|'] + ['| %s | %s |' % (name, f(m)) for name, f in METRIC_ROWS]
    lines += ['', '读法：',
              '- “改动了公式或引用”应当是 0：提示词禁止改数学，每一条都要人工看。',
              '- “original 不是原样文字 / 找不到 / 无法定位”反映模型能否照抄原文，这些修改 --apply 用不上。',
              '- “你接受的修改”只统计 review.md 里打了 `[x]` 的；没打勾的可能是不采用，也可能还没看。',
              '  想看微调有没有比底模好，用 `--compare` 做盲评，比这里的绝对数字更可靠。', '']
    flagged = []
    for row in done.values():
        for code, message in zip(row.get('warning_codes') or [], row.get('warnings') or []):
            if code in ('math_changed', 'math_order'):
                flagged.append('- **%s**：%s' % (row['location'], message))
    if flagged:
        lines += ['## 改动了公式或引用的修改', ''] + flagged + ['']
    errors = ['- **%s**：%s' % (r['location'], str(r.get('error'))[:200]) for r in done.values() if r.get('error')]
    if errors:
        lines += ['## 出错', ''] + errors + ['']
    (out_dir / 'quality-report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (out_dir / 'quality.json').write_text(json.dumps(m, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('\n'.join(lines[:3]) + '\n→ ' + str(out_dir / 'quality-report.md'))
    return 0


CHOICES = ('甲更好', '乙更好', '差不多', '都不能用')
BLIND_HEADING = re.compile(r'^### (\d+) · .* · `([0-9a-f]{16})`\s*$')
CHOICE_LINE = re.compile(r'^- \[( |x|X)\] (' + '|'.join(CHOICES) + r')\s*$')


def _read_choices(path):
    """{candidate id: choice or 'invalid'} from an existing blind.md."""
    if not path.exists():
        return {}
    picks, current = {}, None
    for line in path.read_text(encoding='utf-8').splitlines():
        m = BLIND_HEADING.match(line)
        if m:
            current = m.group(2)
            continue
        box = CHOICE_LINE.match(line)
        if box and current and box.group(1).lower() == 'x':
            picks[current] = 'invalid' if current in picks else box.group(2)
    return picks


def _answer_block(answer, fence_source):
    tag = {'revise': '建议修改', 'keep': '建议不改'}[answer['verdict']]
    block = ['（%s）%s' % (tag, answer.get('note_zh', ''))]
    for i, rev in enumerate(answer.get('revisions') or [], 1):
        fence = _fence(fence_source + rev['original'] + rev['revised'])
        block += ['', '修改 %d 原文：' % i, fence + 'latex', rev['original'], fence,
                  '改为：', fence + 'latex', rev['revised'], fence]
    return block


def _same_answer(a, b):
    def norm(answer):
        return (answer['verdict'], [(re.sub(r'\s+', ' ', r['original']).strip(), re.sub(r'\s+', ' ', r['revised']).strip())
                                    for r in answer.get('revisions') or []])
    return norm(a) == norm(b)


def compare_runs(dir_a, dir_b):
    """Blind A/B review of two runs over the same list: blind.md to tick, result.md with the tally."""
    for d in (dir_a, dir_b):
        if not (d / 'results.jsonl').exists():
            log('%s 里没有 results.jsonl。' % d)
            return 2
    rows_a, rows_b = load_done(dir_a / 'results.jsonl'), load_done(dir_b / 'results.jsonl')
    dest = dir_a / ('compare-' + (dir_b.resolve().name or 'other'))
    dest.mkdir(parents=True, exist_ok=True)
    key_path = dest / 'key.json'
    key = json.loads(key_path.read_text(encoding='utf-8')) if key_path.exists() else {
        'a': str(dir_a), 'b': str(dir_b), 'salt': '%016x' % random.SystemRandom().getrandbits(64)}
    key_path.write_text(json.dumps(key, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    picks = _read_choices(dest / 'blind.md')
    both = [i for i in rows_a if rows_a[i].get('answer') and rows_b.get(i, {}).get('answer')]
    both.sort(key=lambda i: ((rows_a[i].get('tex_lines') or [{'line': 10 ** 9}])[0]['line'], rows_a[i]['location']))
    warnings = []
    if {rows_a[i].get('tex_sha256') for i in both} != {rows_b[i].get('tex_sha256') for i in both}:
        warnings.append('两次运行用的 nt.tex 不同，比较可能不公平。')
    blind = ['# 盲评：同一份清单的两组润色建议', '',
             '甲、乙随机对应两个模型（每条独立随机）。每条只勾一个：`- [x] 甲更好` / 乙更好 / 差不多 / 都不能用。'
             '勾完运行 `python3 qwen_polish.py --compare %s --out %s`，结果在 result.md。重跑会保留勾选。'
             % (dir_b, dir_a), ''] + ['> ' + w for w in warnings]
    tally = {'a': 0, 'b': 0, '差不多': 0, '都不能用': 0, 'identical': 0, 'undecided': 0, 'invalid': 0}
    reveal = []
    for n, ident in enumerate(both, 1):
        ra, rb = rows_a[ident], rows_b[ident]
        a_first = int(sha(key['salt'] + ident), 16) % 2 == 0
        first, second = (ra, rb) if a_first else (rb, ra)
        blind += ['', '### %d · %s · `%s`' % (n, ra['location'], ident), '', '- 问题：' + ra['problem'],
                  '- 清单原句：' + ra['original']]
        if _same_answer(ra['answer'], rb['answer']):
            tally['identical'] += 1
            blind += ['', '两边回答相同，不用选。']
            continue
        blind += ['', '**甲**'] + _answer_block(first['answer'], '') + ['', '**乙**'] + _answer_block(second['answer'], '')
        pick = picks.get(ident)
        blind += [''] + ['- [%s] %s' % ('x' if pick == choice else ' ', choice) for choice in CHOICES]
        if pick is None:
            tally['undecided'] += 1
        elif pick == 'invalid':
            tally['invalid'] += 1
        elif pick in ('甲更好', '乙更好'):
            winner = 'a' if (pick == '甲更好') == a_first else 'b'
            tally[winner] += 1
            reveal.append('- %s：%s 更好' % (ra['location'], dir_a if winner == 'a' else dir_b))
        else:
            tally[pick] += 1
    (dest / 'blind.md').write_text('\n'.join(blind) + '\n', encoding='utf-8')
    ma, mb = run_metrics(dir_a), run_metrics(dir_b)
    decided = tally['a'] + tally['b']
    result = ['# 盲评结果', '', 'A = `%s`（%s）' % (dir_a, '、'.join(ma['models'])),
              'B = `%s`（%s）' % (dir_b, '、'.join(mb['models'])), '',
              '两边都有回答的 %d 条：回答相同 %d，A 更好 %d，B 更好 %d，差不多 %d，都不能用 %d，未选 %d，多选无效 %d。'
              % (len(both), tally['identical'], tally['a'], tally['b'], tally['差不多'], tally['都不能用'],
                 tally['undecided'], tally['invalid']),
              ('分出胜负的 %d 条里 A 胜率 %s。' % (decided, _pct(_ratio(tally['a'], decided)))) if decided else '还没有分出胜负的条目。',
              '', '| 自动指标 | A | B |', '|---|---|---|'] + \
             ['| %s | %s | %s |' % (name, f(ma), f(mb)) for name, f in METRIC_ROWS]
    if decided and decided < 20:
        result += ['', '样本少于 20 条，胜率波动很大，只能当参考。']
    if reveal:
        result += ['', '## 逐条揭晓', ''] + reveal
    (dest / 'result.md').write_text('\n'.join(result) + '\n', encoding='utf-8')
    print('\n'.join(result[5:7]) + '\n→ %s\n→ %s' % (dest / 'blind.md', dest / 'result.md'))
    return 0


# ---------------------------------------------------------------- main

def main(argv=None):
    p = argparse.ArgumentParser(description='Language polish for the audited nt.tex with the 27B fine-tune '
                                            '(OpenAI-compatible API), --apply the ticked changes, and test '
                                            'the fine-tune with --report / --compare.')
    p.add_argument('candidates', type=Path, nargs='?', default=None,
                   help='candidate list (txt/md); default: the bundled %s' % DEFAULT_LIST.name)
    p.add_argument('--tex', type=Path, help='the CURRENT (post-audit) nt.tex: context, line numbers and which '
                                            'quotes are still there; required with --apply')
    p.add_argument('--pre-audit-tex', type=Path,
                   help='copy of nt.tex from before the math audit: tells "rewritten by the audit" apart from '
                        '"the list never matched"')
    p.add_argument('--include-gone', action='store_true',
                   help='also send candidates whose quote is no longer in --tex (the answer cannot be applied)')
    p.add_argument('--out', type=Path, default=Path('qwen-polish-out'), help='output directory (one per model)')
    p.add_argument('--apply', action='store_true', help='write OUT/<tex>.polished.tex from the ticks in review.md')
    p.add_argument('--report', action='store_true', help='write OUT/quality-report.md for the model of this run')
    p.add_argument('--compare', type=Path, metavar='OTHER_OUT',
                   help='blind A/B review of this run (--out) against another run directory')
    p.add_argument('--base-url', default=os.environ.get('QWEN_BASE_URL', 'http://127.0.0.1:8080/v1'))
    p.add_argument('--model', help='model id; default: first entry of GET /models')
    p.add_argument('--api-key-env', default='', help='env var holding the key (e.g. HF_TOKEN); empty = none')
    p.add_argument('--thinking', choices=('off', 'on', 'omit'), default='off',
                   help='Qwen thinking via chat_template_kwargs (omit = do not send the field)')
    p.add_argument('--max-tokens', type=int, default=None, help='default 2048, or 12288 with --thinking on')
    p.add_argument('--temperature', type=float, default=0.3, help='low keeps wording changes consistent')
    p.add_argument('--top-p', type=float, default=0.8)
    p.add_argument('--top-k', type=int, default=0, help='also send top_k (vLLM/MLX accept it); 0 = do not send')
    p.add_argument('--json-schema', action='store_true',
                   help='ask the server to enforce the answer format (vLLM supports it; mlx_lm.server does not)')
    p.add_argument('--concurrency', type=int, default=1,
                   help='requests in flight at once (vLLM/HF endpoints: 4–16; local MLX: 1)')
    p.add_argument('--timeout', type=float, default=600, help='seconds per request')
    p.add_argument('--max-retries', type=int, default=4)
    p.add_argument('--only', help='only locations containing this text, e.g. "Subsection 6.7"')
    p.add_argument('--limit', type=int, help='stop after this many new requests')
    p.add_argument('--redo', action='store_true', help='ignore earlier results and ask again')
    p.add_argument('--retry-errors', action='store_true', help='ask again only where the last attempt failed')
    p.add_argument('--dry-run', action='store_true', help='parse, show the first prompt, send nothing')
    args = p.parse_args(argv)

    if args.apply:
        if not args.tex:
            p.error('--apply needs --tex nt.tex')
        return apply_changes(args.tex, args.out)
    if args.compare:
        return compare_runs(args.out, args.compare)
    if args.candidates is None:
        if not DEFAULT_LIST.is_file():
            p.error('give the candidate list (the bundled %s is missing)' % DEFAULT_LIST.name)
        args.candidates = DEFAULT_LIST
    if not 1 <= args.concurrency <= 64:
        p.error('--concurrency must be between 1 and 64')
    args.base_url = args.base_url.rstrip('/')
    if args.max_tokens is None:
        args.max_tokens = 12288 if args.thinking == 'on' else 2048

    every, parse_warnings = parse_candidates(args.candidates.read_text(encoding='utf-8'))
    for w in parse_warnings:
        log('清单：' + w)
    candidates = [c for c in every if args.only in c['location']] if args.only else every
    if not candidates:
        log('No candidates parsed (expected lines "* **…**", "* 原句：…", "* 问题：…").')
        return 2
    tex = args.tex.read_text(encoding='utf-8') if args.tex else ''
    pre_tex = args.pre_audit_tex.read_text(encoding='utf-8') if args.pre_audit_tex else ''
    states = {c['id']: presence(tex, c, pre_tex) for c in every} if tex else {}
    gone = {i: state for i, state in states.items() if state in ('gone', 'unmatched')}
    if not tex:
        log('没有给 --tex：无法判断哪些原句已被数学修复改写，模型也看不到当前稿的上下文。强烈建议加上。')

    if args.report:
        return quality_report(args.out, every, tex, gone)

    if args.dry_run:
        print('%d candidates parsed, %d warnings' % (len(candidates), len(parse_warnings)))
        if tex:
            tally = {}
            for c in candidates:
                tally[states[c['id']]] = tally.get(states[c['id']], 0) + 1
            print('in %s: found %d, partly found %d, gone (rewritten by the audit) %d, never matched %d'
                  % (args.tex, tally.get('found', 0), tally.get('partial', 0), tally.get('gone', 0),
                     tally.get('unmatched', 0)))
            for c in candidates:
                if states[c['id']] != 'found':
                    print('  %-9s %s' % (states[c['id']], c['location']))
        first = next((c for c in candidates if c['id'] not in gone), candidates[0])
        context, _ = context_for(tex, first) if tex else ('', [])
        for m in build_messages(first, context):
            print('\n----- %s -----\n%s' % (m['role'], m['content']))
        return 0

    key = ''
    if args.api_key_env:
        key = os.environ.get(args.api_key_env, '')
        if not key:
            log(args.api_key_env + ' is empty')
            return 2
    model = args.model
    if not model:
        try:
            model = first_model(args.base_url, key, 60)
        except Exception as exc:
            log('Could not list models at %s/models (%s); pass --model.' % (args.base_url, exc))
            return 2
    args.out.mkdir(parents=True, exist_ok=True)
    results = args.out / 'results.jsonl'
    done = load_done(results)
    tex_hash = sha(tex) if tex else None

    jobs, stale, skipped_gone = [], 0, 0
    for n, c in enumerate(candidates, 1):
        if c['id'] in gone and not args.include_gone:
            skipped_gone += 1
            continue
        context, tex_lines = context_for(tex, c) if tex else ('', [])
        messages = build_messages(c, context)
        print_id = fingerprint(args, build_payload(args, model, messages))
        previous = None if args.redo else done.get(c['id'])
        if previous and previous.get('fingerprint') != print_id:
            stale += 1                     # question, context, model or settings changed: ask again
            previous = None
        if previous and not (args.retry_errors and previous.get('error')):
            continue
        jobs.append((n, c, context, tex_lines, messages, print_id))
    if args.limit is not None:
        jobs = jobs[:args.limit]
    print('model %s at %s; %d candidates, %d to ask (%d because the question, context, model or settings '
          'changed), %d skipped because the quote is no longer in nt.tex, %d in flight'
          % (model, args.base_url, len(candidates), len(jobs), stale, skipped_gone, args.concurrency))

    def finish(job, answer, meta):
        n, c, context, tex_lines, messages, print_id = job
        row = {'id': c['id'], 'location': c['location'], 'section': c['section'], 'problem': c['problem'],
               'original': c['original'], 'snippets': c['snippets'], 'tex_lines': tex_lines,
               'tex_sha256': tex_hash, 'model': model, 'fingerprint': print_id,
               'at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'tool_version': VERSION}
        row.update(meta)
        if answer is not None:
            row['answer'] = answer
            codes = check_codes(answer, c, context, tex)
            row['warnings'] = [message for _, message in codes]
            row['warning_codes'] = [code for code, _ in codes]
            print('[%d/%d] %s: %s%s' % (n, len(candidates), c['location'], answer['verdict'],
                                         ('  ⚠ ' + '; '.join(row['warnings'])) if row['warnings'] else ''))
        else:
            print('[%d/%d] %s: ERROR %s' % (n, len(candidates), c['location'], meta['error'][:200]))
        with open(results, 'a', encoding='utf-8') as handle:      # only the main thread writes
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')
            handle.flush()
        done[c['id']] = row

    pool = futures.ThreadPoolExecutor(max_workers=args.concurrency)
    request_failed, interrupted = False, False
    try:
        pending = {pool.submit(ask, args, key, model, job[4]): job for job in jobs}
        for future in futures.as_completed(pending):
            try:
                answer, meta = future.result()
            except Exception as exc:
                answer, meta = None, {'error': '%s: %s' % (type(exc).__name__, exc)}
            if answer is None:
                request_failed = True
            finish(pending[future], answer, meta)
    except KeyboardInterrupt:
        interrupted = True
        print('\nInterrupted; finished results are kept. Run the same command to continue.'
              + (' Waiting for requests already sent (Ctrl-C again to quit at once).' if args.concurrency > 1 else ''))
        pool.shutdown(wait=False, cancel_futures=True)
    else:
        pool.shutdown(wait=True)
    compact(results, done)
    head = write_review(args.out / 'review.md', every, done, model, parse_warnings, gone)   # the whole list
    print(head + '\n→ ' + str(args.out / 'review.md'))
    if interrupted:
        return 130
    return 3 if request_failed else 0


if __name__ == '__main__':
    sys.exit(main())
