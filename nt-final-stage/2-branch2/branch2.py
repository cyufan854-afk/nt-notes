#!/usr/bin/env python3
"""Step 2 from start to finish: baseline.tex -> branch2.tex with the 27B, in stages that keep where each change came from.

    python3 branch2.py prepare                 Mac: build the 3090 requests from ../baseline.tex (polish, triage, refs)
    (RunPod)  MODEL=… MODEL_REVISION=… JOB=job-27b bash gpu/run_gpu.sh      all three tasks in one GPU session
    python3 branch2.py import results-….tgz    Mac: unpack the GPU results into the job directory (safely)
    python3 branch2.py status                  where things stand and what to do next
    python3 branch2.py next [--accept-clean] [--compile] [--done] [--force] [--accept-errors]

Stages (each a full manuscript in stages/, so that every change can be attributed):
  1-polish.tex   baseline + the polish revisions you ticked in job-27b/polish/review.md (written by nt27b apply)
  2-triage.tex   1-polish + the fixes decided from the triage of the LOW audit findings (an agent edits this file,
                 guided by stages/2-triage-task.md; the 27B proposes, the agent decides and writes)
  3-refs.tex     2-triage + the fixes decided from the citation check (stages/3-refs-task.md)
  ../branch2.tex 3-refs.tex, after the final checks; stages/provenance.md says how much each stage changed
Every stage is checked before the next one starts: the labels and the numbered environments stay those of the baseline,
\\begin / \\end are balanced, no conflict markers. Standard library only.
"""
import argparse
import difflib
import json
import re
import shutil
import sys
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nt27b as nt  # noqa: E402

STAGES = (('1-polish.tex', '润色'), ('2-triage.tex', '初筛修补'), ('3-refs.tex', '引用核查修补'))
LABEL = re.compile(r'\\label\{([^}]+)\}')
NUMBERED = re.compile(r'\\begin\{(theorem|definition)\}')
MARKER = re.compile(r'^[ \t]*(?:<{7}|={7}|>{7})(?:\s|$)', re.M)


class Paths:
    def __init__(self, root=None, job='job-27b'):
        self.root = Path(root) if root else HERE.parent          # nt-final-stage/
        self.package = HERE
        self.job = (self.package / job) if not Path(job).is_absolute() else Path(job)
        self.stages = self.package / 'stages' if root is None else Path(root) / '2-branch2' / 'stages'
        self.baseline = self.root / 'baseline.tex'
        self.branch2 = self.root / 'branch2.tex'
        self.state = self.stages / 'state.json'

    def stage(self, i):
        return self.stages / STAGES[i][0]


def read(path):
    return Path(path).read_bytes().decode('utf-8')


def load_state(p):
    return json.loads(p.state.read_text(encoding='utf-8')) if p.state.exists() else {}


def save_state(p, state):
    p.stages.mkdir(parents=True, exist_ok=True)
    nt.write_json(p.state, state)


def structure_problems(text, reference):
    """Differences that a stage may not introduce: labels, numbered environments, environment balance, conflict markers."""
    out = []
    if LABEL.findall(text) != LABEL.findall(reference):
        old, new = LABEL.findall(reference), LABEL.findall(text)
        out.append('label 变了' + (f'：少了 {[x for x in old if x not in new][:5]}' if [x for x in old if x not in new] else '')
                   + (f'，多了 {[x for x in new if x not in old][:5]}' if [x for x in new if x not in old] else ''))
    if NUMBERED.findall(text) != NUMBERED.findall(reference):
        out.append('theorem / definition 环境的个数或顺序变了')
    body = text[text.find('\\begin{document}'):]
    for env in sorted(set(re.findall(r'\\(?:begin|end)\{([A-Za-z*]+)\}', body))):
        b, e = len(re.findall(r'\\begin\{' + re.escape(env) + r'\}', body)), len(re.findall(r'\\end\{' + re.escape(env) + r'\}', body))
        if b != e:
            out.append(f'环境 {env} 的 \\begin 与 \\end 数目不同（{b} / {e}）')
    if MARKER.search(text):
        out.append('有合并冲突标记')
    return out


def change_summary(before, after):
    """(changed hunks, changed lines) between two manuscripts, by lines."""
    hunks = lines = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, before.splitlines(), after.splitlines(), autojunk=False).get_opcodes():
        if tag != 'equal':
            hunks += 1
            lines += max(i2 - i1, j2 - j1)
    return hunks, lines


