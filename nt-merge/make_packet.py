#!/usr/bin/env python3
"""Paste-ready material for step 4 (cross review of the merge): the prompt plus the manuscripts, in one file.

    python3 make_packet.py              writes cross-review-full.md and cross-review-compact[-NN].md here

Everything lives in one folder: this script, merge_check.py, retention.py, the four manuscripts and step 3's notes.

  cross-review-full.md       CROSS_REVIEW_PROMPT.md + the step-3 notes (merge-log.md, escalate.md, progress.md; those
                             that exist) + the four manuscripts in full, each wrapped in
                             ===== 文件：… ===== lines that give its line count and last line (so truncation shows)
  cross-review-compact*.md   the prompt + the notes + only the units where the merge could have gone wrong (final differs
                             from both sides, both sides changed, a one-sided change rolled back, or listed in
                             escalate.md): final's text and three diffs (baseline->branch1, baseline->branch2,
                             branch1->final); the other units are listed by id.
                             Split into parts of at most --max-chars characters.

The four manuscripts are about 2.7 MB together (roughly 850k tokens): only a model with a context of about a million
tokens can take the full file. For a smaller context, use the compact parts. Standard library only.
"""
import argparse
import difflib
import hashlib
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import merge_check as mc  # noqa: E402
import retention  # noqa: E402

FILES = (('baseline.tex', '共同祖先'), ('branch1.tex', '作者一侧'), ('branch2.tex', '27B 一侧'), ('final.tex', '合并结果（审查对象）'))
# Step 3's notes, next to the manuscripts; included when present.
NOTES = (('merge-log.md', '合并说明，含疑难复核追加的结论'), ('escalate.md', '疑难单元清单与复核结论'),
         ('progress.md', '合并进度、约定、未决事项'))
ESCALATED = re.compile(r'^\s*-\s*\[([^\]]+)\]\s*单元\s*`?([^\s`·]+)', re.M)
CHARS_PER_TOKEN = 3.2


def escalated(text):
    """{unit id: status} from escalate.md (status: 待复核 / 维持 / 改写 / 交作者)."""
    return {uid: status for status, uid in ESCALATED.findall(text or '')}


def read_notes(root):
    """[(name, role, text)] for the step-3 notes that exist."""
    folder = Path(root)
    return [(name, role, (folder / name).read_text(encoding='utf-8')) for name, role in NOTES if (folder / name).exists()]


def wrap(name, text, role):
    lines = text.splitlines()
    last = next((l for l in reversed(lines) if l.strip()), '')
    sha = hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]
    return (f'\n===== 文件：{name}（{role}；{len(lines)} 行；最后一行「{last.strip()[:80]}」；SHA-256 {sha}…）=====\n'
            f'{text}\n===== 文件结束：{name} =====\n')


def raw_units(text):
    """{unit id: raw text} with the same unit boundaries and ids as merge_check / retention."""
    starts, ids = retention.unit_index(text)
    end = text.find('\\end{document}')
    bounds = starts[1:] + [end if end >= 0 else len(text)]
    out = {}
    for uid, a, b in zip(ids, starts, bounds):
        out[uid] = out.get(uid, '') + text[a:b]
    return out


def diff(a, b, name_a, name_b):
    lines = list(difflib.unified_diff((a or '').splitlines(), (b or '').splitlines(), name_a, name_b, n=1, lineterm=''))
    return '\n'.join(lines) if lines else '（无差异）'


def risky(row):
    return row['source'] == 'new' or bool(row['needs_note']) or (row['branch1_changed'] and row['branch2_changed'])


def compact_units(base, b1, b2, final, log=None, esc=None):
    """(detailed unit blocks, one-line summary groups) for the compact packet. ``esc``: escalated() of escalate.md."""
    def renamed(text):
        return retention.rename_labels(text, retention.label_mapping(text, final))
    esc = esc or {}
    rows = mc.audit(base, b1, b2, final, log)
    ub, u1, u2, uf = raw_units(renamed(base)), raw_units(b1), raw_units(renamed(b2)), raw_units(final)
    blocks, groups = [], {'final 与 branch1 相同，branch2 没改': [], 'final 取自 branch2，branch1 没改': [],
                          '三份都没改（或只有 label 改名）': [], '其他（final 与某一边相同）': []}
    for r in rows:
        uid = r['unit']
        if risky(r) or uid in esc:
            why = r['needs_note'] or ('两边都改过' if r['branch1_changed'] and r['branch2_changed'] else '列入疑难清单')
            parts = [f'\n##### 单元 {uid} · {why} · final 取自 {r["source"]}' + (f' · 日志里{"有" if r["in_log"] else "没有"}提到' if r['in_log'] is not None else '')
                     + (f' · 疑难清单：{esc[uid]}' if uid in esc else ''),
                     '\n--- final（全文）---\n' + uf.get(uid, '').strip('\n'),
                     '\n--- 差异：baseline → branch1 ---\n' + (diff(ub.get(uid), u1.get(uid), 'baseline', 'branch1') if uid in ub else '（baseline 里没有这个单元：branch1 新增）'),
                     '\n--- 差异：baseline → branch2 ---\n' + (diff(ub.get(uid), u2.get(uid), 'baseline', 'branch2') if uid in ub else '（baseline 里没有这个单元）'),
                     '\n--- 差异：branch1 → final ---\n' + diff(u1.get(uid), uf.get(uid), 'branch1', 'final')]
            blocks.append((uid, '\n'.join(parts) + '\n'))
        elif r['branch1_changed'] and not r['branch2_changed']:
            groups['final 与 branch1 相同，branch2 没改'].append(uid)
        elif r['branch2_changed'] and not r['branch1_changed']:
            groups['final 取自 branch2，branch1 没改'].append(uid)
        elif not r['branch1_changed'] and not r['branch2_changed']:
            groups['三份都没改（或只有 label 改名）'].append(uid)
        else:
            groups['其他（final 与某一边相同）'].append(uid)
    return blocks, groups


