"""JSONL findings become independent, resumable child jobs."""
import fcntl
import json
from pathlib import Path
import re
import shutil
import tempfile
import os
import uuid
from .core import dumps, validate_config


def load(path):
    path = Path(path).expanduser().resolve()
    if path.stat().st_size > 2_000_000:
        raise ValueError('findings JSONL 超过 2 MB，请分批')
    rows, ids = [], set()
    for line_no, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError('每行必须为对象')
            item = {}
            for key, alias in [('location','位置'),('excerpt','原文片段'),('concern','疑点')]:
                value = row.get(key, row.get(alias))
                if not isinstance(value, str) or not value.strip():
                    raise ValueError('缺少非空字符串字段 ' + key)
                if any(ord(c) < 32 and c not in '\n\r\t' for c in value):
                    raise ValueError('字段含异常控制字符；请用 json.dumps 生成 JSONL，LaTeX 反斜杠须正确转义')
                item[key] = value
            item['id'] = row.get('id', f'F{len(rows)+1:04d}')
            if not isinstance(item['id'], str) or not item['id'].strip() or item['id'] in ids:
                raise ValueError('id 必须为非空且不重复的字符串')
            ids.add(item['id']); rows.append(item)
        except (ValueError, TypeError) as exc:
            raise ValueError(f'findings 第 {line_no} 行：{exc}') from None
    if not rows:
        raise ValueError('findings 为空')
    if len(rows) > 1000:
        raise ValueError('每批最多 1000 条 finding')
    return rows


def atomic_json(path, value):
    path = Path(path)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='manifest-')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            f.write(dumps(value)); f.flush(); os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        Path(name).unlink(missing_ok=True)


def create(store, path, context_files, tags, project, budget=None):
    # Validate the ENTIRE input before creating jobs or spending any model calls.
    rows = load(path)
    cfg = validate_config(json.loads((store.root/'config.json').read_text(encoding='utf-8')))
    if budget is not None and budget <= 0:
        raise ValueError('每条 finding 的调用预算必须为正整数')
    batch_id = 'batch-' + uuid.uuid4().hex[:12]
    folder = store.root / batch_id; folder.mkdir()
    items = []
    try:
        for row in rows:
            objective = ('独立复核这条 finding：判断疑点是否成立；需要时提出修订稿或生成 Python 检查。'
                         '只处理这一条，保留未解决的条件和分歧。源文件不自动改写。')
            job = store.create(objective, context_files, tags, project, budget, finding=row, config=cfg)
            items.append({'finding_id':row['id'], 'location':row['location'], 'job_id':job})
        manifest = {'id':batch_id,'protocol_version':3,'project':project,'items':items,
                    'source':str(Path(path).expanduser().resolve()), 'findings':rows}
        atomic_json(folder/'manifest.json',manifest)
    except BaseException:
        # No inference starts until the manifest exists. Remove only our pending children.
        for item in items:
            with store.db() as db:
                db.execute('DELETE FROM jobs WHERE id=? AND state="pending"',(item['job_id'],))
            shutil.rmtree(store.root/item['job_id'],ignore_errors=True)
        shutil.rmtree(folder,ignore_errors=True)
        raise
    return batch_id


def manifest(store, batch_id):
    if not re.fullmatch(r'batch-[0-9a-f]{12}',batch_id):
        raise ValueError('batch ID 格式错误')
    return json.loads((store.root/batch_id/'manifest.json').read_text(encoding='utf-8'))


def status(store, batch_id):
    m = manifest(store,batch_id)
    items = []
    for row in m['items']:
        child = store.status(row['job_id'])
        if not isinstance(child,dict):
            raise ValueError('清单子任务缺失：'+row['job_id'])
        items.append({**row, 'state':child['state'], 'finding_status':child['finding_status'],
                      'calls':child['calls'], 'error':child['error'], 'report':child['report']})
    states = {x['state'] for x in items}
    if states & {'pending','running','paused'}:
        state='paused' if 'paused' in states else 'pending'
    else:
        state='needs_review' if 'needs_review' in states else 'completed'
    return {'id':batch_id,'state':state,'items':items,'report':str(store.root/batch_id/'report.md')}


def execute(store,batch_id,add_calls=0):
    if add_calls < 0:
        raise ValueError('add-calls-per-finding 不能为负数')
    m=manifest(store,batch_id)
    with (store.root/batch_id/'lock').open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('此清单已有调度器运行') from None
        for row in m['items']:
            before=store.get(row['job_id'])
            if before['state'] in ('completed','needs_review'):
                continue
            result=store.execute(row['job_id'],add_calls)
            # Do not continue spending on later findings after an explicit interruption.
            if result.get('error') == '用户中断':
                break
        result=status(store,batch_id)
        atomic_json(store.root/batch_id/'status.json',result)
        write_report(store,result)
        return result


def write_report(store,result):
    parts=['# Findings 清单报告','清单：'+result['id'],
           '状态为模型辅助判断。“已修复”表示修订稿已复核，源文件未改写；计算证据不等于一般性证明。']
    for item in result['items']:
        parts.extend([f'## {item["finding_id"]} · {item["location"]}',
                      f'结论：{item["finding_status"]}；流程：{item["state"]}；模型调用：{item["calls"]}',
                      '子任务：'+item['job_id'],
                      store.get(item['job_id'])['result'] or ('尚无完整报告。'+item['error'])])
    (store.root/result['id']/'report.md').write_text('\n\n'.join(parts)+'\n',encoding='utf-8')