TASKS = {
    1: ('triage', '初筛修补', 'DeepSeek 审计表里 LOW 条目的 27B 初筛',
        '27B 判为真缺口并给了补丁的：核对补丁是否正确、是否必要，必要时自己写更好的最小修补；'
        '27B 判为无法判断、或自称已解决但证据不是原文的：对照原文自己判断改不改；出错的条目也要看。'),
    2: ('refs', '引用核查修补', '27B 的引用核查',
        '逐处核对：被引用的结论是否真的支持这句话、它的前提在这里是否都满足、编号是否引错。'
        '确有问题时做最小的修改（改引用、补上前提的说明、补一句理由）；27B 弄错的不改，写明理由。'),
}


def task_text(p, i):
    key, title, what, how = TASKS[i]
    stage, previous = p.stage(i), p.stage(i - 1)
    log = p.stages / (stage.stem + '-log.md')
    return f"""# 第 2 步 · {title}（交给 Claude 或其他前沿模型的 agent 模式）

你要处理{what}的结果：

- 清单：`{p.job / key / 'for-claude.md'}`（每行一条：序号或行号、单元、原文、27B 的判断和补丁）
- 完整报告：`{p.job / key / 'review.md'}`
- 要改的稿子：`{stage}`（它是上一步 `{previous.name}` 的副本，已经含有前面各步的修改）

做法：

1. 逐条判断。{how}
2. 清单里的原文和补丁取自 baseline。前面的润色可能改过措辞，所以先在 `{stage.name}` 里找到对应位置，再改。
3. 只改 `{stage.name}` 这一个文件。不增删、不调换 theorem / definition 环境，不改 `\\label`；只做必要的最小修改，风格与原文一致。
4. 每一条都写进 `{log}`，一行一条：`条目 · 单元 · 改了 / 没改 · 一句理由`。
5. 不要在聊天里输出整份文件。完成后告诉作者运行：`python3 branch2.py next --done`（它会检查 label 和环境没有被改动）。

这些修改都算 27B 的改动（27B 提出、你决定并写入），第 3 步的留存率会按“{title}”这一阶段单独统计。
"""


def count_ticks(review):
    return len(re.findall(r'^\s*- \[[xX]\]', review.read_text(encoding='utf-8'), re.M)) if review.exists() else 0


def failed_requests(p):
    """{task: [(id, reason)]} when the answers are complete except for requests that failed (still failing after the
    GPU runner's retries); None when anything is pending, stale or invalid, so that only real failures can be accepted."""
    import contextlib
    import io
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = nt.main(['status', str(p.job), '--json', '--details'])
    if code != 0:
        return None
    try:
        report = json.loads(out.getvalue())
    except ValueError:
        return None
    failed = {}
    for task, row in report.items():
        if not isinstance(row, dict) or row.get('pending') or row.get('stale') or row.get('state') not in ('ready', 'incomplete'):
            return None
        issues = [i for i in row.get('issues', []) if i.get('state') == 'error']
        if len(issues) != row.get('errors', 0):
            return None
        if issues:
            failed[task] = [(i['id'], i.get('reason', '')) for i in issues]
    return failed or None


def where(p):
    """(stage key, message) of the next thing to do."""
    state = load_state(p)
    if not (p.job / 'manifest.json').exists():
        return 'prepare', '还没有准备任务：python3 branch2.py prepare'
    if state.get('finalized'):
        return 'done', f'已完成：{p.branch2}（来源统计见 {p.stages / "provenance.md"}）'
    if not p.stage(0).exists():
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            complete = nt.main(['verify', str(p.job)]) == 0
        failed = None if complete else failed_requests(p)
        accepted = state.get('accepted_errors')
        if failed and accepted == {k: [i for i, _ in v] for k, v in failed.items()}:
            complete = True                 # accepted with --accept-errors: they are in the agents' review lists
        elif failed:
            n = sum(len(v) for v in failed.values())
            lines = '；'.join(f'{task} {i}（{why}）' for task, v in failed.items() for i, why in v)
            return 'errors', (f'回答都齐了，只有 {n} 条重试后仍然出错：{lines}。它们会以 [error] 列进对应的 for-claude.md，'
                              '由初筛 / 引用核查那一步的 agent 对照原文人工判断。接受并继续：python3 branch2.py next --accept-errors'
                              '（也可以在 GPU 上用同样的命令再跑一次，只会重试这几条）')
        if not complete:
            return 'answers', (f'回答还不完整。在 RunPod 上运行 MODEL=<第 1 步的仓名> MODEL_REVISION=<commit> JOB={p.job.name} bash gpu/run_gpu.sh，'
                               f'把 results-*.tgz 取回后 python3 branch2.py import results-….tgz；进度：python3 nt27b.py status {p.job.name}')
        if not (p.job / 'polish' / 'review.md').exists():
            return 'collect', '回答已齐：python3 branch2.py next 会整理成审阅文件'
        return 'polish', (f'在 {p.job / "polish" / "review.md"} 里勾选要采用的润色（- [x] 接受），然后 python3 branch2.py next'
                          '（加 --accept-clean 同时采用所有规则检查通过的建议；加 --compile 编译核对）')
    for i in (1, 2):
        if not p.stage(i).exists():
            return f'start{i}', f'下一步：python3 branch2.py next 会准备“{TASKS[i][1]}”的稿子和任务说明'
        if not state.get(f'done{i}'):
            return f'edit{i}', (f'把 {p.stages / (p.stage(i).stem + "-task.md")} 交给 Claude（agent 模式），由它修改 {p.stage(i).name}；'
                                f'完成后 python3 branch2.py next --done')
    return 'finalize', f'下一步：python3 branch2.py next 做最后的检查并写出 {p.branch2}（加 --compile 编译核对）'


