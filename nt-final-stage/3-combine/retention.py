#!/usr/bin/env python3
"""How many of each source's edits survive in a final LaTeX file.

For every source, BEFORE -> AFTER is diffed into hunks: one hunk is one contiguous change
at word level (whitespace and line wrapping are ignored).  Each hunk is then classified
against FINAL:

  kept       the hunk's AFTER text is still in FINAL, unchanged and uninterrupted
  reverted   the hunk's BEFORE text is back in FINAL (the change was undone)
  rewritten  neither: the place was changed again in some other way

Counts are per hunk, not per character, so one rewritten sentence weighs the same as a
one-word fix.  Hunks are assigned to units (a theorem/definition with its proofs, or the
prose under a heading) of the AFTER snapshot, labelled by the unit's \\label.

Usage:
  python3 retention.py --final final.tex \\
      --source 27B nt.tex branch2.tex \\
      --source "Muse Wonder" before-muse.tex after-muse.tex \\
      --out retention            # writes retention.md and retention.csv

Python 3.10+, standard library only.
"""
import argparse
import bisect
import csv
import difflib
import re
import sys
from pathlib import Path

TOKEN = re.compile(r'\S+')
UNIT_ENVS = ('theorem', 'definition', 'lemma', 'proposition', 'corollary', 'remark', 'example')
STATUS_ZH = {'kept': '保留', 'reverted': '撤回', 'rewritten': '改写'}


# ---------------------------------------------------------------- alignment

def tokenize(text):
    return [(m.group(), m.start(), m.end()) for m in TOKEN.finditer(text)]


def segments(text, toks):
    """Split into segments at blank lines and at \\begin/\\end lines.

    Segments are compared with whitespace normalised, so re-wrapping a paragraph only
    affects that paragraph.  Returns (normalised strings, first-token index per segment
    plus a final sentinel)."""
    cuts = [0]
    for m in re.finditer(r'\n[ \t]*\n|\n(?=[ \t]*\\(?:begin|end)\{)', text):
        cuts.append(m.end())
    cuts.append(len(text) + 1)
    starts = [t[1] for t in toks]
    norm, first = [], []
    for a, b in zip(cuts, cuts[1:]):
        i, j = bisect.bisect_left(starts, a), bisect.bisect_left(starts, b)
        if i == j:
            continue
        norm.append(' '.join(t[0] for t in toks[i:j]))
        first.append(i)
    first.append(len(toks))
    return norm, first


def align(a_text, b_text):
    """Token-level opcodes from a to b: segment-level diff, then word-level inside changes."""
    at, bt = tokenize(a_text), tokenize(b_text)
    a_seg, a_first = segments(a_text, at)
    b_seg, b_first = segments(b_text, bt)
    ops = []
    outer = difflib.SequenceMatcher(None, a_seg, b_seg, autojunk=False)
    for tag, i1, i2, j1, j2 in outer.get_opcodes():
        ta1, ta2, tb1, tb2 = a_first[i1], a_first[i2], b_first[j1], b_first[j2]
        if tag == 'equal':
            ops.append(('equal', ta1, ta2, tb1, tb2))
            continue
        inner = difflib.SequenceMatcher(None, [t[0] for t in at[ta1:ta2]], [t[0] for t in bt[tb1:tb2]], autojunk=False)
        for t, x1, x2, y1, y2 in inner.get_opcodes():
            ops.append((t, ta1 + x1, ta1 + x2, tb1 + y1, tb1 + y2))
    amap = [-1] * len(at)
    for tag, x1, x2, y1, y2 in ops:
        if tag == 'equal':
            for k in range(x2 - x1):
                amap[x1 + k] = y1 + k
    return at, bt, ops, amap


def hunks(ops, gap):
    """Non-equal opcodes, merged when separated by at most ``gap`` unchanged tokens."""
    out = []
    for tag, a1, a2, b1, b2 in ops:
        if tag == 'equal':
            continue
        if out and a1 - out[-1][1] <= gap and b1 - out[-1][3] <= gap:
            out[-1] = (out[-1][0], a2, out[-1][2], b2)
        else:
            out.append((a1, a2, b1, b2))
    return out  # (before_start, before_end, after_start, after_end)


