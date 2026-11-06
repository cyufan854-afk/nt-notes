#!/usr/bin/env python3
"""nt27b: three batch jobs for the 27B fine-tune on nt.tex.

  polish  full-text English polish, block by block (math must stay byte-identical)
  triage  first-pass triage of the unreviewed DeepSeek findings (LOW explicitness / boundary items)
  refs    citation check: does each "by Theorem X" really support the sentence it is used in?

Workflow (details in README.md):
  prepare  build OUT/<task>/requests.jsonl from nt.tex (+ CSV, + pre-fix tex, + language list); send nothing
  estimate token counts and GPU time/cost of the prepared job
  ask      send requests to any OpenAI-compatible endpoint (mlx_lm.server on the Mac, vLLM on a rented GPU);
           resumable, format-checked, prints throughput and cost
  collect  validate answers, write OUT/<task>/review.md, summary.json, for-claude.md
  apply    polish only: apply ticked (or, with --accept-clean, all clean) revisions -> nt.polished.tex,
           with whole-document invariant checks and optional pdflatex

Standard library only; Python 3.9+. Uses the bundled qwen_polish.py for locating text and math checks.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
import concurrent.futures as futures
import csv
import difflib
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import qwen_polish as qp  # noqa: E402

VERSION = '1.1.1'   # unchanged: requests, answers and their validation are the same as 1.1.1; only file locations changed
# The common ancestor of branch1 and branch2 lives once, in the stage folder above this package (nt-final-stage/).
# Its content is fixed; prepare reads it from there and checks the hash instead of keeping a second copy.
BASELINE = HERE.parent / 'baseline.tex'
BASELINE_SHA256 = '8684a76e6014d66bd520f5b65f12acdb3e24157cfa5f0a227025963b6cb84dd5'
TASKS = ('polish', 'triage', 'refs')
CHARS_PER_TOKEN = 3.2          # LaTeX + English, Qwen tokenizer; used only for estimates


def log(text):
    print(text, file=sys.stderr, flush=True)


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with open(tmp, 'w', encoding='utf-8') as h:
        for r in rows:
            h.write(json.dumps(r, ensure_ascii=False) + '\n')
    os.replace(tmp, path)


def read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def request_hash(req):
    return qp.sha(json.dumps(req, ensure_ascii=False, sort_keys=True, separators=(',', ':')))


def snapshot_error(job, task, reqs):
    try:
        manifest = json.loads((job / 'manifest.json').read_text(encoding='utf-8'))
        expected = manifest['tex_sha256']
        task_hash = manifest['tasks'][task]['tex_sha256']
        shared = (job / 'nt.prepared.tex').read_text(encoding='utf-8')
        local = (job / task / 'nt.prepared.tex').read_text(encoding='utf-8')
        if qp.sha(shared) != expected or qp.sha(local) != task_hash or task_hash != expected:
            return '稿件快照与 manifest 不一致；请重新 prepare 到新目录。'
        if any(r.get('source_sha256') != task_hash for r in reqs):
            return '请求与稿件快照不一致，或任务来自旧版本；请重新 prepare 到新目录。'
    except (OSError, ValueError, KeyError, TypeError):
        return '缺少可验证的任务快照；请使用本版本重新 prepare 到新目录。'
    return None


def current_responses(job, task, reqs, done):
    """Only matching requests from the latest selected run can supply answers."""
    run_path = job / task / 'run.json'
    try:
        config = json.loads(run_path.read_text(encoding='utf-8'))
        run_args = argparse.Namespace(**config)
        model = config['model']
    except (OSError, ValueError, KeyError, TypeError):
        config = None
    checked, stale = {}, 0
    for req in reqs:
        row = done.get(req['id'])
        if not row:
            continue
        error = None
        if not config or row.get('request_hash') != request_hash(req):
            error = '回答属于旧请求或旧版本，需要重新 ask。'
        else:
            try:
                if row.get('fingerprint') != fingerprint(req, run_args, model):
                    error = '回答与当前模型运行配置不一致，需要重新 ask。'
            except (AttributeError, KeyError, TypeError, ValueError):
                error = '运行配置不完整，需要重新 ask。'
        if error:
            stale += 1
            checked[req['id']] = dict(row, answer=None, error=error, stale=True)
        elif row.get('answer'):
            try:
                answer = VALIDATORS[task](row['answer'])
                checked[req['id']] = dict(row, answer=answer)
            except ValueError as exc:
                checked[req['id']] = dict(row, answer=None, error='回答校验失败：' + str(exc))
        else:
            checked[req['id']] = row
    return checked, stale


def squash(text):
    return re.sub(r'\s+', ' ', text).strip()


def line_of(tex, pos):
    return tex.count('\n', 0, pos) + 1


# ======================================================================= document structure

ENV_RX = re.compile(r'\\begin\{(theorem|definition|proof|altproof)\}(.*?)\\end\{\1\}', re.S)
LABEL_RX = re.compile(r'\\label\{((?:thm|def|subsec):[^}]*)\}')
REF_RX = re.compile(r'\\(?:ref|eqref)\{((?:thm|def):[^}]*)\}')


class Doc:
    """Environments, labels and headings of nt.tex, with character offsets."""

    def __init__(self, tex):
        self.tex = tex
        self.body_start = tex.index('\\begin{document}') + len('\\begin{document}')
        end = tex.rfind('\\end{document}')
        self.body_end = end if end > 0 else len(tex)
        self.line_starts = [0] + [m.end() for m in re.finditer('\n', tex)]
        self.envs = []
        for m in ENV_RX.finditer(tex):
            label = LABEL_RX.search(m.group(2))
            self.envs.append({'kind': m.group(1), 'start': m.start(), 'end': m.end(),
                              'body_start': m.start(2), 'body_end': m.end(2),
                              'label': label.group(1) if label else None})
        self._env_starts = [e['start'] for e in self.envs]
        last_stmt = None
        for e in self.envs:                       # attach proofs to the statement right before them
            if e['kind'] in ('theorem', 'definition'):
                last_stmt = e
            else:
                e['of'] = last_stmt['label'] if last_stmt else None
        self.by_label = {e['label']: e for e in self.envs if e['label'] and e['kind'] in ('theorem', 'definition')}
        self.proofs_of = {}
        for e in self.envs:
            if e['kind'] in ('proof', 'altproof') and e.get('of'):
                self.proofs_of.setdefault(e['of'], []).append(e)
        self.heads = []
        for m in re.finditer(r'\\(section|subsection)\*?\{', tex):
            depth, i = 1, m.end()
            while i < len(tex) and depth:
                depth += {'{': 1, '}': -1}.get(tex[i], 0) if tex[i - 1] != '\\' else 0
                i += 1
            title = tex[m.end():i - 1]
            title = re.sub(r'\\texorpdfstring\{((?:[^{}]|\{[^{}]*\})*)\}\{(?:[^{}]|\{[^{}]*\})*\}', r'\1', title)
            self.heads.append((m.start(), m.group(1), squash(title)))
        self._head_starts = [h[0] for h in self.heads]
        self._head_contexts = []
        sec = sub = ''
        for _, kind, title in self.heads:
            if kind == 'section':
                sec, sub = title, ''
            else:
                sub = title
            self._head_contexts.append((sec, sub))
        conv = tex.find('\\section*{Notation and Conventions}')
        nxt = tex.find('\\section{', conv + 1) if conv >= 0 else -1
        self.conventions = tex[conv:nxt].strip() if conv >= 0 and nxt > 0 else ''

    def pos_of_line(self, line):
        line = max(1, min(line, len(self.line_starts)))
        return self.line_starts[line - 1]

    def line_of(self, pos):
        # Match str.count's end-offset semantics, including negative offsets.
        if pos < 0:
            pos = max(0, len(self.tex) + pos)
        return bisect_right(self.line_starts, pos)

    def env_at(self, pos):
        index = bisect_right(self._env_starts, pos) - 1
        if index >= 0 and pos < self.envs[index]['end']:
            return self.envs[index]
        return None

    def heading_at(self, pos):
        index = bisect_right(self._head_starts, pos) - 1
        return self._head_contexts[index] if index >= 0 else ('', '')

    def statement(self, label, cap=3000):
        e = self.by_label.get(label)
        if not e:
            return ''
        text = self.tex[e['start']:e['end']].strip()
        return text if len(text) <= cap else text[:cap] + '\n[... statement truncated ...]'

    def env_name(self, e):
        if e is None:
            return 'prose'
        if e['kind'] in ('theorem', 'definition'):
            return e['label'] or e['kind']
        return '%s of %s' % (e['kind'], e.get('of') or '?')


def window(tex, start, end, focus_start, focus_end, cap):
    """Text of [start, end), cut to at most cap characters centred on [focus_start, focus_end)."""
    if end - start <= cap:
        return tex[start:end]
    half = max(0, (cap - (focus_end - focus_start)) // 2)
    s = max(start, focus_start - half)
    e = min(end, s + cap)
    s = max(start, e - cap)
    return ('[...]\n' if s > start else '') + tex[s:e] + ('\n[...]' if e < end else '')


def math_mask(text):
    """Sorted list of (start, end) spans of formulas / refs in text."""
    return [(m.start(), m.end()) for m in qp.MATH.finditer(text)]


def inside(spans, pos):
    for s, e in spans:
        if s <= pos < e:
            return True
        if s > pos:
            return False
    return False


# ======================================================================= task: polish

POLISH_SYSTEM = r"""[task: polish]
You are a copy-editor for English mathematical writing in LaTeX (a rigorous number-theory textbook).
You receive ONE block of the manuscript, plus a little preceding text for flow (read-only).
The mathematics has been audited and is out of scope: never change it, even if it looks wrong. If you
see a possible mathematical problem, change nothing there and mention it in note_zh, starting with
"数学疑点：".

Fix only real English problems: grammar, articles, agreement, idiom, word order, run-on or telegraphic
sentences (e.g. a bare formula or an imperative squeezed into parentheses as a reason), unclear
antecedents, inconsistent tense, punctuation. Keep the register of a rigorous textbook. Do not restyle
sentences that are already acceptable, do not shorten proofs, do not merge or reorder arguments.

Hard rules (an edit that breaks one is thrown away automatically):
1. Every formula ($...$, \[...\], math environments) and every \ref, \label, \cite stays byte-identical
   and in the same order inside the edited text. Do not add, remove, split or join formulas.
2. Keep hypotheses, quantifiers, claims and their order. Do not add or remove mathematical content.
3. Keep valid LaTeX and the author's macros (\leg, \ZmodUnits, \id, ...). No Markdown.
4. "original" is copied VERBATIM from the Block (not from the preceding text): a whole sentence or
   clause, long enough to occur only once in the Block. "revised" is its full replacement.
5. At most 6 revisions per block; prefer fewer. If the block is fine, answer "keep" with no revisions.

