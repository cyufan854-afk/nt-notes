#!/usr/bin/env python3
"""双击运行：计算 27B 与 Muse Wonder 改动在最终稿里的留存率。

文件都在上一层的主文件夹 nt-final-stage/（本脚本在 3-combine/ 里）：
  baseline.tex   27B 的基线，固定用它（branch1 与 branch2 的共同祖先）；运行时校验 SHA-256，不对就停下
  branch2.tex    第 2 步的产物（27B 的分支）；没有就跳过 27B 这一组
  final.tex      第 3 步合并出的最终稿；没有就用 branch1.tex 当最终稿做一次演示

Muse Wonder 那一组用本文件夹 snapshots/ 里的 muse-before → muse-after。
结果写在本文件夹：retention.md（总表 + 按单元明细）和 retention.csv。

也可以在终端指定文件：python3 run_retention.py --final 某稿.tex --branch2 某分支.tex
"""
import argparse
import hashlib
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SNAP = HERE / 'snapshots'
# baseline.tex 是数据，内容固定（= nt27b 1.1.1 的 data/nt.tex）。不一致就说明主文件夹里的 baseline 被改过或换错了。
BASELINE_SHA256 = '8684a76e6014d66bd520f5b65f12acdb3e24157cfa5f0a227025963b6cb84dd5'
MUSE_BEFORE = 'nt-branch1-muse-before.tex'
MUSE_AFTER = 'nt-branch1-muse-after.tex'
sys.path.insert(0, str(HERE))


class SetupError(Exception):
    """A missing or wrong input file; the message says what to do."""


def pause():
    try:
        input('\n完成。按回车关闭窗口…')
    except (EOFError, KeyboardInterrupt):
        pass


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plan(root=ROOT, snapshots=SNAP, out=HERE / 'retention', final=None, branch2=None, expected_sha=BASELINE_SHA256):
    """The argument list for retention.main, plus notes to print. Raises SetupError for a missing or wrong baseline."""
    root, snapshots = Path(root), Path(snapshots)
    notes = []
    final = Path(final) if final else root / 'final.tex'
    if not final.exists():
        if final != root / 'final.tex':
            raise SetupError(f'找不到最终稿 {final}')
        final = root / 'branch1.tex'
        if not final.exists():
            raise SetupError(f'主文件夹 {root} 里既没有 final.tex 也没有 branch1.tex')
        notes.append('【演示】没找到 final.tex（第 3 步的最终稿），先用 branch1.tex 当最终稿。')
    args = ['--final', str(final)]
    branch2 = Path(branch2) if branch2 else root / 'branch2.tex'
    if branch2.exists():
        base = root / 'baseline.tex'
        if not base.exists():
            raise SetupError(f'找不到 27B 的基线 {base}。27B 的改动只能相对 baseline.tex 计算，不用别的稿子代替。')
        digest = sha256(base)
        if expected_sha and digest != expected_sha:
            raise SetupError(f'{base} 的 SHA-256 是 {digest[:12]}…，应为 {expected_sha[:12]}…：baseline 被改过或换错了文件。'
                             '请换回原始的 baseline.tex 再运行。')
        args += ['--source', '27B', str(base), str(branch2)]
    else:
        notes.append(f'【跳过 27B】没找到 {branch2}。')
    for name in (MUSE_BEFORE, MUSE_AFTER):
        if not (snapshots / name).exists():
            raise SetupError(f'找不到快照 {snapshots / name}')
    args += ['--source', 'Muse Wonder', str(snapshots / MUSE_BEFORE), str(snapshots / MUSE_AFTER), '--out', str(out)]
    return args, notes


def main(argv=None):
    import retention
    p = argparse.ArgumentParser(description='27B 与 Muse Wonder 改动在最终稿里的留存率（默认读主文件夹的 final.tex、branch2.tex、baseline.tex）')
    p.add_argument('--final', help='最终稿（默认 ../final.tex）')
    p.add_argument('--branch2', help='27B 的分支（默认 ../branch2.tex）')
    p.add_argument('--out', default=str(HERE / 'retention'), help='输出文件名前缀')
    a = p.parse_args(argv)
    args, notes = plan(final=a.final, branch2=a.branch2, out=a.out)
    for note in notes:
        print(note + '\n')
    return retention.main(args)


if __name__ == '__main__':
    code = 1
    try:
        code = main()
    except SetupError as error:
        print(f'没有运行：{error}')
    except Exception:
        traceback.print_exc()
        print('\n运行出错，上面是错误信息。')
    pause()
    sys.exit(code)