def build(root=HERE, out_dir=HERE, max_chars=350000, prompt_path=HERE / 'CROSS_REVIEW_PROMPT.md'):
    root, out_dir = Path(root), Path(out_dir)
    texts = {name: mc.read(root / name) for name, _ in FILES}
    prompt = Path(prompt_path).read_text(encoding='utf-8')
    notes = read_notes(root)
    log = next((text for name, _, text in notes if name == 'merge-log.md'), None)
    esc = escalated(next((text for name, _, text in notes if name == 'escalate.md'), ''))
    wrapped_notes = ''.join('\n' + wrap(name, text, role) for name, role, text in notes)
    written = []
    full = prompt + wrapped_notes + ''.join(wrap(name, texts[name], role) for name, role in FILES)
    path = out_dir / 'cross-review-full.md'
    path.write_text(full, encoding='utf-8')
    written.append(path)
    blocks, groups = compact_units(texts['baseline.tex'], texts['branch1.tex'], texts['branch2.tex'], texts['final.tex'], log, esc)
    summary = '\n'.join(f'- {title}（{len(ids)} 个）：' + ('、'.join(ids) if ids else '无') for title, ids in groups.items())
    head_extra = ('\n===== 材料包说明 =====\n这是材料包，不是 4 份全文：下面只有合并中有风险的单元（final 与两边都不同、两边都改过、回滚了只有一边做过的修改、列入疑难清单），'
                  '每个单元给 final 的全文和三段差异（-/+ 行，@@ 是位置）。其余单元只按取自哪边列出 id，不需要审查。'
                  '收到行请写“收到：材料包第 k/n 部分，单元 …”。\n' + wrapped_notes
                  + '\n===== 不在材料包里的单元 =====\n' + summary + '\n')
    for old in out_dir.glob('cross-review-compact*.md'):
        old.unlink()
    parts, current, size = [], [], 0
    budget = max(1, max_chars - len(prompt) - len(head_extra) - 2000)   # a unit larger than this gets a part of its own
    for uid, block in blocks:
        if current and size + len(block) > budget:
            parts.append(current)
            current, size = [], 0
        current.append((uid, block))
        size += len(block)
    if current or not parts:
        parts.append(current)
    for n, part in enumerate(parts, 1):
        name = 'cross-review-compact.md' if len(parts) == 1 else f'cross-review-compact-{n:02d}.md'
        ids = [uid for uid, _ in part]
        text = (prompt + head_extra + f'\n===== 材料包第 {n}/{len(parts)} 部分：{len(ids)} 个单元 =====\n'
                + ('本部分单元：' + '、'.join(ids) if ids else '（没有需要审查的单元）') + '\n'
                + ''.join(block for _, block in part) + f'\n===== 材料包第 {n}/{len(parts)} 部分结束 =====\n')
        (out_dir / name).write_text(text, encoding='utf-8')
        written.append(out_dir / name)
    return written, len(blocks)


def main(argv=None):
    ap = argparse.ArgumentParser(description='生成第 4 步交叉审查要粘贴的文件（prompt + 稿子）')
    ap.add_argument('--root', default=str(HERE), help='放 baseline / branch1 / branch2 / final 和第 3 步说明文件的文件夹（默认就是本文件夹）')
    ap.add_argument('--out', default=str(HERE), help='输出目录')
    ap.add_argument('--max-chars', type=int, default=350000, help='材料包每部分的字符上限（默认约 11 万 token）')
    a = ap.parse_args(argv)
    for name, _ in FILES:
        if not (Path(a.root) / name).exists():
            print(f'缺少 {Path(a.root) / name}：第 4 步要在第 3 步写出 final.tex 之后做')
            return 2
    written, risky_count = build(a.root, a.out, a.max_chars)
    for path in written:
        chars = len(path.read_text(encoding='utf-8'))
        print(f'{path.name}：{chars / 1e6:.2f}M 字符，约 {chars / CHARS_PER_TOKEN / 1000:.0f}k token')
    print(f'材料包里有风险的单元 {risky_count} 个。上下文约 100 万 token 的模型可以用 cross-review-full.md；'
          '较小的用 cross-review-compact*.md（多部分时每部分单独发、单独回复）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