Answer with ONE JSON object and nothing else:
{"verdict": "revise" or "keep",
 "revisions": [{"original": "...", "revised": "..."}],
 "note_zh": "一两句中文说明：改了什么、为什么；或为什么不改"}"""

PROSE_MIN_WORDS = 12


def prose_words(text):
    stripped = qp.MATH.sub(' ', text)
    stripped = re.sub(r'\\[A-Za-z@]+\*?(\[[^\]]*\])?', ' ', stripped)
    stripped = re.sub(r'%.*', ' ', stripped)
    return len(re.findall(r'[A-Za-z]{2,}', stripped))


def split_blocks(doc, keep=(), target=2400, hard=4200):
    """Blocks of the body: consecutive paragraphs, never crossing a (sub)section heading and always
    starting a new block at a theorem/definition (its proof may share the block), at most `target`
    characters unless one paragraph is longer; a paragraph longer than `hard` is cut at sentence ends
    outside math. Blocks with almost no prose are dropped unless they contain a position in `keep`."""
    tex = doc.tex
    cuts = {doc.body_start, doc.body_end}
    for p, _, _ in doc.heads:
        if doc.body_start < p < doc.body_end:
            cuts.add(p)
    for e in doc.envs:
        if e['kind'] in ('theorem', 'definition'):
            cuts.add(e['start'])
    cuts = sorted(c for c in cuts if doc.body_start <= c <= doc.body_end)
    blocks = []
    for a, b in zip(cuts, cuts[1:]):
        # paragraphs inside the region
        paras, s = [], a
        for m in re.finditer(r'\n[ \t]*\n', tex[a:b]):
            e = a + m.start()
            if tex[s:e].strip():
                paras.append((s, e))
            s = a + m.end()
        if tex[s:b].strip():
            paras.append((s, b))
        pieces = []
        for s, e in paras:
            if e - s <= hard:
                pieces.append((s, e))
                continue
            text = tex[s:e]
            mask = math_mask(text)
            ends = [m.end() for m in re.finditer(r'(?<=[.;])\s+', text) if not inside(mask, m.start())]
            cur = 0
            for x in ends:
                if x - cur >= target:
                    pieces.append((s + cur, s + x)); cur = x
            pieces.append((s + cur, e))
        cur = None
        for s, e in pieces:
            if cur and e - cur[0] <= target:
                cur = (cur[0], e)
            else:
                if cur:
                    blocks.append(cur)
                cur = (s, e)
        if cur:
            blocks.append(cur)
    out = []
    for s, e in blocks:
        # trim whitespace so offsets point at text
        while s < e and tex[s].isspace():
            s += 1
        while e > s and tex[e - 1].isspace():
            e -= 1
        if e > s and (prose_words(tex[s:e]) >= PROSE_MIN_WORDS or any(s <= k < e for k in keep)):
            out.append((s, e))
    return out


def prepare_polish(doc, list_path, outdir):
    tex = doc.tex
    cands = []
    if list_path and list_path.exists():
        cands, warns = qp.parse_candidates(list_path.read_text(encoding='utf-8'))
        for w in warns:
            log('清单：' + w)
    hints = {}
    for c in cands:
        for snip in c['snippets'] or [c['original']]:
            found = qp.locate(tex, snip, c['location'])
            if found:
                hints.setdefault(found[0], []).append(c)
                break
    rows = []
    blocks = split_blocks(doc, keep=list(hints))
    used_hints = set()
    for s, e in blocks:
        block = tex[s:e]
        env = doc.env_at(s)
        sec, sub = doc.heading_at(s)
        prev = tex[max(doc.body_start, s - 500):s].strip()
        my = []
        for p, cs in hints.items():
            if s <= p < e:
                for c in cs:
                    if c['id'] not in used_hints:
                        my.append(c); used_hints.add(c['id'])
        bid = qp.sha('%d:%d:%s' % (s, e, block))[:12]
        loc = '%s / %s / %s, lines %d–%d' % (sec, sub or '-', doc.env_name(env), doc.line_of(s), doc.line_of(e))
        parts = ['Location: ' + loc]
        if prev:
            parts.append('### Preceding text (read-only, for flow)\n' + prev[-500:])
        parts.append('### Block to edit\n' + block + '\n### End of block')
        if my:
            parts.append('A reviewer flagged these passages in this block (Chinese notes; the reviewer may be wrong, '
                         'and the quotes may be slightly out of date):\n' +
                         '\n'.join('- "%s" — %s' % (squash(c['original'])[:600], squash(c['problem'])[:400]) for c in my))
        parts.append('Return the JSON object now.')
        rows.append({'id': bid, 'task': 'polish', 'max_tokens': 1800, 'temperature': 0.3,
                     'messages': [{'role': 'system', 'content': POLISH_SYSTEM},
                                  {'role': 'user', 'content': '\n\n'.join(parts)}],
                     'meta': {'start': s, 'end': e, 'line': doc.line_of(s), 'location': loc,
                              'block': block, 'hints': [c['id'] for c in my]}})
    write_jsonl(outdir / 'polish' / 'requests.jsonl', rows)
    missing = [c['location'] for c in cands if c['id'] not in used_hints]
    return {'requests': len(rows), 'list_candidates': len(cands), 'list_hints_placed': len(used_hints),
            'list_hints_not_placed': missing}


# ======================================================================= task: triage

TRIAGE_SYSTEM_HEAD = r"""[task: triage]
You check findings reported by another model (DeepSeek) about a number-theory textbook written in
LaTeX. That model often saw only a fragment of the book, so many findings are false: the definition or
convention it missed is stated elsewhere. Your job is to sort ONE finding.

Verdicts:
- "resolved": the material given to you (the book's conventions below, the context, the cited
  statements) already settles the point. Put in "evidence" a VERBATIM quotation (one sentence or
  clause, copied exactly) from that material that settles it.
- "obvious": the text is literally silent, but any careful reader fills it in at once from the
  surrounding text or standard conventions (e.g. a variable is clearly an integer); no change needed.
- "real_gap": a careful reader could be misled or a step needs a fact that is nowhere stated; a short
  addition to the text would help. Give a minimal patch: "patch_original" copied VERBATIM from the
  context (a clause or sentence), "patch_revised" = the same text with the smallest addition. Keep every
  existing formula unchanged; you may add a short formula or clause.
- "cannot_decide": you would need material that is not given (say which in note_zh).
Be strict with "real_gap": use it only when you can name exactly what is missing.

Answer with ONE JSON object and nothing else:
{"verdict": "resolved" | "obvious" | "real_gap" | "cannot_decide",
 "evidence": "verbatim quotation, or empty",
 "patch_original": "verbatim text from the context, or empty",
 "patch_revised": "replacement, or empty",
 "note_zh": "一两句中文：判断理由"}

The book's global notation and conventions (authoritative, applies everywhere):
"""


def line_map(old_lines, new_lines):
    """old line number (1-based) -> new line number, via difflib; unmatched lines map to the nearest."""
    sm = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    mp = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        for k in range(i2 - i1):
            if tag == 'equal':
                mp[i1 + k + 1] = j1 + k + 1
            else:
                mp[i1 + k + 1] = min(j1 + k, j2 - 1) + 1 if j2 > j1 else j1 + 1
    return mp


def context_for_span(doc, s_pos, e_pos, cap_stmt=2500, cap_proof=4500, cap_prose=3500):
    tex = doc.tex
    env = doc.env_at(s_pos)
    parts, name = [], doc.env_name(env)
    if env is None:
        a = tex.rfind('\n\n', doc.body_start, max(doc.body_start, s_pos - 1500))
        b = tex.find('\n\n', min(len(tex), e_pos + 1500))
        a = doc.body_start if a < 0 else a
        b = doc.body_end if b < 0 else b
        parts.append(window(tex, a, b, s_pos, e_pos, cap_prose))
    elif env['kind'] in ('proof', 'altproof'):
        if env.get('of'):
            parts.append(doc.statement(env['of'], cap_stmt))
        parts.append(window(tex, env['start'], env['end'], s_pos, e_pos, cap_proof))
    else:
        parts.append(window(tex, env['start'], env['end'], s_pos, e_pos, cap_stmt + 1500))
        if env['kind'] == 'theorem':
            for pr in doc.proofs_of.get(env['label'], [])[:1]:
                parts.append(window(tex, pr['start'], pr['end'], pr['start'], pr['start'] + 10, 2500))
    return name, '\n\n'.join(p.strip() for p in parts if p.strip())


def cited_statements(doc, text, exclude=(), limit=5, cap=1200):
    out, seen = [], set(exclude)
    for lab in re.findall(r'proof of (?:Theorem|Lemma|Proposition)~?\\ref\{((?:thm|def):[^}]*)\}', text):
        for pr in doc.proofs_of.get(lab, [])[:1]:
            out.append('(%s, whose proof is cited)\n' % lab + doc.statement(lab, cap) + '\n' +
                       window(doc.tex, pr['start'], pr['end'], pr['start'], pr['start'] + 10, 2500))
            seen.add(lab)
    for lab in REF_RX.findall(text):
        if lab in seen or lab not in doc.by_label:
            continue
        seen.add(lab)
        out.append(doc.statement(lab, cap))
        if len(out) >= limit:
            break
    return out


def locate_triage(doc, quote, unit, mapped_start, mapped_end):
    """Search the named unit, using mapped lines rather than a first-hit guess."""
    label = re.search(r'(?:thm|def):[\w.:-]+', unit)
    label = label.group(0) if label else None
    statement = doc.by_label.get(label)
    regions = []
    if statement:
        regions = [statement] + doc.proofs_of.get(label, [])
        if unit.lower().startswith(('proof', 'altproof')):
            regions = doc.proofs_of.get(label, []) or [statement]
    else:
        env = doc.env_at(mapped_start)
        if env:
            regions = [env]
    if not regions:
        regions = [{'start': max(doc.body_start, mapped_start - 1500),
                    'end': min(doc.body_end, mapped_end + 1500)}]
    hits = []
    if len(quote) >= 12:
        for region in regions:
            hit = qp.locate(doc.tex[region['start']:region['end']], quote)
            if hit:
                hits.append((region['start'] + hit[0], region['start'] + hit[1], hit[2]))
    if sum(hit[2] for hit in hits) == 1:
        return hits[0][0], hits[0][1], 'found'
    region = next((r for r in regions if r['start'] <= mapped_start < r['end']), regions[0])
    start = min(max(mapped_start, region['start']), region['end'] - 1)
    end = min(max(start + 1, mapped_end), region['end'])
    return start, end, ('ambiguous' if hits else 'short' if len(quote) < 12 else 'not_found')


def prepare_triage(doc, csv_path, pre_tex_path, outdir, include_substantive=False, include_gone=False):
    tex = doc.tex
    with open(csv_path, encoding='utf-8-sig', newline='') as handle:
        rows_csv = list(csv.DictReader(handle))
    wanted = {'待看:显式性/边界'} | ({'待看:可能实质'} if include_substantive else set())
    picked = [r for r in rows_csv if r['Claude分类'] in wanted and not r['Claude核实'].strip()]
    old = pre_tex_path.read_text(encoding='utf-8')
    old_doc = Doc(old)
    mp = line_map(old.splitlines(), tex.splitlines())
    system = TRIAGE_SYSTEM_HEAD + doc.conventions
    rows, gone = [], []
    for r in picked:
        try:
            a, b = int(r['起行']), int(r['止行'] or r['起行'])
        except ValueError:
            a = b = 0
        quote = r['引文'].strip()
        if not a and not re.search(r'(?:thm|def):[\w.:-]+', r['单元']):
            continue
        mapped_start = doc.pos_of_line(mp.get(a, a))
        mapped_end = doc.pos_of_line(mp.get(b, b) + 1)
        s_pos, e_pos, quote_state = locate_triage(doc, quote, r['单元'], mapped_start, mapped_end)
        if quote_state == 'not_found' and not include_gone:
            _, _, old_state = locate_triage(old_doc, quote, r['单元'], old_doc.pos_of_line(a), old_doc.pos_of_line(b + 1))
            if old_state in ('found', 'ambiguous'):
                gone.append(r['序号'])
                continue
        name, ctx = context_for_span(doc, s_pos, e_pos)
        env = doc.env_at(s_pos)
        cited = cited_statements(doc, ctx, exclude=[env['label'] if env and env.get('label') else
                                                   (env.get('of') if env else None)])
        nl = doc.line_of(s_pos)
        parts = ['Unit: %s (current lines %d–%d)' % (name, nl, doc.line_of(e_pos)),
                 '### Context (current text of the book)\n' + ctx + '\n### End of context']
        if cited:
            parts.append('### Statements cited in the context\n' + '\n\n'.join(cited) + '\n### End of cited statements')
        parts.append('### Finding (task "%s", severity %s, type %s)\nQuoted text: %s\nReported issue: %s'
                     % (r['任务'], r['严重度'], r['类型'], quote or '(none)', squash(r['理由'])))
        if quote_state == 'not_found':
            parts.append('Note: the quoted text was not found verbatim in the current book; it may have been '
                         'reworded since the finding was made.')
        elif quote_state == 'ambiguous':
            parts.append('Note: the quotation has multiple matches inside the intended unit. The context '
                         'is anchored to mapped source lines. Do not assume any first match is the target; '
                         'use cannot_decide if the intended passage is still ambiguous.')
        parts.append('Return the JSON object now.')
        rid = qp.sha('triage:' + r['序号'])[:12]
        rows.append({'id': rid, 'task': 'triage', 'max_tokens': 900, 'temperature': 0.1,
                     'messages': [{'role': 'system', 'content': system},
                                  {'role': 'user', 'content': '\n\n'.join(parts)}],
                     'meta': {'no': r['序号'], 'unit': r['单元'], 'unit_now': name, 'line': nl,
                              'old_lines': '%s–%s' % (r['起行'], r['止行']), 'severity': r['严重度'],
                              'task_kind': r['任务'], 'type': r['类型'], 'class': r['Claude分类'],
                              'quote': quote, 'reason': r['理由'], 'quote_state': quote_state,
                              'material': ctx + '\n\n' + '\n\n'.join(cited)}})
    rows.sort(key=lambda x: (x['meta']['line'], x['meta']['no']))     # same unit together: prefix cache
    write_jsonl(outdir / 'triage' / 'requests.jsonl', rows)
    return {'requests': len(rows), 'csv_rows_selected': len(picked), 'skipped_quote_rewritten': len(gone),
            'skipped_numbers': gone, 'include_substantive': include_substantive}


# ======================================================================= task: refs

REFS_SYSTEM = r"""[task: refs]
You check citations in a number-theory textbook written in LaTeX. You receive ONE sentence that cites a
result ("by Theorem~\ref{...}", "(Definition~\ref{...})", ...), the statement being proved there, and the
full statement of the cited result. Decide whether the cited result really supports what the sentence
uses it for.

