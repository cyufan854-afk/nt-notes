import argparse
import json
from pathlib import Path
import sys
from .core import Store, default_config, dumps
from . import findings
from .access import CATALOG, inspect_provider, configure, login, probe, model_info


def main():
    p = argparse.ArgumentParser(description='Co-op：独立多模型调度器')
    p.add_argument('--workspace', default='.coop', help='状态目录，默认为当前目录下 .coop')
    sub = p.add_subparsers(dest='cmd', required=True)
    init = sub.add_parser('init')
    init.add_argument('--demo', action='store_true')
    batches = sub.add_parser('batch', help='逐条处理 findings JSONL').add_subparsers(dest='batch_action', required=True)
    batch_run = batches.add_parser('run')
    batch_run.add_argument('findings_file')
    batch_run.add_argument('--file', action='append', default=[], help='额外上下文文件，每条 finding 都会收到')
    batch_run.add_argument('--tag', action='append', default=[])
    batch_run.add_argument('--project', default='default')
    batch_run.add_argument('--max-calls-per-finding', type=int)
    batch_resume = batches.add_parser('resume')
    batch_resume.add_argument('id')
    batch_resume.add_argument('--add-calls-per-finding', type=int, default=0)
    for name in ('status', 'report'):
        batches.add_parser(name).add_argument('id')
    edit = sub.add_parser('edit', help='按单元循环修订 LaTeX 源文件（写入前备份）').add_subparsers(dest='edit_action', required=True)
    for name in ('units', 'run'):
        cmd = edit.add_parser(name, help='只列出单元，不调用模型' if name == 'units' else '新建编辑会话并开始')
        cmd.add_argument('source')
        cmd.add_argument('--only', action='append', default=[], help='只处理这些单元 id，可重复')
        cmd.add_argument('--from', dest='start', help='从这个单元 id 开始')
        cmd.add_argument('--limit', type=int, help='最多处理多少个单元（试跑用）')
        cmd.add_argument('--changed-from', help='只处理与这份旧文件不同的单元')
        cmd.add_argument('--unchanged-from', help='只处理与这份文件相同的单元（与 --changed-from 互补，用来分批）')
        if name == 'run':
            cmd.add_argument('--project', default='default')
            cmd.add_argument('--max-calls-per-unit', type=int)
    edit_resume = edit.add_parser('resume')
    edit_resume.add_argument('id')
    edit_resume.add_argument('--add-calls-per-unit', type=int, default=0)
    edit_resume.add_argument('--accept-external', action='store_true', help='接受 coop 之外对源文件的修改（先提交到备份）')
    edit_resume.add_argument('--use', action='append', default=[], metavar='岗位=PROVIDER',
                             help='从现在起把岗位交给另一个 provider（岗位：planner / analysts.0 / analysts.1 / reviewer / arbiter），'
                                  '例如某家额度用完时 --use analysts.0=grok；可重复；记在报告里')
    edit_resume.add_argument('--arbiter', choices=['cli', 'manual'],
                             help='切换仲裁方式：cli 自动调用 roles.arbiter（agy 上的 Argon）；manual 网页人工中转（agy 额度不够时的后备）')
    edit_ledger = edit.add_parser('ledger', help='跨单元决定台账：列出某个源文件的条目，或手工添加一条')
    edit_ledger.add_argument('source')
    edit_ledger.add_argument('--add', help='添加一条（例如全书统一的记号或写法）')
    edit_status = edit.add_parser('status')
    edit_status.add_argument('id', nargs='?')
    edit.add_parser('report').add_argument('id')
    edit_restore = edit.add_parser('restore')
    edit_restore.add_argument('id')
    edit_restore.add_argument('--to', default='original', help='original 或备份仓库中的提交号')
    edit_restore.add_argument('--force', action='store_true')
    web = edit.add_parser('web', help='网页版强模型仲裁：导出批次、导入回复、放弃').add_subparsers(dest='web_action', required=True)
    web_export = web.add_parser('export', help='重新生成等待仲裁单元的批次文件')
    web_export.add_argument('id')
    web_export.add_argument('--batch-units', type=int, help='每批最多单元数')
    web_export.add_argument('--batch-chars', type=int, help='每批文件大约的字符上限')
    web_import = web.add_parser('import', help='导入保存下来的网页回复；- 表示从标准输入读取')
    web_import.add_argument('id')
    web_import.add_argument('files', nargs='+')
    web_drop = web.add_parser('drop', help='放弃这些单元的网页仲裁，改为需要人工')
    web_drop.add_argument('id')
    web_drop.add_argument('units', nargs='*')
    web_drop.add_argument('--all', action='store_true', help='所有等待仲裁的单元')
    run = sub.add_parser('run')
    run.add_argument('instruction')
    run.add_argument('--file', action='append', default=[])
    run.add_argument('--tag', action='append', default=[])
    run.add_argument('--project', default='default')
    run.add_argument('--max-calls', type=int)
    resume = sub.add_parser('resume')
    resume.add_argument('id')
    resume.add_argument('--add-calls', type=int, default=0)
    status = sub.add_parser('status')
    status.add_argument('id', nargs='?')
    report = sub.add_parser('report')
    report.add_argument('id')
    sub.add_parser('doctor')
    sub.add_parser('providers')
    auth = sub.add_parser('login', help='在当前交互终端打开官方 CLI 登录')
    auth.add_argument('provider')
    conf = sub.add_parser('configure')
    conf.add_argument('provider')
    group = conf.add_mutually_exclusive_group()
    group.add_argument('--model')
    group.add_argument('--default-model', action='store_true')
    conf.add_argument('--executable')
    conf.add_argument('--auth-mode', choices=['subscription', 'native', 'api'])
    conf.add_argument('--kind', choices=['gemini', 'antigravity'], help='Google 入口：antigravity（agy，订阅）或 gemini（Gemini CLI，付费 API key）')
    check = sub.add_parser('check', help='发送一次极小测试请求；all 会逐家发送，可能消耗额度')
    check.add_argument('provider', help='provider 名称或 all')
    check.add_argument('--timeout', type=int, default=60)
    models = sub.add_parser('models')
    models.add_argument('provider')
    models.add_argument('--fetch', action='store_true', help='API: 用已配置密钥请求 /models；antigravity: 运行 agy models 并核对 slug')
    mem = sub.add_parser('memory').add_subparsers(dest='action', required=True)
    for verb in ('approve', 'revoke'):
        mem.add_parser(verb).add_argument('id')
    search = mem.add_parser('search')
    search.add_argument('--tag', action='append', default=[])
    search.add_argument('--project', default='default')
    args = p.parse_args()
    try:
        store = Store(args.workspace)
        cfgfile = store.root / 'config.json'
        if args.cmd == 'init':
            if cfgfile.exists():
                raise ValueError('配置已存在；请编辑它或使用另一个 --workspace')
            cfgfile.write_text(json.dumps(default_config(args.demo), ensure_ascii=False, indent=2), encoding='utf-8')
            result = {'config': str(cfgfile), 'demo': args.demo}
        elif args.cmd == 'batch':
            if args.batch_action == 'run':
                batch_id = findings.create(store, args.findings_file, args.file, args.tag, args.project, args.max_calls_per_finding)
                result = findings.execute(store, batch_id)
            elif args.batch_action == 'resume':
                result = findings.execute(store, args.id, args.add_calls_per_finding)
            else:
                result = findings.status(store, args.id)
                if args.batch_action == 'report':
                    findings.write_report(store, result)
                    print(Path(result['report']).read_text(encoding='utf-8'))
                    return 0
        elif args.cmd == 'edit':
            from . import editloop
            act = args.edit_action
            if act in ('units', 'run') and args.limit is not None and args.limit <= 0:
                raise ValueError('--limit 必须为正整数')
            if act == 'units':
                result = editloop.preview(store, args.source, args.only, args.start, args.limit, args.changed_from, args.unchanged_from)
            elif act == 'run':
                sid = editloop.create(store, args.source, args.only, args.start, args.limit, args.changed_from,
                                      args.project, args.max_calls_per_unit, args.unchanged_from)
                result = editloop.execute(store, sid)
            elif act == 'resume':
                result = editloop.execute(store, args.id, args.add_calls_per_unit, args.accept_external, args.arbiter, args.use)
            elif act == 'status':
                result = editloop.status(store, args.id)
            elif act == 'ledger':
                result = editloop.ledger(store, args.source, args.add)
            elif act == 'web':
                if args.web_action == 'export':
                    result = editloop.web_export(store, args.id, args.batch_units, args.batch_chars)
                elif args.web_action == 'import':
                    texts = [sys.stdin.read() if f == '-' else Path(f).expanduser().read_text(encoding='utf-8')
                             for f in args.files]
                    result = editloop.web_import(store, args.id, texts)
                    print(dumps(result))
                    return 2 if result['errors'] or not result['imported'] else 0
                else:
                    result = editloop.web_drop(store, args.id, args.units, args.all)
            elif act == 'report':
                path = store.root / args.id / 'report.md'
                if not path.exists():
                    editloop.write_report(editloop.Session(store, args.id))
                print(path.read_text(encoding='utf-8'))
                return 0
            else:
                result = editloop.restore(store, args.id, args.to, args.force)
        elif args.cmd == 'run':
            job = store.create(args.instruction, args.file, args.tag, args.project, args.max_calls)
            result = store.execute(job)
        elif args.cmd == 'resume':
            result = store.execute(args.id, args.add_calls)
        elif args.cmd == 'status':
            result = store.status(args.id)
        elif args.cmd == 'report':
            row = store.get(args.id)
            if not row['result']:
                raise ValueError('尚无报告；使用 status 查看暂停原因')
            print(row['result'])
            return 0
        elif args.cmd == 'providers':
            result = CATALOG
        elif args.cmd in ('doctor', 'login', 'configure', 'check', 'models'):
            cfg = json.loads(cfgfile.read_text(encoding='utf-8'))
            if args.cmd == 'doctor':
                result = {name: inspect_provider(name, spec) for name, spec in cfg['providers'].items()}
                result['_note'] = '本地检查不验证额度。check NAME 会发送真实测试请求。'
            else:
                name = args.provider
                if name not in cfg['providers'] and not (args.cmd == 'check' and name == 'all'):
                    raise ValueError('未知 provider: ' + name)
                if args.cmd == 'configure':
                    result = configure(cfgfile, name, args.model, args.executable, args.auth_mode, args.default_model, args.kind)
                elif args.cmd == 'login':
                    result = login(name, cfg['providers'][name])
                elif args.cmd == 'models':
                    result = model_info(store.root, name, cfg['providers'][name], args.fetch)
                else:
                    if args.timeout <= 0:
                        raise ValueError('timeout 必须为正整数')
                    names = list(cfg['providers']) if name == 'all' else [name]
                    result = [probe(store.root, item, cfg['providers'][item], args.timeout) for item in names]
                    print(dumps(result))
                    return 2 if any(item['state'] == 'failed' for item in result) else 0
        elif args.action == 'search':
            result = store.memories([t.lower().strip() for t in args.tag], args.project)
        else:
            row = store.get(args.id)
            if args.action == 'approve' and row['state'] != 'completed':
                raise ValueError('只有完成的任务可以加入已确认记忆')
            with store.db() as db:
                db.execute('UPDATE jobs SET approved=? WHERE id=?', (int(args.action == 'approve'), args.id))
            result = {'id': args.id, 'approved': args.action == 'approve'}
        print(dumps(result))
        if args.cmd == 'login' and isinstance(result, dict) and result.get('native_exit_code', 0) != 0:
            return 1
        return 2 if isinstance(result, dict) and result.get('state') in ('paused', 'needs_review', 'awaiting_web') else 0
    except (Exception, KeyboardInterrupt) as exc:
        print(dumps({'error': str(exc) or '用户中断；可 resume 恢复'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
