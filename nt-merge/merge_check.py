#!/usr/bin/env python3
"""Helpers for the agentic three-way merge of step 3. Nothing here merges anything.

  plan    list every unit (a theorem/definition with its proofs, or the prose under a heading) and which side changed
          it relative to the common ancestor, plus the map from baseline labels to branch1 labels (branch1 may have
          added numbered environments and renumbered the labels after them; branch2 keeps baseline's labels)
  verify  check final.tex against branch1: the same labels in the same order, the same numbered environments,
          every \\ref resolvable, no conflict markers, optionally a full latexmk compile

  python3 merge_check.py plan   [--root .] [--out merge-plan.md]
  python3 merge_check.py verify [--root .] [--compile]
  python3 merge_check.py audit  [--root .] [--out merge-audit.md]     (reads merge-log.md next to this script)

--root defaults to this script's own folder: everything lives in one folder.

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

from retention import NUMBERED, LABEL, ENV, numbered, label_map, similarity, rename_labels  # noqa: E402  (shared with the retention report)
REF = re.compile(r'\\(?:ref|eqref|cref|Cref|autoref|pageref)\*?\{([^}]+)\}')
MARKER = re.compile(r'^[ \t]*(?:<{7}|={7}|>{7}|\|{7})(?:\s|$)', re.M)


def read(path):
    return Path(path).read_bytes().decode('utf-8')


def norm(text):
    return ' '.join(text.split())


def mentioned_in(uid, text):
    """True if the unit id occurs in ``text`` as a whole id: thm:2.2.10 does not count as a mention of thm:2.2.1."""
    return re.search(r'(?<![A-Za-z0-9_-])' + re.escape(uid) + r'(?![A-Za-z0-9_-])(?!\.\d)', text) is not None


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


def audit(base, b1, b2, final, log_text=None):
    """Where each unit of final.tex comes from, and whether merge-log.md mentions every decision that needs a word.

    Each side is first renamed to final.tex's labels. A unit of final.tex equals branch1's, branch2's, the baseline's
    (both sides rolled back), or none of them (combined or new text by the merging model). It needs an explanation in
    the log when it is new text, or when it rolls back a change that only one side made."""
    def renamed(text):
        return rename_labels(text, {k: v for k, v in label_map(text, final).items() if k != v})
    ub, u1, u2, uf = units(renamed(base)), units(b1), units(renamed(b2)), units(final)
    rows = []
    for uid, text in uf.items():
        sides = {'branch1': u1.get(uid), 'branch2': u2.get(uid), 'baseline': ub.get(uid)}
        same = [k for k in ('branch1', 'branch2', 'baseline') if sides[k] is not None and sides[k] == text]
        changed1 = sides['branch1'] is not None and sides['baseline'] is not None and sides['branch1'] != sides['baseline']
        changed2 = sides['branch2'] is not None and sides['baseline'] is not None and sides['branch2'] != sides['baseline']
        source = same[0] if same else 'new'
        need = None
        if source == 'new':
            closest = max((k for k in ('branch1', 'branch2') if sides[k]), key=lambda k: similarity(sides[k], text), default=None)
            need = '新写或融合的文字' + (f'（最接近 {closest}）' if closest else '')
        elif changed1 != changed2 and source in ('baseline', 'branch2' if changed1 else 'branch1'):
            need = '回滚了只有 ' + ('branch1' if changed1 else 'branch2') + ' 做过的修改'
        elif changed1 and changed2 and source == 'baseline':
            need = '两边的修改都回滚了'
        mentioned = None if log_text is None or need is None else mentioned_in(uid, log_text)
        rows.append({'unit': uid, 'source': '/'.join(same) if same else 'new', 'branch1_changed': changed1,
                     'branch2_changed': changed2, 'needs_note': need, 'in_log': mentioned})
    return rows


def write_audit(rows, out, log_present):
    need = [r for r in rows if r['needs_note']]
    missing = [r for r in need if r['in_log'] is False]
    count = {}
    for r in rows:
        count[r['source']] = count.get(r['source'], 0) + 1
    lines = ['# 合并核对（merge_check.py audit）', '',
             '最终稿每个单元取自哪边：' + '，'.join(f'{k} {v}' for k, v in sorted(count.items())) + '。',
             f'需要在 merge-log.md 里说明的单元 {len(need)} 个' + (f'，其中 {len(missing)} 个日志里没有提到。' if log_present else '（还没有 merge-log.md）。'),
             '', '| 单元 | 取自 | branch1 改过 | branch2 改过 | 需要说明 | 日志里有 |', '|---|---|---|---|---|---|']
    mark = {True: '是', False: '', None: '—'}
    for r in rows:
        if r['needs_note'] or r['source'] == 'new':
            lines.append(f'| {r["unit"]} | {r["source"]} | {mark[r["branch1_changed"]]} | {mark[r["branch2_changed"]]} | '
                         f'{r["needs_note"] or ""} | {"—" if r["in_log"] is None else ("有" if r["in_log"] else "**没有**")} |')
    Path(out).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return need, missing


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
    p.add_argument('action', choices=('plan', 'audit', 'verify'))
    p.add_argument('--root', default=str(HERE), help='放 baseline.tex / branch1.tex / branch2.tex / final.tex 的文件夹（默认就是本文件夹）')
    p.add_argument('--out', help='plan: merge-plan.md；audit: merge-audit.md（默认都在本文件夹）')
    p.add_argument('--compile', action='store_true', help='verify 时另用 latexmk -pdf 编译一遍')
    a = p.parse_args(argv)
    root = Path(a.root)
    if a.action == 'plan':
        out = a.out or str(HERE / 'merge-plan.md')
        rows, maps = plan(read(root / 'baseline.tex'), read(root / 'branch1.tex'), read(root / 'branch2.tex'))
        both = write_plan(rows, maps, out)
        print(f'{len(rows)} 个单元，两边都改过 {both} 个；label 改名 {len(maps["renamed_in_branch1"])} 处。详见 {out}')
        return 0
    if a.action == 'audit':
        out = a.out or str(HERE / 'merge-audit.md')
        log = HERE / 'merge-log.md'
        rows = audit(read(root / 'baseline.tex'), read(root / 'branch1.tex'), read(root / 'branch2.tex'), read(root / 'final.tex'),
                     log.read_text(encoding='utf-8') if log.exists() else None)
        need, missing = write_audit(rows, out, log.exists())
        print(f'需要说明的单元 {len(need)} 个，日志里没提到的 {len(missing)} 个' + ('' if log.exists() else '（还没有 merge-log.md）') + f'。详见 {out}')
        for r in missing:
            print(f'✗ {r["unit"]}：{r["needs_note"]}，merge-log.md 里没有提到')
        return 0 if log.exists() and not missing else 2
    cmd = ['latexmk', '-pdf', '-interaction=nonstopmode', '-halt-on-error'] if a.compile else None
    problems = verify(read(root / 'final.tex'), read(root / 'branch1.tex'), cmd)
    for x in problems:
        print('✗ ' + x)
    print('全部检查通过' if not problems else f'{len(problems)} 项没通过')
    return 0 if not problems else 2


if __name__ == '__main__':
    sys.exit(main())