Verdicts:
- "supports": the cited statement gives exactly what is used, and its hypotheses are satisfied by what
  the text has already established (or are evidently satisfied).
- "hypotheses_unchecked": the cited result does give the fact, but at least one of its hypotheses is
  neither stated nor evident at this point. List each such hypothesis in "missing_hypotheses".
- "mismatch": the cited statement does not say what the sentence uses (wrong part, wrong direction,
  stronger claim than the citation gives), or the citation seems to point to the wrong result.
- "unclear": you cannot tell from the material given (say why in note_zh).
Be precise and conservative: "supports" is the normal case. Do not report style.

"cited_fact" must be a VERBATIM quotation (copied exactly) from the cited statement: the part that is
being used. Leave it empty only for "mismatch" when no part applies.

Answer with ONE JSON object and nothing else:
{"verdict": "supports" | "hypotheses_unchecked" | "mismatch" | "unclear",
 "cited_fact": "verbatim quotation from the cited statement",
 "missing_hypotheses": ["..."],
 "note_zh": "一两句中文：判断理由"}"""


def sentence_around(text, pos, end, cap=900):
    """The sentence(s) of text containing [pos, end), boundaries outside formulas."""
    mask = math_mask(text)
    starts = [0] + [m.end() for m in re.finditer(r'(?<=[.;:])\s+(?=[A-Z\\(])|\n[ \t]*\n', text)
                    if not inside(mask, m.start())]
    s = max([x for x in starts if x <= pos] or [0])
    later = [x for x in starts if x > end]
    e = min(later) if later else len(text)
    if e - s > cap:
        s = max(s, pos - cap // 2)
        e = min(e, s + cap)
    return text[s:e].strip()


def prepare_refs(doc, outdir):
    tex = doc.tex
    rows = []
    for m in REF_RX.finditer(tex, doc.body_start, doc.body_end):
        lab = m.group(1)
        if lab not in doc.by_label:
            continue
        env = doc.env_at(m.start())
        if env and env['kind'] in ('theorem', 'definition') and env['label'] == lab:
            continue
        if env and env['kind'] in ('proof', 'altproof') and env.get('of') == lab:
            continue                      # "[Alternative proof of Theorem X]", "part (a)" of the same result
        if env:
            region_s, region_e = env['body_start'], env['body_end']
        else:
            a = tex.rfind('\n\n', doc.body_start, m.start())
            b = tex.find('\n\n', m.end())
            region_s = doc.body_start if a < 0 else a
            region_e = doc.body_end if b < 0 else b
        region = tex[region_s:region_e]
        sent = sentence_around(region, m.start() - region_s, m.end() - region_s)
        # Identical citation sentences in different proofs still need separate checks:
        # their established hypotheses and statements being proved may differ.
        if env is None:
            where, proving = 'prose', ''
        elif env['kind'] in ('proof', 'altproof'):
            where, proving = doc.env_name(env), doc.statement(env.get('of') or '', 2500)
        else:
            where, proving = env['label'] or env['kind'], ''
        # a little text before the sentence, for what has been established so far
        before_start = max(region_s, region_s + region.find(sent[:60]) - 1200) if sent[:60] in region else region_s
        before = tex[before_start:region_s + max(0, region.find(sent[:60]))].strip()
        parts = ['Location: %s, line %d' % (where, doc.line_of(m.start()))]
        if proving:
            parts.append('### Statement being proved\n' + proving + '\n### End')
        if before:
            parts.append('### Text just before the sentence\n' + before[-1200:] + '\n### End')
        parts.append('### Sentence with the citation (\\ref{%s})\n%s\n### End' % (lab, sent))
        parts.append('### Cited statement (%s)\n%s\n### End' % (lab, doc.statement(lab, 3500)))
        parts.append('Return the JSON object now.')
        rid = qp.sha('refs:%d:%s' % (m.start(), lab))[:12]
        rows.append({'id': rid, 'task': 'refs', 'max_tokens': 800, 'temperature': 0.1,
                     'messages': [{'role': 'system', 'content': REFS_SYSTEM},
                                  {'role': 'user', 'content': '\n\n'.join(parts)}],
                     'meta': {'label': lab, 'line': doc.line_of(m.start()), 'where': where,
                              'sentence': sent, 'target': doc.statement(lab, 3500)}})
    write_jsonl(outdir / 'refs' / 'requests.jsonl', rows)
    return {'requests': len(rows), 'ref_occurrences': len(REF_RX.findall(tex, doc.body_start, doc.body_end))}


# ======================================================================= answer formats

POLISH_SCHEMA = qp.ANSWER_SCHEMA
TRIAGE_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['verdict', 'evidence', 'patch_original', 'patch_revised', 'note_zh'],
    'properties': {'verdict': {'type': 'string', 'enum': ['resolved', 'obvious', 'real_gap', 'cannot_decide']},
                   'evidence': {'type': 'string'}, 'patch_original': {'type': 'string'},
                   'patch_revised': {'type': 'string'}, 'note_zh': {'type': 'string'}}}
REFS_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['verdict', 'cited_fact', 'missing_hypotheses', 'note_zh'],
    'properties': {'verdict': {'type': 'string', 'enum': ['supports', 'hypotheses_unchecked', 'mismatch', 'unclear']},
                   'cited_fact': {'type': 'string'},
                   'missing_hypotheses': {'type': 'array', 'items': {'type': 'string'}},
                   'note_zh': {'type': 'string'}}}
SCHEMAS = {'polish': POLISH_SCHEMA, 'triage': TRIAGE_SCHEMA, 'refs': REFS_SCHEMA}


def _need_str(v, k):
    if k not in v:
        raise ValueError('missing required field "%s"' % k)
    x = v[k]
    if not isinstance(x, str):
        raise ValueError('"%s" must be text' % k)
    return x


def validate_triage(v):
    if not isinstance(v, dict):
        raise ValueError('the reply is not a JSON object')
    if v.get('verdict') not in TRIAGE_SCHEMA['properties']['verdict']['enum']:
        raise ValueError('"verdict" must be one of resolved / obvious / real_gap / cannot_decide')
    result = {'verdict': v['verdict'], 'evidence': _need_str(v, 'evidence'),
            'patch_original': _need_str(v, 'patch_original'), 'patch_revised': _need_str(v, 'patch_revised'),
            'note_zh': _need_str(v, 'note_zh')}
    if set(v) != set(TRIAGE_SCHEMA['required']):
        raise ValueError('unexpected fields in triage reply')
    if result['verdict'] == 'resolved' and not result['evidence'].strip():
        raise ValueError('resolved requires nonempty evidence')
    if result['verdict'] == 'real_gap' and not (result['patch_original'].strip() and result['patch_revised'].strip()):
        raise ValueError('real_gap requires both patch_original and patch_revised')
    return result


def validate_refs(v):
    if not isinstance(v, dict):
        raise ValueError('the reply is not a JSON object')
    if v.get('verdict') not in REFS_SCHEMA['properties']['verdict']['enum']:
        raise ValueError('"verdict" must be one of supports / hypotheses_unchecked / mismatch / unclear')
    if set(v) != set(REFS_SCHEMA['required']):
        raise ValueError('missing or unexpected fields in refs reply')
    hyps = v['missing_hypotheses']
    if not isinstance(hyps, list) or not all(isinstance(h, str) for h in hyps):
        raise ValueError('"missing_hypotheses" must be a list of strings')
    result = {'verdict': v['verdict'], 'cited_fact': _need_str(v, 'cited_fact'), 'missing_hypotheses': hyps,
            'note_zh': _need_str(v, 'note_zh')}
    if result['verdict'] != 'mismatch' and not result['cited_fact'].strip():
        raise ValueError('this refs verdict requires nonempty cited_fact')
    if result['verdict'] == 'supports' and hyps:
        raise ValueError('supports cannot have missing_hypotheses')
    if result['verdict'] == 'hypotheses_unchecked' and not any(h.strip() for h in hyps):
        raise ValueError('hypotheses_unchecked requires a missing hypothesis')
    return result


def validate_polish(value):
    if not isinstance(value, dict) or set(value) != set(POLISH_SCHEMA['required']):
        raise ValueError('missing or unexpected fields in polish reply')
    answer = qp.validate_answer(value)
    revisions = answer['revisions']
    if len(revisions) > 6:
        raise ValueError('at most 6 revisions per block')
    if (answer['verdict'] == 'keep') != (not revisions):
        raise ValueError('keep requires no revisions; revise requires revisions')
    return answer


VALIDATORS = {'polish': validate_polish, 'triage': validate_triage, 'refs': validate_refs}


def parse_reply(text, validator):
    text = text or ''
    if '</think>' in text:
        text = text.rsplit('</think>', 1)[1]
    text = text.strip()
    fence = re.fullmatch(r'```(?:json)?\s*(.*?)\s*```', text, re.S | re.I)
    if fence:
        text = fence.group(1)
    try:
        return validator(json.loads(text))
    except json.JSONDecodeError:
        error = 'no JSON object in the reply'
    except ValueError as exc:
        error = str(exc)
    decoder, found = json.JSONDecoder(), None
    for start in (i for i, ch in enumerate(text) if ch == '{'):
        try:
            obj, _ = decoder.raw_decode(text, start)
            found = validator(obj)
        except ValueError:
            continue
    if found is None:
        raise ValueError(error)
    return found


# ======================================================================= ask

def payload_for(req, args, model, messages=None, max_tokens=None):
    p = {'model': model, 'messages': messages or req['messages'],
         'max_tokens': max_tokens or req['max_tokens'], 'temperature': req['temperature'],
         'top_p': args.top_p, 'stream': False}
    if args.thinking != 'omit':
        p['chat_template_kwargs'] = {'enable_thinking': args.thinking == 'on'}
        if args.thinking == 'on':
            p['max_tokens'] = max(p['max_tokens'], 8192)
    if args.json_schema:
        p['response_format'] = {'type': 'json_schema',
                                'json_schema': {'name': req['task'] + '_answer', 'schema': SCHEMAS[req['task']],
                                                'strict': True}}
    return p


def fingerprint(req, args, model):
    return qp.sha(json.dumps({'base_url': args.base_url, 'payload': payload_for(req, args, model),
                              'model_revision': getattr(args, 'model_revision', ''),
                              'request_hash': request_hash(req), 'v': VERSION},
                             ensure_ascii=False, sort_keys=True))


def ask_one(req, args, key, model):
    validator = VALIDATORS[req['task']]
    url = args.base_url + '/chat/completions'
    messages, max_tokens = req['messages'], req['max_tokens']
    payload = payload_for(req, args, model)
    delay, last, fmt_retries, started = 5.0, None, 0, time.monotonic()
    usage_in = usage_out = 0
    for attempt in range(1, args.max_retries + 2):
        try:
            raw = qp.http_json(url, payload, key, args.timeout)
            if not isinstance(raw, dict):
                raise ValueError('backend response is not a JSON object')
            u = raw.get('usage') or {}
            if not isinstance(u, dict):
                raise ValueError('backend response field "usage" is not an object')
            usage_in += int(u.get('prompt_tokens') or 0)
            usage_out += int(u.get('completion_tokens') or 0)
            choices = raw.get('choices')
            if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
                raise ValueError('backend response has no valid choices[0] object')
            choice = choices[0]
            message = choice.get('message')
            if not isinstance(message, dict):
                raise ValueError('backend response has no valid choices[0].message object')
            content = message.get('content')
            if content is not None and not isinstance(content, str):
                raise ValueError('backend response message content is not text')
            text = content or ''
            if choice.get('finish_reason') == 'length':
                last = 'reply cut off (finish_reason=length)'
                fmt_retries += 1
                max_tokens = min(max_tokens * 2, 8192)
                payload = payload_for(req, args, model, messages, max_tokens)
                if attempt <= args.max_retries:
                    continue
                break
            try:
                answer = parse_reply(text, validator)
            except ValueError as exc:
                last = 'unusable reply: %s' % exc
                fmt_retries += 1
                if attempt <= args.max_retries:
                    payload = payload_for(req, args, model, messages + [
                        {'role': 'assistant', 'content': text[-4000:]},
                        {'role': 'user', 'content': 'That reply could not be used (%s). Reply again with only the '
                                                    'JSON object in the required format.' % exc}], max_tokens)
                    continue
                return None, {'error': last, 'raw_reply': text[-4000:], 'attempts': attempt,
                              'prompt_tokens': usage_in, 'completion_tokens': usage_out}
            return answer, {'attempts': attempt, 'format_retries': fmt_retries,
                            'seconds': round(time.monotonic() - started, 1), 'prompt_tokens': usage_in,
                            'completion_tokens': usage_out, 'raw_reply': text, 'served_model': raw.get('model')}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode('utf-8', 'replace')[:400]
            last = 'HTTP %d: %s' % (exc.code, body)
            if exc.code not in qp.RETRY_STATUS:
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, KeyError, IndexError,
                TypeError, ValueError) as exc:
            last = '%s: %s' % (type(exc).__name__, exc)
        if attempt <= args.max_retries:
            time.sleep(delay)
            delay = min(delay * 2, 60)
    return None, {'error': last, 'attempts': attempt, 'prompt_tokens': usage_in, 'completion_tokens': usage_out}


def sample_rows(rows, n):
    if not n or n >= len(rows):
        return rows
    step = len(rows) / n
    return [rows[int(i * step)] for i in range(n)]


def cmd_ask(args):
    """Serialize writers so overlapping CLI runs cannot compact stale state over new answers."""
    args.job.mkdir(parents=True, exist_ok=True)
    with (args.job / '.ask.lock').open('a+') as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log('另一个 ask 正在使用此任务目录；请等它结束后再运行，避免回答互相覆盖。')
            return 2
        return _cmd_ask(args)


def _cmd_ask(args):
    job = args.job
    tasks = TASKS if args.task == 'all' else (args.task,)
    key = os.environ.get(args.api_key_env, '') if args.api_key_env else ''
    if args.api_key_env and not key:
        log(args.api_key_env + ' is empty'); return 2
    model = args.model
    if not model:
        try:
            model = qp.first_model(args.base_url, key, 60)
        except Exception as exc:
            log('Could not list models at %s/models (%s); pass --model.' % (args.base_url, exc)); return 2
    t0 = time.monotonic()
    failed = False
    grand_in = grand_out = 0
    for task in tasks:
        reqs = read_jsonl(job / task / 'requests.jsonl')
        if not reqs:
            log('%s: no requests (run prepare first)' % task)
            if args.task != 'all':
                failed = True
            continue
        error = snapshot_error(job, task, reqs)
        if error:
            log(task + ': ' + error)
            failed = True
            continue
        reqs = sample_rows(reqs, args.sample)
        resp_path = job / task / 'responses.jsonl'
        done = qp.load_done(resp_path)
        todo = []
        for r in reqs:
            fp = fingerprint(r, args, model)
            prev = done.get(r['id'])
            valid_previous = False
            if prev and prev.get('answer') and not prev.get('error'):
                try:
                    VALIDATORS[task](prev['answer'])
                    valid_previous = True
                except ValueError:
                    pass
            if (prev and (valid_previous or prev.get('error'))
                    and prev.get('request_hash') == request_hash(r) and prev.get('fingerprint') == fp
                    and not args.redo and not (args.retry_errors and prev.get('error'))):
                if prev.get('error') or not prev.get('answer'):
                    failed = True
                continue
            todo.append((r, fp))
        if args.limit is not None:
            todo = todo[:args.limit]
        config = {k: getattr(args, k) for k in ('base_url', 'thinking', 'json_schema', 'top_p')}
        config.update(model=model, model_revision=getattr(args, 'model_revision', ''))
        write_json(job / task / 'run.json', config)
        log('[%s] %d requests, %d to send, %d in flight, model %s' % (task, len(reqs), len(todo), args.concurrency, model))
        if not todo:
            continue
        t_task, n_ok, n_err, tin, tout = time.monotonic(), 0, 0, 0, 0
        pool = futures.ThreadPoolExecutor(max_workers=args.concurrency)
        try:
            pending = {pool.submit(ask_one, r, args, key, model): (r, fp) for r, fp in todo}
            for i, fut in enumerate(futures.as_completed(pending), 1):
                r, fp = pending[fut]
                try:
                    answer, meta = fut.result()
                except Exception as exc:
                    # One malformed backend response or request bug must not discard other finished work.
                    answer = None
                    meta = {'error': '%s: %s' % (type(exc).__name__, exc), 'attempts': 0}
                row = {'id': r['id'], 'task': task, 'fingerprint': fp, 'model': model,
                       'request_hash': request_hash(r), 'base_url': args.base_url,
                       'at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'tool_version': VERSION}
                row.update(meta)
                if answer is not None:
                    row['answer'] = answer; n_ok += 1
                else:
                    n_err += 1; failed = True
                tin += meta.get('prompt_tokens', 0); tout += meta.get('completion_tokens', 0)
                with open(resp_path, 'a', encoding='utf-8') as h:
                    h.write(json.dumps(row, ensure_ascii=False) + '\n')
                done[r['id']] = row
                if i % args.progress_every == 0 or i == len(todo):
                    el = time.monotonic() - t_task
                    log('  [%s] %d/%d  ok %d err %d  %.0fs  in %.0f tok/s  out %.0f tok/s%s'
                        % (task, i, len(todo), n_ok, n_err, el, tin / max(el, 1e-9), tout / max(el, 1e-9),
                           ('  ~$%.2f so far' % ((time.monotonic() - t0) / 3600 * args.gpu_price)) if args.gpu_price else ''))
        except KeyboardInterrupt:
            log('Interrupted; finished answers are kept. Run the same command to continue.')
            pool.shutdown(wait=False, cancel_futures=True)
            qp.compact(resp_path, done)
            return 130
        pool.shutdown(wait=True)
        qp.compact(resp_path, done)
        grand_in += tin; grand_out += tout
    el = time.monotonic() - t0
    log('done in %.1f min; tokens in %d, out %d%s' % (el / 60, grand_in, grand_out,
        ('; GPU time ≈ $%.2f at $%.2f/h' % (el / 3600 * args.gpu_price, args.gpu_price)) if args.gpu_price else ''))
    return 3 if failed else 0


# ======================================================================= collect

def similarity(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def balanced(text):
    depth = 0
    for i, ch in enumerate(text):
        if ch == '{' and (i == 0 or text[i - 1] != '\\'):
            depth += 1
        elif ch == '}' and (i == 0 or text[i - 1] != '\\'):
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


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


def _layout_pattern(snippet):
    """A regex for `snippet` that tolerates a different line layout only: each run of spaces / one line break may be any
    run of spaces and tabs with at most one line break (the manuscript wraps and indents; a model rewrites a wrapped line
    with single spaces). A blank line (paragraph break) must still be a blank line; everything else is exact."""
    out = []
    for part in re.split(r'(\s+)', snippet):
        if not part:
            continue
        if not part.isspace():
            out.append(re.escape(part))
        elif part.count('\n') >= 2:
            out.append(r'[ \t]*\n[ \t]*\n\s*')
        else:
            out.append(r'(?:[ \t]+(?:\n[ \t]*)?|\n[ \t]*)')
    return ''.join(out)


def find_original(text, original):
    """([(start, end)], tolerant): exact occurrences of a polish `original`; only when there is none, the occurrences
    that differ from it in line layout alone (see _layout_pattern; decided 2026-11-06 after the first run, where 73 of
    the 76 originals 'not in the block' differed only so). The span is always the manuscript's own text, and every
    check on the composed result (formulas verbatim, commands, braces, comments) still runs on the real source."""
    if not original or not original.strip():
        return [], False
    hits = [(m.start(), m.end()) for m in re.finditer(re.escape(original), text)]
    if hits:
        return hits, False
    return [(m.start(), m.end()) for m in re.finditer(_layout_pattern(original), text)], True


LAYOUT_NOTE = '原文的换行 / 缩进与稿子不同，按版式定位；采用后这几行在源码里合成一行（输出不变）'


def polish_checks(rev, block):
    """(status, reasons): status 'clean', 'flagged' (needs a human tick) or 'rejected' (never applied)."""
    old, new = rev['original'], rev['revised']
    rejected, flagged = [], []
    hits, _ = find_original(block, old)
    if not hits:
        rejected.append('original 不在本块原文中（不是原样抄写）')
    elif len(hits) > 1:
        rejected.append('original 在本块中出现 %d 次，无法定位' % len(hits))
    w = qp.math_warning(old, new, '')
    if w:
        rejected.append(w)
    logic = qp.logic_warning(old, new)
    if logic:
        flagged.append(logic)
    if squash(old) == squash(new):
        rejected.append('修改前后相同')
    if new.count('$') % 2 != old.count('$') % 2 or balanced(old) != balanced(new):
        rejected.append('$ 或花括号配对被破坏')
    struct = re.compile(r'\\(?:begin|end)\{[^}]*\}|\\item\b|\\label\{[^}]*\}|\\(?:sub)*section\*?')
    if struct.findall(old) != struct.findall(new):
        rejected.append('改动了环境、\\item 或 \\label 结构')
    commands = re.compile(r'\\(?:[A-Za-z@]+\*?|[^A-Za-z@])')
    if commands.findall(old) != commands.findall(new):
        rejected.append('改动了 LaTeX 命令或宏')
    comments = re.compile(r'(?<!\\)(?:\\\\)*%[^\n]*')
    if comments.findall(old) != comments.findall(new):
        rejected.append('改动了 LaTeX 注释，可能隐藏正文')
    if len(hits) == 1:
        start, end = hits[0]
        composed = block[:start] + new + block[end:]
        if qp.math_tokens(block) != qp.math_tokens(composed):
            rejected.append('放回原文后改动了公式或引用（含公式内部片段）')
        before, after = syntax_tokens(block), syntax_tokens(composed)
        if before['commands'] != after['commands']:
            rejected.append('放回原文后改变了 LaTeX 命令边界')
        if before['groups'] != after['groups']:
            rejected.append('放回原文后改变了花括号结构')
        if before['comments'] != after['comments']:
            rejected.append('放回原文后改变了 LaTeX 注释')
    if re.search(r'\*\*|`|^#', new, re.M):
        flagged.append('出现 Markdown 记号')
    if '\n\n' in new.strip() and '\n\n' not in old.strip():
        flagged.append('新增了空行（会多出一个段落）')
    sim = similarity(old, new)
    if sim < 0.5:
        flagged.append('改动很大（保留原文 %.0f%%）' % (100 * sim))
    status = 'rejected' if rejected else ('flagged' if flagged else 'clean')
    return status, rejected, flagged, sim


def collect_polish(job, reqs, done):
    out_md = ['# 全文润色建议（27B）', '',
              '在要采用的修改下把 `- [ ]` 改成 `- [x]`，可以直接改“改为”框里的文字。'
              '“规则检查通过”的修改可以用 `apply --accept-clean` 一次全部采用；“需人工看”的必须勾选；“已拒绝”的不会被应用。', '']
    stats = {'blocks': len(reqs), 'answered': 0, 'errors': 0, 'keep': 0, 'revise': 0, 'revisions': 0,
             'clean': 0, 'flagged': 0, 'rejected': 0, 'math_doubt': 0, 'first_try_ok': 0, 'sim': []}
    reject_reasons, body, doubts = {}, [], []
    previous = qp.read_decisions(job / 'polish' / 'review.md')
    for r in reqs:
        row = done.get(r['id'])
        meta = r['meta']
        if not row:
            continue
        if not row.get('answer'):
            stats['errors'] += 1
            body += ['## %s（出错）' % meta['location'], '', '- 错误：' + str(row.get('error'))[:300], '']
            continue
        stats['answered'] += 1
        a = row['answer']
        if not row.get('format_retries'):
            stats['first_try_ok'] += 1
        stats[a['verdict']] += 1
        if qp.MATH_DOUBT in a.get('note_zh', ''):
            stats['math_doubt'] += 1; doubts.append((meta['location'], a['note_zh']))
        if a['verdict'] == 'keep' and not a.get('revisions'):
            continue
        body += ['## %s' % meta['location'], '']
        if meta.get('hints'):
            body.append('- 本块含语言问题清单里的 %d 条' % len(meta['hints']))
        if a.get('note_zh'):
            body.append('- 模型说明：' + a['note_zh'])
        for i, rev in enumerate(a.get('revisions') or [], 1):
            stats['revisions'] += 1
            status, rej, flg, sim = polish_checks(rev, meta['block'])
            reasons = rej + flg
            if status != 'rejected' and find_original(meta['block'], rev['original'])[1]:
                reasons = reasons + [LAYOUT_NOTE]
            stats[status] += 1; stats['sim'].append(sim)
            for reason in rej:
                k = re.sub(r'\d+', '#', reason)[:40]
                reject_reasons[k] = reject_reasons.get(k, 0) + 1
            key, stamp = qp.revision_key(row, i), qp.revision_stamp(rev)
            mine = previous.get(key)
            if mine and mine['stamp'] != stamp:
                mine = None
            tag = {'clean': '规则检查通过', 'flagged': '需人工看', 'rejected': '已拒绝'}[status]
            fence = qp._fence(rev['original'] + '\n' + (mine['revised'] if mine else rev['revised']))
            body += ['', '#### 修改 %d · `%s` · `%s`' % (i, key, stamp), '',
                     '- %s%s' % (tag, ('：' + '；'.join(reasons)) if reasons else ''),
                     '- [%s] 接受' % ('x' if mine and mine['accepted'] else ' '), '',
                     '原文：', fence + 'latex', rev['original'], fence,
                     '改为（可直接编辑）：', fence + 'latex', mine['revised'] if mine else rev['revised'], fence]
        body.append('')
    sims = stats.pop('sim')
    stats['mean_text_kept'] = round(sum(sims) / len(sims), 3) if sims else None
    stats['reject_reasons'] = reject_reasons
    head = ('共 %(blocks)d 块：已回答 %(answered)d，出错 %(errors)d；建议修改 %(revise)d 块、不改 %(keep)d 块；'
            '修改 %(revisions)d 条：规则检查通过 %(clean)d，需人工看 %(flagged)d，已拒绝 %(rejected)d。' % stats)
    out_md.insert(3, head)
    if doubts:
        out_md += ['## 模型提到的数学疑点（文字未改，交给 Claude 核对）', ''] + \
                  ['- **%s**：%s' % (l, n) for l, n in doubts] + ['']
    tmp = job / 'polish' / 'review.md.tmp'
    tmp.write_text('\n'.join(out_md + body) + '\n', encoding='utf-8')
    os.replace(tmp, job / 'polish' / 'review.md')
    claude = ['# 给 Claude：润色里的数学疑点和被拒绝的修改', '']
    claude += ['## 数学疑点', ''] + ['- %s：%s' % (l, n) for l, n in doubts] + ['']
    (job / 'polish' / 'for-claude.md').write_text('\n'.join(claude) + '\n', encoding='utf-8')
    return head, stats


def found_anywhere(needle, *haystacks):
    compact = squash(needle)
    if not compact or (len(compact) < 8 and not qp.MATH.search(needle)):
        return False
    # Short formulas such as $x>0$ are still strong verbatim evidence.
    return any(needle in h for h in haystacks if h)


def found_quote(needle, *haystacks):
    """Evidence quotes (triage evidence, refs cited_fact): verbatim up to whitespace. The manuscript wraps lines and
    indents them with tabs inside environments, while a quotation naturally joins them with one space; nothing else is
    normalised (spacing inside a formula such as n-1 / n - 1 still differs). This only decides which review list a
    finding goes to; polish originals and triage patches are still located exactly (found_anywhere, polish_checks)."""
    compact = squash(needle)
    if not compact or (len(compact) < 8 and not qp.MATH.search(needle)):
        return False
    return any(compact in squash(h) for h in haystacks if h)


def collect_triage(job, reqs, done, tex, conventions):
    groups = {'real_gap': [], 'cannot_decide': [], 'unverified': [], 'resolved': [], 'obvious': [], 'error': []}
    stats = {'requests': len(reqs), 'answered': 0, 'errors': 0, 'first_try_ok': 0}
    for r in reqs:
        row = done.get(r['id'])
        if not row:
            continue
        m = r['meta']
        if not row.get('answer'):
            stats['errors'] += 1; groups['error'].append((m, None, ['出错：' + str(row.get('error'))[:200]])); continue
        stats['answered'] += 1
        if not row.get('format_retries'):
            stats['first_try_ok'] += 1
        a, notes = row['answer'], []
        v = a['verdict']
        if v == 'resolved':
            if not found_quote(a['evidence'], m['material'], conventions):
                notes.append('evidence 不是书中原文（无法核实），按未核实处理')
                v = 'unverified'
        if a['patch_original'] or a['patch_revised']:
            if not found_anywhere(a['patch_original'], tex):
                notes.append('patch_original 不在当前稿中')
            else:
                hits = len(qp.find_all(tex, a['patch_original']))
                if hits > 1:
                    notes.append('patch_original 在稿中出现 %d 次' % hits)
            old_t, new_t = qp.math_tokens(a['patch_original']), qp.math_tokens(a['patch_revised'])
            it = iter(new_t)
            if not all(any(x == y for y in it) for x in old_t):
                notes.append('patch 删改了原有公式（应只增不改）')
        if v == 'real_gap' and not a['patch_revised']:
            notes.append('real_gap 但没给 patch')
        groups[v].append((m, a, notes))
    stats.update({k: len(v) for k, v in groups.items()})
    md = ['# DeepSeek 未看条目初筛（27B）', '',
          '共 %(requests)d 条：已回答 %(answered)d，出错 %(errors)d。real_gap %(real_gap)d，cannot_decide %(cannot_decide)d，'
          'evidence 无法核实 %(unverified)d，resolved %(resolved)d，obvious %(obvious)d。' % stats, '',
          '前三组交给 Claude 复核（见 for-claude.md）；resolved / obvious 只列表备查。', '']
    titles = {'real_gap': '真缺口（附最小补丁）', 'cannot_decide': '无法判断', 'unverified': '自称已解决但证据不是原文',
              'error': '出错', 'resolved': '已解决（证据已核实为原文）', 'obvious': '显然，不需要改'}
    for g in ('real_gap', 'cannot_decide', 'unverified', 'error', 'resolved', 'obvious'):
        if not groups[g]:
            continue
        md += ['## %s（%d）' % (titles[g], len(groups[g])), '']
        for m, a, notes in groups[g]:
            md.append('- **#%s** %s，第 %d 行（%s, %s, %s）' % (m['no'], m['unit_now'], m['line'], m['severity'], m['task_kind'], m['type']))
            if g in ('resolved', 'obvious'):
                md.append('  - %s' % (a['note_zh'] if a else ''))
                continue
            md.append('  - 引文：%s' % squash(m['quote'])[:300])
            md.append('  - DeepSeek：%s' % squash(m['reason'])[:500])
            if a:
                md.append('  - 27B：%s' % a['note_zh'])
                if a['evidence']:
                    md.append('  - 证据：%s' % squash(a['evidence'])[:300])
                if a['patch_revised']:
                    md += ['  - 补丁原文：`%s`' % squash(a['patch_original'])[:400],
                           '  - 补丁改为：`%s`' % squash(a['patch_revised'])[:500]]
            for n in notes:
                md.append('  - ⚠️ ' + n)
        md.append('')
    (job / 'triage' / 'review.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    claude = ['# 给 Claude：27B 初筛后需要复核的 DeepSeek 条目', '',
              '每条：序号 · 单元 · 当前行号 · DeepSeek 原话 · 27B 判断（含补丁）。请逐条判断是否改 nt.tex。', '']
    for g in ('real_gap', 'unverified', 'cannot_decide', 'error'):
        for m, a, notes in groups[g]:
            claude.append('- [%s] #%s · %s · L%d · 引文「%s」 · DS：%s · 27B：%s%s%s' % (
                g, m['no'], m['unit_now'], m['line'], squash(m['quote'])[:200], squash(m['reason'])[:350],
                a['note_zh'] if a else '',
                (' · 补丁：「%s」→「%s」' % (squash(a['patch_original'])[:250], squash(a['patch_revised'])[:300]))
                if a and a['patch_revised'] else '',
                (' · ⚠️ ' + '；'.join(notes)) if notes else ''))
    (job / 'triage' / 'for-claude.md').write_text('\n'.join(claude) + '\n', encoding='utf-8')
    head = md[2]
    return head, stats


def collect_refs(job, reqs, done):
    groups = {'mismatch': [], 'hypotheses_unchecked': [], 'unclear': [], 'quote_unverified': [], 'supports': [],
              'error': []}
    stats = {'requests': len(reqs), 'answered': 0, 'errors': 0, 'first_try_ok': 0}
    for r in reqs:
        row = done.get(r['id'])
        if not row:
            continue
        m = r['meta']
        if not row.get('answer'):
            stats['errors'] += 1; groups['error'].append((m, None, [str(row.get('error'))[:200]])); continue
        stats['answered'] += 1
        if not row.get('format_retries'):
            stats['first_try_ok'] += 1
        a, notes, v = row['answer'], [], row['answer']['verdict']
        if v == 'supports' and (not a['cited_fact'] or a['missing_hypotheses']):
            notes.append('支持结论缺少证据或仍有未核对前提')
            v = 'quote_unverified'
        elif a['cited_fact'] and not found_quote(a['cited_fact'], m['target']):
            notes.append('cited_fact 不是被引定理的原文')
            if v == 'supports':
                v = 'quote_unverified'
        groups[v].append((m, a, notes))
    stats.update({k: len(v) for k, v in groups.items()})
    titles = {'mismatch': '引用与用途不符', 'hypotheses_unchecked': '前提没有核对', 'unclear': '无法判断',
              'quote_unverified': '判为支持但引文不是原文', 'error': '出错', 'supports': '支持'}
    md = ['# 引用核对（27B）', '',
          '共 %(requests)d 处：已回答 %(answered)d，出错 %(errors)d；不符 %(mismatch)d，前提未核对 %(hypotheses_unchecked)d，'
          '无法判断 %(unclear)d，引文未核实 %(quote_unverified)d，支持 %(supports)d。' % stats, '']
    claude = ['# 给 Claude：27B 认为可能有问题的引用', '']
    for g in ('mismatch', 'hypotheses_unchecked', 'unclear', 'quote_unverified', 'error'):
        if not groups[g]:
            continue
        md += ['## %s（%d）' % (titles[g], len(groups[g])), '']
        for m, a, notes in groups[g]:
            md += ['- **L%d** %s 引 `%s`' % (m['line'], m['where'], m['label']),
                   '  - 句子：%s' % squash(m['sentence'])[:600]]
            if a:
                md.append('  - 27B：%s' % a['note_zh'])
                if a['missing_hypotheses']:
                    md.append('  - 未核对的前提：' + '；'.join(a['missing_hypotheses']))
            md += ['  - ⚠️ ' + n for n in notes]
            claude.append('- [%s] L%d · %s · 引 %s · 句子「%s」 · 27B：%s%s' % (
                g, m['line'], m['where'], m['label'], squash(m['sentence'])[:400], a['note_zh'] if a else '',
                (' · 缺前提：' + '；'.join(a['missing_hypotheses'])) if a and a['missing_hypotheses'] else ''))
        md.append('')
    (job / 'refs' / 'review.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    (job / 'refs' / 'for-claude.md').write_text('\n'.join(claude) + '\n', encoding='utf-8')
    return md[2], stats


def cmd_collect(args):
    job = args.job
    if not (job / 'manifest.json').exists():
        log('没有 manifest.json，请先 prepare。'); return 3
    summary, failed = {}, False
    for task in TASKS:
        reqs = read_jsonl(job / task / 'requests.jsonl')
        if not reqs:
            continue
        error = snapshot_error(job, task, reqs)
        if error:
            log(task + ': ' + error)
            summary[task] = {'requests': len(reqs), 'answered': 0, 'errors': len(reqs), 'snapshot_error': error}
            failed = True
            continue
        tex = (job / task / 'nt.prepared.tex').read_text(encoding='utf-8')
        doc = Doc(tex)
        done, stale = current_responses(job, task, reqs, qp.load_done(job / task / 'responses.jsonl'))
        if task == 'polish':
            head, st = collect_polish(job, reqs, done)
        elif task == 'triage':
            head, st = collect_triage(job, reqs, done, tex, doc.conventions)
        else:
            head, st = collect_refs(job, reqs, done)
        rows = [done[r['id']] for r in reqs if r['id'] in done]
        st['stale'] = stale
        st['pending'] = sum(r['id'] not in done for r in reqs)
        if st.get('errors') or stale:
            failed = True
        st['prompt_tokens'] = sum(x.get('prompt_tokens', 0) for x in rows)
        st['completion_tokens'] = sum(x.get('completion_tokens', 0) for x in rows)
        secs = [x['seconds'] for x in rows if isinstance(x.get('seconds'), (int, float))]
        st['mean_seconds'] = round(sum(secs) / len(secs), 1) if secs else None
        summary[task] = st
        print('[%s] %s\n  → %s' % (task, head, job / task / 'review.md'))
    write_json(job / 'summary.json', summary)
    return 3 if failed else 0


def cmd_status(args):
    """Read-only progress report; pending answers are normal, corrupt jobs are not."""
    report = {}
    failed = False
    prepared = False
    tasks = TASKS if args.task == 'all' else (args.task,)
    for task in tasks:
        stats = dict(state='not_prepared', total=0, completed=0, pending=0, errors=0, stale=0)
        report[task] = stats
        try:
            reqs = read_jsonl(args.job / task / 'requests.jsonl')
            if not reqs:
                continue
            prepared = True
            stats['total'] = len(reqs)
            error = snapshot_error(args.job, task, reqs)
            if error:
                raise ValueError(error)
            rows = read_jsonl(args.job / task / 'responses.jsonl')
            if any(not isinstance(row, dict) or not isinstance(row.get('id'), str) for row in rows):
                raise ValueError('回答记录格式无效')
            done, _ = current_responses(args.job, task, reqs, {row['id']: row for row in rows})
            issues = []
            for req in reqs:
                row = done.get(req['id'])
                if not row:
                    stats['pending'] += 1
                    kind, reason = 'pending', '尚未回答'
                elif row.get('stale'):
                    stats['stale'] += 1
                    kind, reason = 'stale', row.get('error', '回答已过期')
                elif row.get('error') or not row.get('answer'):
                    stats['errors'] += 1
                    kind, reason = 'error', row.get('error') or '回答为空'
                else:
                    stats['completed'] += 1
                    continue
                if args.details:
                    issues.append(dict(id=req['id'], state=kind, reason=reason))
            stats['state'] = 'ready' if stats['completed'] == stats['total'] else 'incomplete'
            if args.details:
                stats['issues'] = issues
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            stats.update(state='invalid', reason=str(exc))
            failed = True
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print('| 任务 | 状态 | 总数 | 完成 | 待处理 | 失败 | 过期 |')
        print('|---|---|---:|---:|---:|---:|---:|')
        for task, stats in report.items():
            print('| %s | %s | %d | %d | %d | %d | %d |' %
                  (task, stats['state'], stats['total'], stats['completed'],
                   stats['pending'], stats['errors'], stats['stale']))
            if stats.get('reason'):
                print('%s: %s' % (task, stats['reason']))
            for issue in stats.get('issues', []):
                print('%s %s [%s]: %s' % (task, issue['id'], issue['state'], issue['reason']))
    return 3 if failed or not prepared else 0


def cmd_verify(args):
    tasks = TASKS if args.task == 'all' else (args.task,)
    checked, failed = 0, False
    for task in tasks:
        reqs = read_jsonl(args.job / task / 'requests.jsonl')
        if not reqs:
            if args.task != 'all':
                log(task + ': no prepared requests'); failed = True
            continue
        error = snapshot_error(args.job, task, reqs)
        if error:
            log(task + ': ' + error); failed = True; continue
        reqs = sample_rows(reqs, args.sample)
        done, stale = current_responses(args.job, task, reqs,
                                        qp.load_done(args.job / task / 'responses.jsonl'))
        bad = sum(not done.get(r['id'], {}).get('answer') or bool(done.get(r['id'], {}).get('error')) for r in reqs)
        log('%s: selected %d, incomplete/error %d, stale %d' % (task, len(reqs), bad, stale))
        checked += len(reqs)
        failed = failed or bool(bad)
    return 3 if failed or not checked else 0


# ======================================================================= apply (polish)

def invariants(tex):
    body = tex[tex.find('\\begin{document}'):]
    return dict(syntax_tokens(body), **{'math': qp.math_tokens(body),
            'labels': re.findall(r'\\label\{[^}]*\}', body),
            'envs': re.findall(r'\\(?:begin|end)\{[^}]*\}', body),
            'heads': re.findall(r'\\(?:section|subsection)\*?\{[^}]*\}', body)})


def compile_check(tex_text, name='nt.polished.tex'):
    if not shutil.which('pdflatex'):
        return None, 'pdflatex 不可用，未编译'
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / name
        p.write_text(tex_text, encoding='utf-8')
        try:
            for _ in range(2):
                result = subprocess.run(['pdflatex', '-no-shell-escape', '-interaction=nonstopmode', '-halt-on-error', name], cwd=d,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=900)
                if result.returncode:
                    return False, 'pdflatex 编译失败（退出码 %d）' % result.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, '编译未完成：%s' % exc
        logp = p.with_suffix('.log')
        log_text = logp.read_text(encoding='utf-8', errors='replace') if logp.exists() else ''
        errors = len(re.findall(r'^!', log_text, re.M))
        undefined = len(re.findall(r'undefined', log_text))
        pages = re.search(r'Output written on .*?\((\d+) pages?\b', log_text)
        ok = errors == 0 and pages is not None
        return ok, '错误 %d，undefined 警告 %d，%s' % (errors, undefined, ('%s 页' % pages.group(1)) if pages else '没有生成 PDF')


def cmd_apply(args):
    job = args.job
    tex_path = args.tex
    tex = tex_path.read_text(encoding='utf-8')
    rows = read_jsonl(job / 'polish' / 'requests.jsonl')
    if not rows:
        log('没有润色请求，请先 prepare。'); return 3
    error = snapshot_error(job, 'polish', rows)
    if error:
        log(error); return 3
    reqs = {r['id']: r for r in rows}
    done, stale = current_responses(job, 'polish', rows, qp.load_done(job / 'polish' / 'responses.jsonl'))
    if stale or any(r.get('error') for r in done.values()):
        log('存在过期或失败的回答，请先 ask --retry-errors 并 collect；未生成新稿。'); return 3
    if not any(row.get('answer') for row in done.values()):
        log('没有可用的润色回答，请先 ask。'); return 3
    decisions = qp.read_decisions(job / 'polish' / 'review.md')
    prepared = (job / 'polish' / 'nt.prepared.tex').read_text(encoding='utf-8')
    same = prepared == tex
    if not same:
        log('注意：--tex 与 prepare 时的稿子不同（例如之后又改了数学）。修改会按原文文字重新定位；找不到或有歧义的跳过。')
    planned, skipped = [], []
    for rid, row in done.items():
        if rid not in reqs or not row.get('answer'):
            continue
        meta = reqs[rid]['meta']
        for i, rev in enumerate(row['answer'].get('revisions') or [], 1):
            key, stamp = qp.revision_key(row, i), qp.revision_stamp(rev)
            status, rej, flg, _ = polish_checks(rev, meta['block'])
            reasons = rej + flg
            mine = decisions.get(key)
            if mine and mine['stamp'] != stamp:
                mine = None
            accepted = bool(mine and mine['accepted']) or (args.accept_clean and status == 'clean')
            if not accepted:
                continue
            if status == 'rejected':
                skipped.append((key, meta['location'], '已拒绝：' + '；'.join(reasons))); continue
            revised = mine['revised'] if (mine and mine['accepted']) else rev['revised']
            final_status, final_rej, _, _ = polish_checks({'original': rev['original'], 'revised': revised}, meta['block'])
            if final_status == 'rejected':
                skipped.append((key, meta['location'], '最终替换未通过检查：' + '；'.join(final_rej))); continue
            hits, _ = find_original(tex, rev['original'])
            if same:
                hits = [h for h in hits if meta['start'] <= h[0] and h[1] <= meta['end']]
            if len(hits) != 1:
                skipped.append((key, meta['location'], '原文在稿中出现 %d 次' % len(hits))); continue
            planned.append({'key': key, 'loc': meta['location'], 'start': hits[0][0], 'end': hits[0][1],
                            'revised': revised})
    planned.sort(key=lambda p: p['start'])
    applied, last = [], -1
    for p in planned:
        if p['start'] < last:
            skipped.append((p['key'], p['loc'], '与前一处修改重叠')); continue
        applied.append(p); last = p['end']
    new = tex
    for p in reversed(applied):
        new = new[:p['start']] + p['revised'] + new[p['end']:]
    inv_old, inv_new = invariants(tex), invariants(new)
    broken = [k for k in inv_old if inv_old[k] != inv_new[k]]
    out = job / 'polish' / (tex_path.stem + '.polished.tex')
    compile_failed = False
    compile_message = None
    if args.compile:
        ok, msg = compile_check(new)
        compile_failed = ok is not True
        compile_message = '编译：' + ('✅ ' if ok is True else '❌ ') + msg
    failed = bool(broken) or compile_failed
    candidate = out.with_name(tex_path.stem + '.failed.tex') if failed else out
    candidate_tmp = candidate.with_name(candidate.name + '.tmp')
    candidate_tmp.write_text(new, encoding='utf-8')
    os.replace(candidate_tmp, candidate)
    diff = ''.join(difflib.unified_diff(tex.splitlines(keepends=True), new.splitlines(keepends=True),
                                        fromfile=tex_path.name, tofile=candidate.name, n=2))
    (job / 'polish' / 'polish.diff').write_text(diff, encoding='utf-8')
    rep = ['# 应用润色', '', '原稿：`%s`（未修改，SHA-256 前缀 `%s`）' % (tex_path, qp.sha(tex)[:12]),
           ('失败候选稿' if failed else '新稿') + '：`%s`（SHA-256 前缀 `%s`）' % (candidate, qp.sha(new)[:12]), '',
           '已应用 %d 处，跳过 %d 处。%s' % (len(applied), len(skipped), '（含 --accept-clean 自动采用）' if args.accept_clean else ''), '',
           '全文不变量（公式与引用、宏与命令、花括号、注释、标签、环境、章节标题）：' + ('全部一致 ✅' if not broken else '❌ 变了：' + '、'.join(broken))]
    if compile_message:
        rep.append(compile_message)
    if failed:
        rep.append('验证失败，未更新正式的 .polished.tex 文件。请先处理 apply-report.md 中的问题。')
    if skipped:
        rep += ['', '## 跳过', ''] + ['- %s · `%s`：%s' % (loc, k, why) for k, loc, why in skipped]
    (job / 'polish' / 'apply-report.md').write_text('\n'.join(rep) + '\n', encoding='utf-8')
    print('\n'.join(rep[:rep.index('## 跳过')] if '## 跳过' in rep else rep).rstrip())
    if failed:
        log('验证失败：候选稿仅供排查，未发布新的正式稿。')
        return 4
    target = getattr(args, 'out', None)
    if target is not None:
        if target.exists() and not getattr(args, 'force', False):
            log('%s 已存在，未覆盖（初筛和引用核查的修改可能已经写在里面）。确认要替换时加 --force。' % target)
            return 5
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + '.tmp')
        tmp.write_text(new, encoding='utf-8')
        os.replace(tmp, target)
        print('已发布到 %s（SHA-256 前缀 %s）。初筛和引用核查要改的地方直接在这份文件上改。' % (target, qp.sha(new)[:12]))
    return 0


# ======================================================================= prepare / estimate

def estimate(job, gpu_in=8000.0, gpu_out=1500.0, overhead_h=0.75, price=2.5, mac_in=120.0, mac_out=6.0):
    lines = ['| 任务 | 请求数 | 输入 token（估） | 其中共享前缀 | 输出上限 | 预计输出 |', '|---|---:|---:|---:|---:|---:|']
    tot_in = tot_out = 0
    exp_out = {'polish': 350, 'triage': 160, 'refs': 140}
    res = {}
    for task in TASKS:
        reqs = read_jsonl(job / task / 'requests.jsonl')
        if not reqs:
            continue
        chars = sum(sum(len(m['content']) for m in r['messages']) for r in reqs)
        sys_chars = len(reqs[0]['messages'][0]['content'])
        tin = chars / CHARS_PER_TOKEN
        tout = exp_out[task] * len(reqs)
        cap = sum(r['max_tokens'] for r in reqs)
        tot_in += tin; tot_out += tout
        res[task] = {'requests': len(reqs), 'input_tokens': int(tin), 'expected_output_tokens': tout}
        lines.append('| %s | %d | %.2fM | %.0f/请求 | %.2fM | %.2fM |' % (task, len(reqs), tin / 1e6, sys_chars / CHARS_PER_TOKEN,
                                                                     cap / 1e6, tout / 1e6))
    gpu_h = tot_in / gpu_in / 3600 + tot_out / gpu_out / 3600 + overhead_h
    mac_h = tot_in / mac_in / 3600 + tot_out / mac_out / 3600
    lines += ['', '合计：输入约 %.2fM token，输出约 %.2fM token。' % (tot_in / 1e6, tot_out / 1e6),
              'GPU（vLLM，单卡 H100/A100-80G，按读入 %.0f tok/s、生成 %.0f tok/s 粗估，另加 %.2f 小时启动/下载）：约 %.1f 小时，'
              '按 $%.2f/小时约 $%.1f。共享前缀会被 vLLM 前缀缓存，实际读入更快。' % (gpu_in, gpu_out, overhead_h, gpu_h, price, gpu_h * price),
              'Mac（MLX 4-bit，按读入 %.0f tok/s、生成 %.0f tok/s）：约 %.0f 小时，只适合 --sample 小样本。' % (mac_in, mac_out, mac_h)]
    return '\n'.join(lines), res


def cmd_prepare(args):
    try:
        return _cmd_prepare(args)
    except (OSError, ValueError, KeyError, TypeError, csv.Error) as exc:
        log('prepare 失败：%s' % exc)
        return 2


def resolve_tex(path):
    """The manuscript to prepare: by default the stage's baseline.tex, which must have its pinned hash."""
    if path is None:
        if not BASELINE.is_file():
            raise ValueError('找不到 %s：nt27b 放在 nt-final-stage/2-branch2/ 里时从上一层读 baseline.tex；'
                             '单独使用时请用 --tex 指定稿件' % BASELINE)
        path = BASELINE
    digest = qp.sha(path.read_text(encoding='utf-8'))
    if path.resolve() == BASELINE.resolve() and digest != BASELINE_SHA256:
        raise ValueError('%s 的 SHA-256 是 %s…，应为 %s…：baseline 被改过或换错了文件' % (path, digest[:12], BASELINE_SHA256[:12]))
    if digest != BASELINE_SHA256:
        log('注意：--tex 不是 baseline.tex（SHA-256 %s…）。branch2 必须从 baseline 开始改；只在测试或试跑时这样用。' % digest[:12])
    return path