def cmd_prepare(p, args):
    code = nt.main(['prepare', '--out', str(p.job)] + (['--tex', str(args.tex)] if args.tex else []))
    if code == 0:
        save_state(p, {'job': str(p.job)})
        print(f'\n已准备 {p.job}。下一步在 RunPod 上一次跑完三类请求：\n'
              f'  MODEL=<第 1 步的仓名> MODEL_REVISION=<该仓库的 commit> JOB={p.job.name} GPU_PRICE=<时价> bash gpu/run_gpu.sh')
    return code


def cmd_import(p, args):
    """Unpack results-*.tgz from run_gpu.sh into the job directory; nothing outside it, no links."""
    archive = Path(args.archive)
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        bad = [m.name for m in members if m.issym() or m.islnk() or m.name.startswith('/') or '..' in Path(m.name).parts
               or Path(m.name).parts[:1] != (p.job.name,)]
        if bad:
            raise SystemExit(f'归档里有不该有的路径（只接受 {p.job.name}/ 下的普通文件）：{bad[:5]}')
        kwargs = {'filter': 'data'} if hasattr(tarfile, 'data_filter') else {}
        tar.extractall(p.job.parent, members=members, **kwargs)
    print(f'已解到 {p.job}。')
    # The review files in the archive were written on the GPU machine; write them again with this copy's rules.
    if (p.job / 'manifest.json').exists() and nt.main(['collect', str(p.job)]) != 0:
        print('（重新整理审阅文件时有条目不完整，见上面；python3 branch2.py status 会说明下一步）')
    print(where(p)[1])
    return 0


def check_stage(p, i):
    text, previous = read(p.stage(i)), read(p.stage(i - 1) if i else p.baseline)
    problems = structure_problems(text, read(p.baseline))
    if problems:
        print(f'✗ {p.stage(i).name} 没通过检查：\n  - ' + '\n  - '.join(problems))
        return False
    hunks, lines = change_summary(previous, text)
    print(f'✓ {p.stage(i).name}：label 与编号环境同 baseline；相对上一步改动 {hunks} 处、{lines} 行')
    return True


