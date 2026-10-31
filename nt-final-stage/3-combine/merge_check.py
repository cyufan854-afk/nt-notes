#!/usr/bin/env python3
"""Helpers for the agentic three-way merge of step 3. Nothing here merges anything.

  plan    list every unit (a theorem/definition with its proofs, or the prose under a heading) and which side changed
          it relative to the common ancestor, plus the map from baseline labels to branch1 labels (branch1 may have
          added numbered environments and renumbered the labels after them; branch2 keeps baseline's labels)
  verify  check final.tex against branch1: the same labels in the same order, the same numbered environments,
          every \\ref resolvable, no conflict markers, optionally a full latexmk compile

  python3 merge_check.py plan   [--root ..] [--out merge-plan.md]
  python3 merge_check.py verify [--root ..] [--compile]

Standard library only; Python 3.10+.
"""
import argparse
import difflib
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import retention  # noqa: E402  (unit boundaries are the same as in the retention report)

NUMBERED = ('theorem', 'definition')
LABEL = re.compile(r'\\label\{([^}]+)\}')
REF = re.compile(r'\\(?:ref|eqref|cref|Cref|autoref|pageref)\*?\{([^}]+)\}')
ENV = re.compile(r'\\begin\{(' + '|'.join(NUMBERED) + r')\}(.*?)\\end\{\1\}', re.S)
MARKER = re.compile(r'^[ \t]*(?:<{7}|={7}|>{7}|\|{7})(?:\s|$)', re.M)


def read(path):
    return Path(path).read_bytes().decode('utf-8')


def norm(text):
    return ' '.join(text.split())


def numbered(text):
    """[(kind, label or None, statement without its label)] in document order."""
    out = []
    for m in ENV.finditer(text):
        label = LABEL.search(m.group(2))
        out.append((m.group(1), label.group(1) if label else None, norm(LABEL.sub('', m.group(2)))))
    return out


def _group(label):
    """'def:5.7.1' -> ('def', '5.7'): labels are numbered within a subsection."""
    m = re.fullmatch(r'([A-Za-z]+):(.*)\.(\d+)', label or '')
    return (m.group(1), m.group(2)) if m else (label, '')


TITLE = re.compile(r'^\[([^\]]*)\]')


def similarity(x, y):
    """Text similarity of two statements; an equal title ([name] right after \\begin) is decisive, a different one
    counts against (a statement split in two keeps its title on the part that is still the same notion)."""
    ratio = difflib.SequenceMatcher(None, x, y, autojunk=False).ratio()
    tx, ty = TITLE.match(x), TITLE.match(y)
    if tx and ty:
        return 1.0 + ratio if norm(tx.group(1)).lower() == norm(ty.group(1)).lower() else 0.5 * ratio
    return ratio


def label_map(old_text, new_text):
    """{old label: new label} for numbered environments, aligned by content inside each (kind, subsection) group.

    Unchanged order is assumed (environments are only inserted or deleted, never moved); within a group the
    alignment maximises the summed text similarity (Needleman-Wunsch with zero gap cost)."""
    def groups(text):
        g = {}
        for kind, label, body in numbered(text):
            if label:
                g.setdefault((kind,) + _group(label), []).append((label, body))
        return g
    old, new = groups(old_text), groups(new_text)
    out = {}
    for key in old:
        a, b = old[key], new.get(key, [])
        n, m = len(a), len(b)
        sims = [[similarity(x[1], y[1]) for y in b] for x in a]
        score = [[0.0] * (m + 1) for _ in range(n + 1)]
        for i in range(n - 1, -1, -1):
            for j in range(m - 1, -1, -1):
                sim = sims[i][j]
                score[i][j] = max(score[i + 1][j], score[i][j + 1], sim + score[i + 1][j + 1] if sim >= 0.5 else 0.0)
        i = j = 0
        while i < n and j < m:
            sim = sims[i][j]
            if sim >= 0.5 and abs(score[i][j] - (sim + score[i + 1][j + 1])) < 1e-12:
                out[a[i][0]] = b[j][0]
                i, j = i + 1, j + 1
            elif score[i][j] == score[i + 1][j]:
                i += 1
            else:
                j += 1
    return out


def units(text):
    """{unit id: normalised text} with retention's unit boundaries (the preamble is its own unit)."""
    starts, ids = retention.unit_index(text)
    end = text.find('\\end{document}')
    bounds = starts[1:] + [end if end >= 0 else len(text)]
    out = {}
    for uid, a, b in zip(ids, starts, bounds):
        out[uid] = out.get(uid, '') + norm(text[a:b])
    return out