def _cmd_prepare(args):
    out = args.out
    args.tex = resolve_tex(args.tex)
    tex = args.tex.read_text(encoding='utf-8')
    digest = qp.sha(tex)
    mp = out / 'manifest.json'
    old = json.loads(mp.read_text(encoding='utf-8')) if mp.exists() else {}
    if args.task != 'all' and old and (old.get('tex_sha256') != digest or old.get('tool_version') != VERSION):
        log('部分 prepare 不能更换稿件或任务版本；请 prepare --task all，或使用新的 --out 目录。')
        return 3
    tasks = TASKS if args.task == 'all' else (args.task,)
    if 'triage' in tasks and not (args.csv and args.pre_fix_tex):
        log('triage 需要 --csv 和 --pre-fix-tex')
        return 2

    # Build every generated file beside the job first. Input/parsing failures leave an existing job untouched.
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.nt27b-prepare-', dir=str(out.parent)) as temporary:
        stage = Path(temporary) / 'stage'
        stage.mkdir()
        shutil.copyfile(args.tex, stage / 'nt.prepared.tex')
        doc = Doc(tex)
        info = {'tool_version': VERSION, 'tex': str(args.tex), 'tex_copy': 'nt.prepared.tex',
                'tex_sha256': digest, 'prepared_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'tasks': {}}
        if 'polish' in tasks:
            info['tasks']['polish'] = prepare_polish(doc, args.list, stage)
        if 'triage' in tasks:
            info['tasks']['triage'] = prepare_triage(doc, args.csv, args.pre_fix_tex, stage,
                                                     args.include_substantive, args.include_gone)
        if 'refs' in tasks:
            info['tasks']['refs'] = prepare_refs(doc, stage)
        for task in tasks:
            task_dir = stage / task
            requests = read_jsonl(task_dir / 'requests.jsonl')
            for request in requests:
                request['source_sha256'] = digest
            write_jsonl(task_dir / 'requests.jsonl', requests)
            (task_dir / 'nt.prepared.tex').write_text(tex, encoding='utf-8')
            info['tasks'][task]['tex_sha256'] = digest
        if args.task != 'all' and old:
            merged = old.get('tasks', {}).copy()
            merged.update(info['tasks'])
            info['tasks'] = merged
            # estimate() should still include requests from tasks not rebuilt in this partial prepare.
            for task in merged.keys() - set(tasks):
                previous = out / task / 'requests.jsonl'
                if previous.exists():
                    (stage / task).mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(previous, stage / task / 'requests.jsonl')
        write_json(stage / 'manifest.json', info)
        table, _ = estimate(stage)
        (stage / 'estimate.md').write_text(table + '\n', encoding='utf-8')

        out.mkdir(parents=True, exist_ok=True)
        generated = [Path('nt.prepared.tex')]
        for task in tasks:
            generated += [Path(task) / 'requests.jsonl', Path(task) / 'nt.prepared.tex']
        generated += [Path('estimate.md'), Path('manifest.json')]  # commit the manifest last
        for relative in generated:
            destination = out / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage / relative, destination)

    for t, v in info['tasks'].items():
        print('[%s] %s' % (t, json.dumps({k: v[k] for k in v if not isinstance(v[k], list)}, ensure_ascii=False)))
    print(table)
    return 0