def intact(amap, start, end, n_src):
    """Tokens [start, end) of the source all survive, in order, with nothing inserted between.

    For an empty span this checks the gap between tokens start-1 and start instead."""
    if end > start:
        idx = list(range(start, end))
    else:
        idx = [i for i in (start - 1, start) if 0 <= i < n_src]
        if not idx:
            return True
    if any(amap[i] < 0 for i in idx):
        return False
    return all(amap[i + 1] == amap[i] + 1 for i in idx[:-1])


# ---------------------------------------------------------------- units

def unit_index(text):
    """(start offsets, ids) of units in ``text``; anything before \\begin{document} is 'preamble'."""
    begin = text.find('\\begin{document}')
    envs = '|'.join(UNIT_ENVS)
    starts, ids = [0], ['preamble']
    if begin < 0:
        return starts, ids
    pat = re.compile(r'\\begin\{(' + envs + r')\}|\\(?:sub)?section\*?\s*\{([^}]*)\}')
    pending_heading = None
    for m in pat.finditer(text, begin):
        if m.group(1):
            close = text.find('\\end{' + m.group(1) + '}', m.end())
            label = re.compile(r'\\label\{([^}]+)\}').search(text, m.end(), close if close > 0 else len(text))
            uid = label.group(1) if label else (pending_heading or f'{m.group(1)}@{text.count(chr(10), 0, m.start()) + 1}')
            start = pending_start if pending_heading is not None else m.start()
            pending_heading = None
        else:
            # A heading starts a prose unit; if a unit environment follows directly, the
            # heading is folded into that unit instead.
            pending_heading = 'sec:' + re.sub(r'[^A-Za-z0-9]+', '-', m.group(2)).strip('-').lower()[:40]
            pending_start = m.start()
            nxt = pat.search(text, m.end())
            between = text[m.end(): nxt.start() if nxt else len(text)]
            if len(re.findall(r'[A-Za-z]', re.sub(r'\\[A-Za-z@]+\*?(?:\{[^{}]*\})*', ' ', between))) >= 40:
                uid, start, pending_heading = pending_heading, m.start(), None
            else:
                continue
        starts.append(start)
        ids.append(uid)
    return starts, ids


def unit_of(units, offset):
    starts, ids = units
    return ids[max(0, bisect.bisect_right(starts, offset) - 1)]


# ---------------------------------------------------------------- analysis

def clip(text, limit=240):
    text = ' '.join(text.split())
    return text if len(text) <= limit else text[:limit] + ' …'


def span_text(text, toks, a, b):
    if b <= a:
        return ''
    return text[toks[a][1]:toks[b - 1][2]]


def final_excerpt(after_text, ft, f_text, af_map, a1, a2, reach=60):
    """FINAL text between the nearest surviving tokens around after-span [a1, a2)."""
    left = next((i for i in range(a1 - 1, max(-1, a1 - 1 - reach), -1) if af_map[i] >= 0), None)
    right = next((i for i in range(a2, min(len(af_map), a2 + reach)) if af_map[i] >= 0), None)
    lo = af_map[left] + 1 if left is not None else max(0, (af_map[right] if right is not None else 0) - 8)
    hi = af_map[right] if right is not None else min(len(ft), lo + 8)
    return span_text(f_text, ft, lo, hi)


def analyse(name, before_text, after_text, final_text, gap):
    bt, at, ops, _ = align(before_text, after_text)
    _, ft, _, af_map = align(after_text, final_text)
    _, _, _, bf_map = align(before_text, final_text)
    units = unit_index(after_text)
    rows = []
    for n, (b1, b2, a1, a2) in enumerate(hunks(ops, gap), 1):
        if intact(af_map, a1, a2, len(at)):
            status = 'kept'
        elif intact(bf_map, b1, b2, len(bt)):
            status = 'reverted'
        else:
            status = 'rewritten'
        anchor = at[a1][1] if a1 < len(at) else (at[-1][2] if at else 0)
        rows.append({
            'source': name, 'hunk': n, 'status': status,
            'unit': unit_of(units, anchor),
            'after_line': after_text.count('\n', 0, anchor) + 1,
            'before': span_text(before_text, bt, b1, b2),
            'after': span_text(after_text, at, a1, a2),
            'final': '' if status == 'kept' else final_excerpt(after_text, ft, final_text, af_map, a1, a2),
        })
    return rows