def plan(base, b1, b2):
    """Rows (branch1 id, baseline id, changed in branch1, changed in branch2) and the label maps."""
    m1 = label_map(base, b1)
    m2 = label_map(base, b2)
    inv1 = {v: k for k, v in m1.items()}
    ub, u1, u2 = units(base), units(b1), units(b2)
    rows = []
    for uid in u1:
        old = inv1.get(uid, uid if uid not in m1 or m1.get(uid) == uid else None)
        if old is None or old not in ub:
            rows.append({'unit': uid, 'baseline': None, 'branch1': True, 'branch2': None, 'note': 'branch1 新增'})
            continue
        other = m2.get(old, old)
        t2 = u2.get(other)
        rows.append({'unit': uid, 'baseline': old, 'branch1': u1[uid] != ub[old],
                     'branch2': None if t2 is None else t2 != ub[old],
                     'note': '' if t2 is not None else 'branch2 里找不到这个单元'})
    renamed = {k: v for k, v in m1.items() if k != v}
    lost1 = sorted({lab for _, lab, _ in numbered(base) if lab} - set(m1))
    lost2 = sorted(set(LABEL.findall(base)) - set(LABEL.findall(b2)))
    return rows, {'renamed_in_branch1': renamed, 'baseline_labels_not_in_branch1': lost1,
                  'baseline_labels_not_in_branch2': lost2, 'branch2_renamed': {k: v for k, v in m2.items() if k != v}}


def write_plan(rows, maps, out):
    both = [r for r in rows if r['branch1'] and r['branch2']]
    lines = ['# 合并计划（由 merge_check.py plan 生成，只列信息，不做合并）', '',
             f'单元 {len(rows)} 个：只有 branch1 改过 {sum(1 for r in rows if r["branch1"] and not r["branch2"])}，'
             f'只有 branch2 改过 {sum(1 for r in rows if r["branch2"] and not r["branch1"])}，'
             f'两边都改过 {len(both)}，都没改 {sum(1 for r in rows if not r["branch1"] and r["branch2"] is False)}。', '',
             '## label 对照（baseline → branch1）', '']
    if maps['renamed_in_branch1']:
        lines += ['branch1 新增了带编号的环境，后面的 label 顺延。从 branch2 搬文字时，凡是引用左边 label 的地方要改成右边：', '']
        lines += [f'- `{a}` → `{b}`' for a, b in sorted(maps['renamed_in_branch1'].items())]
    else:
        lines.append('baseline 与 branch1 的 label 一一相同，不用改引用。')
    if maps['baseline_labels_not_in_branch1']:
        lines += ['', '在 branch1 里找不到对应环境的 baseline label（要人工确认）：' + '、'.join(f'`{x}`' for x in maps['baseline_labels_not_in_branch1'])]
    if maps['baseline_labels_not_in_branch2'] or maps['branch2_renamed']:
        lines += ['', '⚠️ branch2 的 label 与 baseline 不一致（它本不该增删带编号的环境）：'
                  f'缺 {maps["baseline_labels_not_in_branch2"]}，改名 {maps["branch2_renamed"]}']
    lines += ['', '## 单元一览', '', '| 单元（branch1） | baseline 中 | branch1 改了 | branch2 改了 | 备注 |', '|---|---|---|---|---|']
    mark = {True: '是', False: '', None: '—'}
    for r in rows:
        lines.append(f'| {r["unit"]} | {r["baseline"] or "—"} | {mark[r["branch1"]]} | {mark[r["branch2"]]} | {r["note"]} |')
    Path(out).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return len(both)