def cmd_estimate(args):
    table, _ = estimate(args.job, args.gpu_in, args.gpu_out, args.overhead_h, args.gpu_price)
    print(table)
    return 0


def cmd_show(args):
    reqs = read_jsonl(args.job / args.task / 'requests.jsonl')
    if not reqs:
        log('no requests'); return 2
    if args.index >= len(reqs):
        log('index out of range: %d (valid: 0..%d)' % (args.index, len(reqs) - 1))
        return 2
    r = reqs[args.index]
    for m in r['messages']:
        print('\n----- %s -----\n%s' % (m['role'], m['content']))
    print('\n----- meta -----\n' + json.dumps({k: v for k, v in r['meta'].items() if k not in ('block', 'material', 'target')},
                                             ensure_ascii=False, indent=1))
    return 0


def nonnegative_int(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError('expected an integer')
    if number < 0:
        raise argparse.ArgumentTypeError('expected an integer >= 0')
    return number


def positive_int(value):
    number = nonnegative_int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('expected an integer >= 1')
    return number


def nonnegative_float(value):
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError('expected a number')
    if not 0 <= number < float('inf'):
        raise argparse.ArgumentTypeError('expected a finite number >= 0')
    return number


def positive_float(value):
    number = nonnegative_float(value)
    if number == 0:
        raise argparse.ArgumentTypeError('expected a finite number > 0')
    return number


def probability(value):
    number = nonnegative_float(value)
    if not 0 < number <= 1:
        raise argparse.ArgumentTypeError('expected a number in (0, 1]')
    return number


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--version', action='version', version='nt27b ' + VERSION)
    sub = p.add_subparsers(dest='cmd', required=True)

    a = sub.add_parser('prepare', help='build the request files; sends nothing')
    a.add_argument('--tex', type=Path, default=None,
                   help='manuscript to prepare (default: ../baseline.tex, hash-checked; branch2 starts from it)')
    a.add_argument('--out', type=Path, default=Path('job'))
    a.add_argument('--task', choices=TASKS + ('all',), default='all')
    a.add_argument('--list', type=Path, default=HERE / '语言问题清单.txt', help='language list (hints for polish)')
    a.add_argument('--csv', type=Path, default=HERE / 'data' / 'ntaudit-DS反馈分拣.csv')
    a.add_argument('--pre-fix-tex', type=Path, default=HERE / 'data' / 'nt.before-fixes.tex',
                   help='nt.tex before the fixes (the CSV line numbers refer to it)')
    a.add_argument('--include-substantive', action='store_true',
                   help='triage also the unreviewed "待看:可能实质" rows (about 1100 more)')
    a.add_argument('--include-gone', action='store_true', help='triage also findings whose quote was rewritten')
    a.set_defaults(func=cmd_prepare)

    a = sub.add_parser('estimate', help='token / time / cost estimate of a prepared job')
    a.add_argument('job', type=Path)
    a.add_argument('--gpu-in', type=positive_float, default=8000.0)
    a.add_argument('--gpu-out', type=positive_float, default=1500.0)
    a.add_argument('--overhead-h', type=nonnegative_float, default=0.75)
    a.add_argument('--gpu-price', type=nonnegative_float, default=2.5)
    a.set_defaults(func=cmd_estimate)

    a = sub.add_parser('show', help='print one prepared prompt')
    a.add_argument('job', type=Path)
    a.add_argument('--task', choices=TASKS, default='polish')
    a.add_argument('--index', type=nonnegative_int, default=0)
    a.set_defaults(func=cmd_show)

    a = sub.add_parser('ask', help='send requests to an OpenAI-compatible endpoint (resumable)')
    a.add_argument('job', type=Path)
    a.add_argument('--task', choices=TASKS + ('all',), default='all')
    a.add_argument('--base-url', default=os.environ.get('NT27B_BASE_URL', 'http://127.0.0.1:8080/v1'))
    a.add_argument('--model', help='model id; default: first entry of GET /models')
    a.add_argument('--model-revision', default='', help='weight / adapter revision, part of cache identity')
    a.add_argument('--api-key-env', default='')
    a.add_argument('--concurrency', type=positive_int, default=1, help='Mac/MLX: 1; vLLM on one GPU: 48–96')
    a.add_argument('--json-schema', action='store_true', help='server-enforced JSON (vLLM yes, mlx_lm.server no)')
    a.add_argument('--thinking', choices=('off', 'on', 'omit'), default='off')
    a.add_argument('--top-p', type=probability, default=0.8)
    a.add_argument('--timeout', type=positive_float, default=900)
    a.add_argument('--max-retries', type=nonnegative_int, default=3)
    a.add_argument('--sample', type=nonnegative_int, default=0, help='only an evenly spaced sample of N requests per task')
    a.add_argument('--limit', type=nonnegative_int, help='at most N new requests per task')
    a.add_argument('--redo', action='store_true')
    a.add_argument('--retry-errors', action='store_true')
    a.add_argument('--gpu-price', type=nonnegative_float, default=0.0, help='$/hour, to print the running cost')
    a.add_argument('--progress-every', type=positive_int, default=20)
    a.set_defaults(func=cmd_ask)

    a = sub.add_parser('collect', help='check answers and write review.md / for-claude.md / summary.json')
    a.add_argument('job', type=Path)
    a.set_defaults(func=cmd_collect)

    a = sub.add_parser('status', help='read-only progress and failure diagnostics')
    a.add_argument('job', type=Path)
    a.add_argument('--task', choices=TASKS + ('all',), default='all')
    a.add_argument('--json', action='store_true', help='machine-readable report')
    a.add_argument('--details', action='store_true', help='include pending/error/stale request IDs and reasons')
    a.set_defaults(func=cmd_status)

    a = sub.add_parser('verify', help='require complete, current, valid answers for a task or sample')
    a.add_argument('job', type=Path)
    a.add_argument('--task', choices=TASKS + ('all',), default='all')
    a.add_argument('--sample', type=nonnegative_int, default=0)
    a.set_defaults(func=cmd_verify)

    a = sub.add_parser('apply', help='polish: apply ticked revisions to nt.tex (never modifies the input)')
    a.add_argument('job', type=Path)
    a.add_argument('--tex', type=Path, required=True)
    a.add_argument('--out', type=Path, help='also publish the verified result here, e.g. ../branch2.tex (never overwritten '
                                            'without --force: the triage/refs fixes are made in that file afterwards)')
    a.add_argument('--force', action='store_true', help='with --out: replace an existing file')
    a.add_argument('--accept-clean', action='store_true', help='also apply every revision that passed all checks')
    a.add_argument('--compile', action='store_true', help='run pdflatex twice on the result')
    a.set_defaults(func=cmd_apply)

    args = p.parse_args(argv)
    if getattr(args, 'base_url', None):
        args.base_url = args.base_url.rstrip('/')
    if hasattr(args, 'concurrency') and not 1 <= args.concurrency <= 256:
        p.error('--concurrency must be 1..256')
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
