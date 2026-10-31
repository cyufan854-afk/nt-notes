#!/usr/bin/env python3
"""双击运行：计算 27B 与 Muse Wonder 改动在最终稿里的留存率。

把下面的文件放进本文件夹（与本脚本同一层），然后双击本脚本：
  nt-final.tex     最终稿（合并后的版本）
  nt-branch2.tex   27B 的分支
  nt.tex           27B 开始改之前的主文件（没有就用 snapshots 里 Muse Wonder 之前的 branch1 代替，会提示）

结果写在本文件夹：retention.md（总表 + 按单元明细）和 retention.csv。
没有 nt-final.tex 时，用 snapshots 里的 v5 当最终稿做一次演示。
"""
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
SNAP = HERE / 'snapshots'
sys.path.insert(0, str(HERE))


def pause():
    try:
        input('\n完成。按回车关闭窗口…')
    except (EOFError, KeyboardInterrupt):
        pass


def main():
    import retention

    final = HERE / 'nt-final.tex'
    if not final.exists():
        final = SNAP / 'nt-branch1-v5.tex'
        print('【演示】没找到 nt-final.tex，先用 snapshots/nt-branch1-v5.tex 当最终稿。\n')

    args = ['--final', str(final)]
    branch2 = HERE / 'nt-branch2.tex'
    if branch2.exists():
        base = HERE / 'nt.tex'
        if not base.exists():
            base = SNAP / 'nt-branch1-muse-before.tex'
            print('【注意】没找到 nt.tex，27B 的基线暂用 Muse Wonder 之前的 branch1。'
                  '如果 branch2 是从另一版 nt.tex 开始改的，请把那一版以 nt.tex 放进来再跑。\n')
        args += ['--source', '27B', str(base), str(branch2)]
    else:
        print('【跳过 27B】没找到 nt-branch2.tex。\n')
    args += ['--source', 'Muse Wonder', str(SNAP / 'nt-branch1-muse-before.tex'), str(SNAP / 'nt-branch1-muse-after.tex'),
             '--out', str(HERE / 'retention')]
    retention.main(args)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        print('\n运行出错，上面是错误信息。')
    pause()