def verify(final, b1, compile_cmd=None):
    """List of problems with final.tex (empty: all checks passed)."""
    problems = []
    for m in MARKER.finditer(final):
        line = final.count('\n', 0, m.start()) + 1
        problems.append(f'第 {line} 行有合并冲突标记')
    l_final, l_b1 = LABEL.findall(final), LABEL.findall(b1)
    if l_final != l_b1:
        missing = [x for x in l_b1 if x not in l_final]
        extra = [x for x in l_final if x not in l_b1]
        problems.append('label 与 branch1 不同' + (f'；缺 {missing[:8]}' if missing else '') + (f'；多 {extra[:8]}' if extra else '')
                        + ('' if missing or extra else '；顺序不同'))
    e_final = [(k, lab) for k, lab, _ in numbered(final)]
    e_b1 = [(k, lab) for k, lab, _ in numbered(b1)]
    if e_final != e_b1:
        problems.append(f'带编号的环境与 branch1 不同（final {len(e_final)} 个，branch1 {len(e_b1)} 个）：不能增删或调换 theorem/definition')
    body = final[final.find('\\begin{document}'):]
    begins = re.findall(r'\\begin\{([A-Za-z*]+)\}', body)
    ends = re.findall(r'\\end\{([A-Za-z*]+)\}', body)
    for env in sorted(set(begins) | set(ends)):
        if begins.count(env) != ends.count(env):
            problems.append(f'环境 {env} 的 \\begin 与 \\end 数目不同（{begins.count(env)} / {ends.count(env)}）')
    labels = set(l_final)
    dangling = sorted({r.strip() for m in REF.finditer(final) for r in m.group(1).split(',') if r.strip() and r.strip() not in labels})
    if dangling:
        problems.append(f'引用了不存在的 label：{dangling[:10]}')
    pre_f, pre_b = final[:final.find('\\begin{document}')], b1[:b1.find('\\begin{document}')]
    if pre_f != pre_b:
        problems.append('导言区与 branch1 不同（若是有意的修改请在 merge-log.md 写明理由）')
    if compile_cmd:
        problems += compile_problems(final, compile_cmd)
    return problems


def compile_problems(text, cmd):
    if shutil.which(cmd[0]) is None:
        return [f'找不到 {cmd[0]}，没有编译']
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / 'final.tex'
        src.write_text(text, encoding='utf-8')
        try:
            proc = subprocess.run(cmd + [src.name], cwd=d, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1800)
        except subprocess.TimeoutExpired:
            return ['编译超时']
        log = (Path(d) / 'final.log').read_text(encoding='utf-8', errors='replace') if (Path(d) / 'final.log').exists() else ''
        aux = (Path(d) / 'final.aux').read_text(encoding='utf-8', errors='replace') if (Path(d) / 'final.aux').exists() else ''
        out = []
        if proc.returncode:
            out.append(f'编译失败（退出码 {proc.returncode}）：' + '; '.join(l for l in log.splitlines() if l.startswith('! '))[:400])
        undefined = sorted(set(re.findall(r"Reference `([^']*)' on page \S+ undefined", log)))
        multiply = sorted(set(re.findall(r"Label `([^']*)' multiply defined", log)))
        mismatch = [f'{m.group(1)}→{m.group(2)}' for m in re.finditer(r'\\newlabel\{(?:thm|def):([\d.]+)\}\{\{([^}]*)\}', aux)
                    if m.group(1) != m.group(2)]
        if undefined:
            out.append(f'未定义引用 {undefined[:10]}')
        if multiply:
            out.append(f'重复 label {multiply[:10]}')
        if mismatch:
            out.append(f'label 名与实际编号不符 {mismatch[:10]}')
        return out


def main(argv=None):
    p = argparse.ArgumentParser(description='第 3 步合并的辅助检查（不做合并）')
    p.add_argument('action', choices=('plan', 'verify'))
    p.add_argument('--root', default=str(HERE.parent), help='放 baseline.tex / branch1.tex / branch2.tex / final.tex 的主文件夹')
    p.add_argument('--out', default=str(HERE / 'merge-plan.md'))
    p.add_argument('--compile', action='store_true', help='verify 时另用 latexmk -pdf 编译一遍')
    a = p.parse_args(argv)
    root = Path(a.root)
    if a.action == 'plan':
        rows, maps = plan(read(root / 'baseline.tex'), read(root / 'branch1.tex'), read(root / 'branch2.tex'))
        both = write_plan(rows, maps, a.out)
        print(f'{len(rows)} 个单元，两边都改过 {both} 个；label 改名 {len(maps["renamed_in_branch1"])} 处。详见 {a.out}')
        return 0
    cmd = ['latexmk', '-pdf', '-interaction=nonstopmode', '-halt-on-error'] if a.compile else None
    problems = verify(read(root / 'final.tex'), read(root / 'branch1.tex'), cmd)
    for x in problems:
        print('✗ ' + x)
    print('全部检查通过' if not problems else f'{len(problems)} 项没通过')
    return 0 if not problems else 2


if __name__ == '__main__':
    sys.exit(main())
