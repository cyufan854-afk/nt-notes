"""Per-branch review/revision and deterministic report assembly."""
from .protocol import check_script

ACCEPTED = {'approve', 'approve_with_notes'}


def finding_status(branches):
    """Five user-facing states. Evidence is possible only with matching host records."""
    for b in branches:
        meta = b['review']['meta']
        if meta['verdict'] not in ACCEPTED:
            return '待人工'
        if b['execution'].get('status') not in ('not_requested', 'completed'):
            return '待人工'
        if meta.get('assessment', 'unknown') != b['answer']['meta'].get('assessment', 'unknown'):
            return '待人工'
    assessments = {b['review']['meta'].get('assessment', 'unknown') for b in branches}
    if len(assessments) != 1 or 'unknown' in assessments:
        return '待人工'
    assessment = assessments.pop()
    if assessment == 'false_positive':
        return '误报'
    if assessment == 'fixed':
        return '已修复'
    if any(has_evidence(b) for b in branches):
        return '有计算证据'
    return '确认有问题'


def has_evidence(branch):
    run = branch['execution']; meta = branch['review']['meta']
    return (run.get('status') == 'completed' and run.get('returncode') == 0
            and bool(run.get('stdout', '').strip()) and run.get('cleanup_ok') is True
            and meta.get('evidence_accepted') is True
            and run.get('id') in meta.get('evidence_ids', []))


def run_workflow(store, job, cfg, req, parallel):
    roles = cfg['roles']
    plan = store.stage(job, cfg, req, 'plan', roles['planner'], 'plan', {}, 'planner')
    answers = parallel([lambda i=i, provider=provider: store.stage(job, cfg, req, f'analysis{i}', provider, 'analysis', {'plan': plan}, f'analysis{i}')
                        for i, provider in enumerate(roles['analysts'])])
    branches = [{'branch': str(i), 'provider': roles['analysts'][i], 'answer': answer,
                 'answer_stage': f'analysis{i}', 'history': []} for i, answer in enumerate(answers)]
    active = [0, 1]
    for round_no in range(cfg['max_rounds'] + 1):
        if round_no:
            revisions = parallel([lambda i=i: store.stage(job, cfg, req, f'revision{round_no}_{i}', roles['analysts'][i], 'analysis',
                                                          {'plan': plan, 'previous': branches[i]['answer'], 'review': branches[i]['review'],
                                                           'execution': branches[i]['execution']}, f'revision{i}') for i in active])
            for i, answer in zip(active, revisions):
                branches[i]['answer'] = answer
                branches[i]['answer_stage'] = f'revision{round_no}_{i}'
        for i in active:
            b = branches[i]
            # The reviewer receives actual scheduler-owned execution, never a model's retelling.
            b['execution'] = store.execution(job, b['answer_stage'], check_script(b['answer']), cfg)
            b['review'] = store.stage(job, cfg, req, f'review{round_no}_{i}', roles['reviewer'], 'review',
                                      {'branch': str(i), 'plan': plan, 'answer': b['answer'], 'execution': b['execution']}, 'reviewer')
            b['history'].append({'round': round_no, 'answer': b['answer'], 'review': b['review'], 'execution': b['execution']})
        active = [i for i in active if branches[i]['review']['meta']['verdict'] == 'revise']
        if not active:
            break
    status = finding_status(branches)
    all_approved = all(b['review']['meta']['verdict'] in ACCEPTED for b in branches)
    execution_ok = all(b['execution'].get('status') in ('not_requested', 'completed') for b in branches)
    state = 'completed' if all_approved and execution_ok else 'needs_review'
    if req.get('finding') and status == '待人工':
        state = 'needs_review'
    result = {'protocol_version': 3, 'finding_status': status, 'branches': branches, 'state': state}
    return result, render_report(job, cfg, req, result)


def render_report(job, cfg, req, result):
    parts = ['# 协作报告', f'任务：{job}', '流程状态：' + result['state'] + '；结论状态：' + result['finding_status'],
             '这些状态是模型辅助的复核结果；“已修复”指修订稿通过复核，源文件未被修改。']
    if cfg['demo']:
        parts.append('**演示：模拟输出，无真实数学推理。**')
    if req.get('finding'):
        f = req['finding']
        parts += ['## 原始 finding', '位置：' + f['location'], f['excerpt'], '疑点：' + f['concern']]
    for b in result['branches']:
        review = b['review']['meta']
        parts += [f'## 分支 {b["branch"]} · {b["provider"]}',
                  '审查：' + review['verdict'] + '；判断：' + review.get('assessment', 'unknown'),
                  b['answer']['body'], '### 审查说明', b['review']['body']]
        if review.get('issues'):
            parts.append('审查元数据：' + repr(review['issues']))
        run = b['execution']
        if run.get('status') != 'not_requested':
            parts += ['### 调度器执行记录', f'状态：{run["status"]}；退出码：{run.get("returncode")}；证据 ID：{run.get("id")}',
                      '脚本 SHA256：' + run.get('code_sha256', ''),
                      '实际 stdout（原始字节另存 stdout.txt）：', quoted(run.get('stdout','')),
                      '实际 stderr：', quoted(run.get('stderr','')),
                      '执行不等于数学证明；检查范围与脚本含义见上面的复核。']
    return '\n\n'.join(parts) + '\n'


def quoted(text):
    # Indentation avoids output containing Markdown fences closing its own display block.
    return '\n'.join('    ' + line for line in text.splitlines()) or '    （空）'