def cmd_next(p, args):
    key, message = where(p)
    state = load_state(p)
    if key == 'errors':
        if not args.accept_errors:
            print(message)
            return 2
        state['accepted_errors'] = {k: [i for i, _ in v] for k, v in failed_requests(p).items()}
        save_state(p, state)
        if not (p.job / 'polish' / 'review.md').exists():
            nt.main(['collect', str(p.job)])
        print('已接受出错的条目，它们留在给 agent 的清单里。\n' + where(p)[1])
        return 0
    if key in ('prepare', 'answers', 'done'):
        print(message)
        return 0 if key == 'done' else 2
    if key == 'collect':
        nt.main(['collect', str(p.job)])
        print(where(p)[1])
        return 0
    if key == 'polish':
        review = p.job / 'polish' / 'review.md'
        if not args.accept_clean and count_ticks(review) == 0:
            print(f'{review} 里还没有勾选任何润色。勾选后再运行，或加 --accept-clean 采用所有规则检查通过的建议。')
            return 2
        p.stages.mkdir(parents=True, exist_ok=True)
        code = nt.main(['apply', str(p.job), '--tex', str(p.baseline), '--out', str(p.stage(0))]
                       + (['--accept-clean'] if args.accept_clean else []) + (['--compile'] if args.compile else []))
        if code != 0:
            return code
        if not check_stage(p, 0):
            p.stage(0).unlink()
            return 3
        print(where(p)[1])
        return 0
    if key.startswith('start'):
        i = int(key[-1])
        shutil.copyfile(p.stage(i - 1), p.stage(i))
        task = p.stages / (p.stage(i).stem + '-task.md')
        task.write_text(task_text(p, i), encoding='utf-8')
        print(f'已准备 {p.stage(i)}（{p.stage(i - 1).name} 的副本）和任务说明 {task}。\n' + where(p)[1])
        return 0
    if key.startswith('edit'):
        i = int(key[-1])
        if not args.done:
            print(message)
            return 2
        if not check_stage(p, i):
            return 3
        state[f'done{i}'] = True
        save_state(p, state)
        print(where(p)[1])
        return 0
    # finalize
    final = read(p.stage(2))
    problems = structure_problems(final, read(p.baseline))
    if args.compile:
        ok, msg = nt.compile_check(final, 'branch2.tex')
        if ok is not True:
            problems.append('编译：' + msg)
    if problems:
        print('✗ 最后检查没通过：\n  - ' + '\n  - '.join(problems))
        return 3
    if p.branch2.exists() and p.branch2.read_bytes() != p.stage(2).read_bytes() and not args.force:
        print(f'{p.branch2} 已存在且内容不同，没有覆盖；确认要替换时加 --force')
        return 5
    shutil.copyfile(p.stage(2), p.branch2)
    rows, previous = [], read(p.baseline)
    for i, (name, title) in enumerate(STAGES):
        text = read(p.stage(i))
        hunks, lines = change_summary(previous, text)
        log = p.stages / (p.stage(i).stem + '-log.md')
        rows.append(f'| {title} | `{name}` | {hunks} | {lines} | ' + ('27B 写、你勾选' if i == 0 else '27B 提出、agent 决定并写入')
                    + (f'（说明：`{log.name}`）' if log.exists() else '') + ' |')
        previous = text
    total = change_summary(read(p.baseline), final)
    (p.stages / 'provenance.md').write_text('\n'.join([
        '# branch2 的改动来源', '', f'baseline → branch2 共改动 {total[0]} 处、{total[1]} 行（按行粗算；第 3 步的留存率按词、按改动块细算，'
        '并按这三个阶段分开统计）。', '', '| 阶段 | 稿子 | 改动处 | 改动行 | 由谁写 |', '|---|---|---|---|---|', *rows, '']), encoding='utf-8')
    state['finalized'] = nt.qp.sha(final)
    save_state(p, state)
    print(f'已写出 {p.branch2}；来源统计 {p.stages / "provenance.md"}。第 3 步可以开始了。')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description='第 2 步总控：baseline.tex → branch2.tex（分阶段，记录来源）')
    ap.add_argument('--job', default='job-27b', help='nt27b 的任务目录（默认 job-27b）')
    ap.add_argument('--root', help=argparse.SUPPRESS)        # tests: another nt-final-stage folder
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('prepare', help='生成全部请求（polish / triage / refs），基于 ../baseline.tex')
    a.add_argument('--tex', type=Path, help=argparse.SUPPRESS)
    a = sub.add_parser('import', help='解开 run_gpu.sh 打包的 results-*.tgz')
    a.add_argument('archive')
    sub.add_parser('status', help='现在到哪一步、下一步做什么')
    a = sub.add_parser('next', help='做下一步')
    a.add_argument('--accept-clean', action='store_true', help='润色：同时采用所有规则检查通过的建议')
    a.add_argument('--compile', action='store_true', help='润色和收尾时用 pdflatex 编译核对')
    a.add_argument('--done', action='store_true', help='初筛 / 引用核查的修改已经完成')
    a.add_argument('--force', action='store_true', help='收尾时允许替换已有的 ../branch2.tex')
    a.add_argument('--accept-errors', action='store_true',
                   help='只剩重试后仍出错的请求时接受它们并继续（它们列在 for-claude.md 里，由 agent 人工判断）')
    args = ap.parse_args(argv)
    p = Paths(args.root, args.job)
    if args.root:
        p.job = p.root / '2-branch2' / args.job
    if args.cmd == 'prepare':
        if args.root and args.tex is None:
            args.tex = p.baseline
        return cmd_prepare(p, args)
    if args.cmd == 'import':
        return cmd_import(p, args)
    if args.cmd == 'status':
        key, message = where(p)
        print(f'[{key}] {message}')
        return 0
    return cmd_next(p, args)


if __name__ == '__main__':
    sys.exit(main())