def summarise(rows):
    total = len(rows)
    counts = {s: sum(r['status'] == s for r in rows) for s in STATUS_ZH}
    return total, counts


def pct(k, n):
    return f'{k} ({100 * k / n:.1f}%)' if n else '0'


def write_reports(results, final_path, gap, out):
    lines = ['# 改动留存率', f'最终稿：`{final_path}`', '',
             f'粒度：按改动块计。一块 = 一处连续的改动（按词比较，忽略空白和换行；相隔不超过 {gap} 个未改动词的改动合并为一块）。',
             '保留 = 改后的文字原样、连续地出现在最终稿的对应位置；撤回 = 改前的文字回到了那里；改写 = 两者都不是。', '',
             '| 来源 | 改动块 | 保留 | 撤回 | 改写 |', '|---|---|---|---|---|']
    for name, rows in results:
        total, c = summarise(rows)
        lines.append(f'| {name} | {total} | {pct(c["kept"], total)} | {pct(c["reverted"], total)} | {pct(c["rewritten"], total)} |')
    lines += ['', '## 按单元汇总', '', '| 单元 | ' + ' | '.join(f'{n}（保留/撤回/改写）' for n, _ in results) + ' |',
              '|---|' + '---|' * len(results)]
    order, by_unit = [], {}
    for name, rows in results:
        for r in rows:
            if r['unit'] not in by_unit:
                order.append(r['unit'])
                by_unit[r['unit']] = []
            by_unit[r['unit']].append(r)
    for unit in order:
        cells = []
        for name, _ in results:
            rs = [r for r in by_unit[unit] if r['source'] == name]
            cells.append('—' if not rs else '/'.join(str(sum(r['status'] == s for r in rs)) for s in STATUS_ZH))
        lines.append(f'| {unit} | ' + ' | '.join(cells) + ' |')
    lines += ['', '## 明细（按单元）']
    for unit in order:
        lines += ['', f'### {unit}']
        for r in by_unit[unit]:
            item = (f'- **{r["source"]} #{r["hunk"]}**（第 {r["after_line"]} 行）{STATUS_ZH[r["status"]]}：'
                    f'`{clip(r["before"]) or "（无）"}` → `{clip(r["after"]) or "（删除）"}`')
            if r['status'] != 'kept':
                item += f'；最终稿此处：`{clip(r["final"]) or "（空）"}`'
            lines.append(item)
    Path(out + '.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    with open(out + '.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['source', 'hunk', 'unit', 'after_line', 'status', 'before', 'after', 'final'])
        w.writeheader()
        for _, rows in results:
            for r in rows:
                w.writerow({**r, 'status': STATUS_ZH[r['status']]})


def main(argv=None):
    p = argparse.ArgumentParser(description='计算各来源改动在最终稿中的留存率（按改动块）')
    p.add_argument('--final', required=True, help='最终稿')
    p.add_argument('--source', nargs=3, action='append', required=True, metavar=('NAME', 'BEFORE', 'AFTER'),
                   help='来源名称及其改动前、改动后两份快照；可重复')
    p.add_argument('--gap', type=int, default=2, help='相隔不超过多少个未改动词的改动合并为一块（默认 2）')
    p.add_argument('--out', default='retention', help='输出文件名前缀（写 .md 和 .csv）')
    args = p.parse_args(argv)
    if args.gap < 0:
        p.error('--gap 不能为负')
    read = lambda path: Path(path).read_bytes().decode('utf-8')
    final = read(args.final)
    results = []
    for name, before, after in args.source:
        rows = analyse(name, read(before), read(after), final, args.gap)
        results.append((name, rows))
        total, c = summarise(rows)
        print(f'{name}: {total} 处改动；保留 {pct(c["kept"], total)}，撤回 {pct(c["reverted"], total)}，改写 {pct(c["rewritten"], total)}')
    write_reports(results, args.final, args.gap, args.out)
    print(f'明细：{args.out}.md，{args.out}.csv')
    return 0


if __name__ == '__main__':
    sys.exit(main())
