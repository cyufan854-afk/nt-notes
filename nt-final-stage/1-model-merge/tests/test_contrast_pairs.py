"""Qwen38_pi_ContrastPairs.ipynb: the embedded module contrast_pairs (standard library only).

Problem parsing and selection, answer extraction and grading, pairing, the pairs-file check and the veto rule. The
vLLM parts need a GPU and are not run here.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NOTEBOOK = HERE.parent / 'Qwen38_pi_ContrastPairs.ipynb'


def module_source():
    nb = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
    for cell in nb['cells']:
        src = ''.join(cell['source'])
        if "CONTRAST_SOURCE = r'''" in src:
            start = src.index("CONTRAST_SOURCE = r'''") + len("CONTRAST_SOURCE = r'''")
            return src[start:src.index("'''", start)]
    raise AssertionError('no embedded contrast_pairs module')


def load():
    if 'contrast_pairs' not in sys.modules:
        directory = Path(tempfile.mkdtemp(prefix='contrast-'))
        (directory / 'contrast_pairs.py').write_text(module_source(), encoding='utf-8')
        spec = importlib.util.spec_from_file_location('contrast_pairs', directory / 'contrast_pairs.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules['contrast_pairs'] = module
        spec.loader.exec_module(module)
    return sys.modules['contrast_pairs']


def problem(pid, category='math', kind='number', expected=12, split='pool', **extra):
    return {'pid': pid, 'split': split, 'category': category, 'prompt': f'question {pid}', 'kind': kind,
            'expected': expected, 'source': f'src#{pid}', **extra}


def sample(k, correct, length, finish='stop', pred='x'):
    return {'k': k, 'text': '', 'response_ids': list(range(length)), 'finish_reason': finish,
            'pred': pred if finish == 'stop' else None, 'correct': correct if finish == 'stop' else None}


class Problems(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = load()

    def test_parsers(self):
        c = self.c
        m = c.math_item({'problem': 'Find n.', 'level': 'Level 4', 'solution': 'So $\\boxed{1{,}234}$.'}, 'number_theory')
        self.assertEqual((m['expected'], m['level'], m['group']), (1234, 4, 'number_theory/L4'))
        self.assertIsNone(c.math_item({'problem': 'x', 'level': 'Level 5', 'solution': '\\boxed{\\frac12}'}, 'algebra'))
        self.assertIsNone(c.math_item({'problem': 'x', 'level': '?', 'solution': '\\boxed{3}'}, 'algebra'))
        q = c.mmlu_pro_item({'options': ['a', 'b', 'c', 'd'], 'answer_index': 2, 'answer': 'C', 'question_id': 7,
                             'question': 'Q?', 'category': 'law'})
        self.assertEqual((q['expected'], q['options'], q['kind']), ('C', 4, 'letter'))
        self.assertIsNone(c.mmlu_pro_item({'options': ['a', 'b', 'c', 'N/A'], 'answer_index': 1, 'answer': 'B',
                                           'question_id': 1, 'question': 'Q'}))
        z = c.ceval_item({'id': 3, 'question': '问', 'A': '1', 'B': '2', 'C': '3', 'D': '4', 'answer': 'D'}, 'logic')
        self.assertEqual((z['expected'], z['kind'], z['lang']), ('D', 'letter_zh', 'zh'))
        x = c.cruxeval_item({'id': 'sample_1', 'code': 'def f(a):\n    return a', 'input': '1', 'output': "'1'"})
        self.assertEqual(x['expected'], "'1'")
        self.assertIsNone(c.cruxeval_item({'id': 's', 'code': 'def (', 'input': '1', 'output': '1'}))
        self.assertEqual(c.bbh_item({'input': 'Q (A) x (B) y', 'target': '(B)'}, 'navigate', 0)['expected'], 'B')
        self.assertEqual(c.bbh_item({'input': 'Q', 'target': '-12'}, 'multistep', 1)['expected'], -12)
        self.assertEqual(c.bbh_item({'input': 'Q', 'target': 'True'}, 'boolean', 2)['kind'], 'word')
        self.assertIsNone(c.bbh_item({'input': 'Q', 'target': '(C)'}, 'navigate', 3))

    def test_math_files_and_candidates(self):
        c = self.c
        files = ['README.md', 'algebra/test-00000-of-00001.parquet', 'algebra/train-00000-of-00001.parquet',
                 'number_theory/test-00000-of-00001.parquet', 'geometry/test-00000-of-00001.parquet']
        self.assertEqual(c.math_files(files, ['number_theory', 'algebra'], 'test'),
                         [('number_theory', 'number_theory/test-00000-of-00001.parquet'),
                          ('algebra', 'algebra/test-00000-of-00001.parquet')])
        with self.assertRaises(ValueError):
            c.math_files(files, ['precalculus'], 'test')
        rows = {'number_theory/test-00000-of-00001.parquet': [
                    {'problem': 'a', 'level': 'Level 3', 'solution': '\\boxed{5}'},
                    {'problem': 'b', 'level': 'Level 1', 'solution': '\\boxed{6}'}],
                'algebra/test-00000-of-00001.parquet': [{'problem': 'c', 'level': 'Level 5', 'solution': '\\boxed{-2}'}]}
        items = c.candidates('math', lambda repo, rev, name: name, lambda path: rows[path], files)
        self.assertEqual(sorted(i['expected'] for i in items), [-2, 5])          # level 1 dropped

    def test_select(self):
        c = self.c
        items = [{'key': f'k{i}', 'group': f'g{i % 3}', 'question': f'q{i}', 'lang': 'en', 'kind': 'number',
                  'expected': i, 'source': f's{i}'} for i in range(20)]
        items.append(dict(items[0], key='dup'))                                  # same question: dropped
        picked = c.select('math', items, seed=1, pool=10, heldout=5)
        self.assertEqual([p['split'] for p in picked].count('pool'), 10)
        self.assertEqual([p['split'] for p in picked].count('heldout'), 5)
        self.assertEqual(len({p['pid'] for p in picked}), 15)
        self.assertEqual(picked, c.select('math', items, seed=1, pool=10, heldout=5))
        self.assertEqual(len({p['group'] for p in picked[:3]}), 3)                # groups interleaved
        self.assertIn('<answer>', picked[0]['prompt'])
        with self.assertRaises(ValueError):
            c.select('math', items, seed=1, pool=19, heldout=5)
        self.assertEqual(c.check_counts(c.COUNTS), c.COUNTS)
        with self.assertRaises(ValueError):
            c.check_counts({'math': {'pool': 1, 'heldout': 0}})


class Answers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = load()

    def test_extract(self):
        c = self.c
        self.assertEqual(c.extract_answer('think <answer>1</answer>\n</think>\n\n<answer> 42 </answer><|im_end|>'), '42')
        self.assertIsNone(c.extract_answer('still thinking <answer>3</answer>'))          # thinking never closed
        self.assertEqual(c.extract_answer('<answer>3</answer> <answer>4</answer>', thinking=False), '4')
        self.assertIsNone(c.extract_answer('</think> the answer is 4'))

    def test_grade(self):
        c = self.c
        num = problem('p', expected=1234)
        for text in ('1234', '1,234', '$1234$', '\\boxed{1234}', '1234.0', ' 1234. '):
            self.assertTrue(c.grade(num, text), text)
        self.assertFalse(c.grade(num, '1235'))
        self.assertIsNone(c.grade(problem('l', expected=12), '1, 2'))           # a list is not the number 12
        self.assertIsNone(c.grade(num, 'one thousand'))
        self.assertIsNone(c.grade(num, None))
        mc = problem('q', 'knowledge_mc', 'letter', 'C', options=4)
        for text, want in (('C', True), ('(C)', True), ('C. something', True), ('B', False), ('E', None), ('Clearly', None)):
            self.assertEqual(c.grade(mc, text), want, text)
        bbh = problem('r', 'logic', 'letter', 'K')
        self.assertTrue(c.grade(bbh, '(K)'))
        zh = problem('s', 'chinese_mc', 'letter_zh', 'B', options=4)
        self.assertTrue(c.grade(zh, 'B、'))
        lit = problem('t', 'code_reasoning', 'literal', "[1, 'a']")
        self.assertTrue(c.grade(lit, "[1,'a']"))
        self.assertFalse(c.grade(lit, "(1, 'a')"))
        self.assertTrue(c.grade(problem('u', 'code_reasoning', 'literal', "'abc'"), "'abc'"))
        self.assertIsNone(c.grade(problem('u', 'code_reasoning', 'literal', "'abc'"), 'abc'))     # not a repr(): unparseable
        self.assertIsNone(c.grade(problem('x', 'code_reasoning', 'literal', '3'), 'this is not Python'))
        big = problem('big', expected=9007199254740993)
        self.assertTrue(c.grade(big, '9007199254740993'))                                       # exact, no float rounding
        self.assertFalse(c.grade(big, '9007199254740992'))
        self.assertTrue(c.grade(problem('d', expected=12), '12.00'))
        self.assertFalse(c.grade(problem('e', expected=12), '12.0000001'))
        self.assertIsNotNone(c.grade(problem('f', expected=1), '1' * 400))                       # no OverflowError
        self.assertFalse(c.grade(problem('v', 'code_reasoning', 'literal', '3'), '3.0'))
        self.assertTrue(c.grade(problem('w', 'logic', 'word', 'True'), 'true.'))

    def test_graded_samples_and_accuracy(self):
        c = self.c
        p1, p2 = problem('a', expected=5), problem('b', 'logic', 'word', 'Yes')
        outs = [{'text': '</think><answer>5</answer>', 'token_ids': [1, 2], 'finish_reason': 'stop'},
                {'text': '</think><answer>6</answer>', 'token_ids': [3], 'finish_reason': 'stop'},
                {'text': 'cut off', 'token_ids': [4], 'finish_reason': 'length'}]
        s1 = c.graded_samples(p1, outs)
        self.assertEqual([s['correct'] for s in s1], [True, False, None])
        s2 = c.graded_samples(p2, [{'text': '</think> no tag', 'token_ids': [9], 'finish_reason': 'stop'},
                                   {'text': '</think><answer>Yes</answer>', 'token_ids': [8], 'finish_reason': 'stop'}])
        acc = c.accuracy([p1, p2], {'a': {'samples': s1}, 'b': {'samples': s2}})
        self.assertAlmostEqual(acc['by_category']['math'], 1 / 3)
        self.assertAlmostEqual(acc['by_category']['logic'], 1 / 2)
        self.assertAlmostEqual(acc['overall'], (1 / 3 + 1 / 2) / 2)
        self.assertEqual((acc['unfinished'], acc['unparseable']), (1, 1))


class Pairs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = load()

    def test_build_pairs(self):
        c = self.c
        probs = [problem('mixed'), problem('right'), problem('wrong'), problem('long'), problem('held', split='heldout'),
                 problem('cut')]
        results = {
            'mixed': {'samples': [sample(0, True, 100), sample(1, False, 400), sample(2, False, 130), sample(3, True, 1000)]},
            'right': {'samples': [sample(0, True, 50), sample(1, True, 60)]},
            'wrong': {'samples': [sample(0, False, 50)]},
            'long': {'samples': [sample(0, True, 100), sample(1, False, 500)]},
            'held': {'samples': [sample(0, True, 10), sample(1, False, 10)]},
            'cut': {'samples': [sample(0, True, 100), sample(1, False, 100, finish='length')]},
        }
        prompt_ids = {p['pid']: [7, 8, 9] for p in probs}
        rows, report = c.build_pairs(probs, results, prompt_ids, max_ratio=2.0, seed=0)
        self.assertEqual(report['pairs'], 1)
        self.assertEqual((report['all_right'], report['all_wrong'], report['length_mismatch']), (2, 1, 1))  # 'cut' counts as all right
        self.assertEqual(report['problems'], 5)                                   # held-out problems are not paired
        right, wrong = rows
        self.assertEqual((right['role'], wrong['role']), ('correct', 'wrong'))
        self.assertEqual((len(right['response_ids']), len(wrong['response_ids'])), (100, 130))   # the closest lengths
        self.assertEqual(right['prompt_ids'], [7, 8, 9])
        self.assertEqual(set(c.check_pairs(rows)), {'mixed'})
        self.assertEqual(report['tokens'], 3 + 100 + 3 + 130)

    def test_check_pairs_rejects(self):
        c = self.c
        base = {'pair': 'p', 'category': 'math', 'prompt_ids': [1], 'response_ids': [2]}
        with self.assertRaises(ValueError):
            c.check_pairs([{**base, 'id': 'a', 'role': 'correct'}])
        with self.assertRaises(ValueError):
            c.check_pairs([{**base, 'id': 'a', 'role': 'correct'}, {**base, 'id': 'b', 'role': 'wrong', 'prompt_ids': [3]}])
        with self.assertRaises(ValueError):
            c.check_pairs([{**base, 'id': 'a', 'role': 'right'}])

    def test_veto(self):
        c = self.c
        subject = {'overall': 0.70, 'by_category': {'math': 0.7}, 'per_problem': {f'p{i}': 0.7 for i in range(10)}}
        worse = {'overall': 0.60, 'by_category': {'math': 0.6}, 'per_problem': {f'p{i}': 0.6 for i in range(10)}}
        close = {'overall': 0.67, 'by_category': {'math': 0.67}, 'per_problem': {f'p{i}': 0.67 for i in range(10)}}
        d = c.veto(subject, [('selected', worse), ('global', close)], max_drop=0.05)
        self.assertEqual(d['approved'], 'global')
        self.assertEqual([r['ok'] for r in d['candidates']], [False, True])
        self.assertAlmostEqual(d['candidates'][0]['vs_subject']['diff'], -0.1)
        self.assertIsNone(c.veto(subject, [('selected', worse)])['approved'])

    def test_sampling_params(self):
        c = self.c
        self.assertEqual(c.sampling_params_from({'temperature': 1.0, 'top_k': 40, 'do_sample': True}),
                         {'temperature': 1.0, 'top_p': 0.95, 'top_k': 40})
        self.assertEqual(c.sampling_params_from(None), c.DEFAULT_SAMPLING)

    def test_notebook_metadata_matches_module(self):
        nb = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
        meta = nb['metadata']['contrast_pairs']
        self.assertEqual(meta['module_sha256'], hashlib.sha256(module_source().encode()).hexdigest())
        self.assertEqual(meta['version'], load().VERSION)


if __name__ == '__main__':
    unittest.main()


class CellsBase(unittest.TestCase):
    """Sections 6 and 7 of the notebook, run with the real cells and a stand-in for vLLM (cp.generate / cp.make_llm)."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.root = Path(self.tmp.name)
        self.c = load()
        nb = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
        cells = [''.join(x['source']) for x in nb['cells']]
        self.samples_cell = next(x for x in cells if x.startswith('def load_samples('))
        self.veto_cell = next(x for x in cells if x.startswith('if STAGE == "veto":'))
        self.heldout = [problem(f'h{i}', split='heldout') for i in range(4)]
        self.loaded = [];self.copied = [];self.generated = []
        self.rate = {}

    def tearDown(self):
        self.tmp.cleanup()

    def env(self, stage='none', chunk=2, problems=None):
        c = self.c;test = self
        fake = type(sys)('fake_cp')
        fake.__dict__.update({k: v for k, v in c.__dict__.items() if not k.startswith('__')})

        def generate(llm, prompt_ids, n, params, max_tokens, seeds):
            test.generated.append((llm, len(prompt_ids)))
            out = []
            for ids, seed in zip(prompt_ids, seeds):
                index = int(ids[0])
                right = index < test.rate[llm] * 4
                out.append([{'text': '</think><answer>' + ('12' if right else '13') + '</answer>', 'token_ids': [1, 2, 3],
                             'finish_reason': 'stop'} for _ in range(n)])
            return out

        def make_llm(path, *args):
            test.loaded.append(test.copied[-1])
            return test.copied[-1]
        fake.generate, fake.make_llm = generate, make_llm
        fake_shutil = type(sys)('fake_shutil')

        def copytree(src, dst):
            test.copied.append(Path(src).name[4:])
        fake_shutil.copytree = copytree
        fake_shutil.rmtree = lambda *a, **k: None
        problems = problems or self.heldout
        env = {'STAGE': stage, 'DRIVE_DIR': str(self.root), 'WORK': self.root / 'work', 'PROBLEMS': problems, 'json': json,
               'Path': Path, 'time': __import__('time'), 'shutil': fake_shutil, 'cp': fake, 'SAMPLES_HELDOUT': 2,
               'MAX_MODEL_LEN': 100, 'VLLM': {'gpu_memory_utilization': 0.9, 'quantization': 'fp8', 'max_num_seqs': 4},
               'SEED': 0, 'VERSIONS': {}, 'VETO_MAX_DROP': 0.05, 'CHUNK': chunk, 'THINKING': True, 'SAMPLING': {},
               'MAX_RESPONSE_TOKENS': 64, 'PROMPT_IDS': {p['pid']: [i, 7] for i, p in enumerate(problems)},
               'RUN_IDENTITY': {'run': 1}}
        exec(compile(self.samples_cell, 'samples-cell', 'exec'), env)
        return env

    def subject(self, rate=0.75):
        self.rate['pi'] = rate
        env = self.env()
        env['run_samples']('pi', self.heldout, 'heldout', 2, self.root / 'work' / 'samples', 'heldout')
        (self.root / 'work' / 'heldout_subject.json').write_text(json.dumps({'quantization': 'fp8'}))

    def run_veto(self, rates):
        self.rate.update(rates)
        (self.root / 'veto').mkdir(parents=True, exist_ok=True)
        request = {'candidates': [{'name': n, 'directory': str(self.root / ('src-' + n)), 'fingerprint': n * 8} for n in ('selected', 'global')]}
        (self.root / 'veto' / 'request.json').write_text(json.dumps(request))
        self.loaded.clear()
        env = self.env('veto')
        exec(compile(self.veto_cell, 'veto-cell', 'exec'), env)
        result = self.root / 'veto' / 'result.json'
        return list(self.loaded), (json.loads(result.read_text()) if result.exists() else None)



class NotebookCells(CellsBase):
    def test_resume_by_problem_whatever_the_chunk(self):
        problems = [problem(f'p{i}', split='heldout') for i in range(6)]
        self.rate['pi'] = 1.0
        out = self.root / 's'
        first = self.env(chunk=2, problems=problems)['run_samples']('pi', problems[:4], 'heldout', 2, out, 'heldout')
        self.assertEqual(len(first), 4)
        self.generated.clear()
        again = self.env(chunk=3, problems=problems)['run_samples']('pi', problems, 'heldout', 2, out, 'heldout')
        self.assertEqual(sorted(again), [p['pid'] for p in problems])
        self.assertEqual(self.generated, [('pi', 2)])                      # only the two problems not sampled before
        self.c.accuracy(problems, again)

    def test_first_passing_candidate_ends_it(self):
        self.subject(0.75)
        loaded, result = self.run_veto({'selected': 0.75, 'global': 0.75})
        self.assertEqual((loaded, result['approved']), (['selected'], 'selected'))
        self.assertIn('eval_identity', result)

    def test_one_model_per_session(self):
        self.subject(0.75)
        loaded, result = self.run_veto({'selected': 0.25, 'global': 0.75})
        self.assertEqual((loaded, result), (['selected'], None))           # stops for a restarted session
        loaded, result = self.run_veto({'selected': 0.25, 'global': 0.75})
        self.assertEqual(loaded, ['global'])                               # 'selected' comes from its saved samples
        self.assertEqual(result['approved'], 'global')
        self.assertEqual([x['name'] for x in result['candidates']], ['selected', 'global'])

    def test_all_rejected(self):
        self.subject(0.75)
        self.run_veto({'selected': 0.25, 'global': 0.25})
        loaded, result = self.run_veto({'selected': 0.25, 'global': 0.25})
        self.assertIsNone(result['approved'])

    def test_a_changed_evaluation_does_not_reuse_old_samples(self):
        self.subject(0.75)
        self.run_veto({'selected': 0.75})
        (self.root / 'veto' / 'result.json').unlink()
        self.c.VERSION, saved = self.c.VERSION + '-changed', self.c.VERSION    # e.g. other grading rules
        try:
            loaded, result = self.run_veto({'selected': 0.25, 'global': 0.75})
        finally:
            self.c.VERSION = saved
        self.assertEqual(loaded, ['selected'])                              # evaluated again, not taken from the old run
        self.assertIsNone(result)

    def test_quantization_must_match(self):
        self.subject(0.75)
        (self.root / 'work' / 'heldout_subject.json').write_text(json.dumps({'quantization': 'bf16'}))
        with self.assertRaises(RuntimeError):
            self.run_veto({'selected': 0.75})


class PairsStageHandOff(CellsBase):
    """Section 6 with STAGE = "pairs" writes pairs.jsonl and pairs.manifest.json; the fusion notebook reads and checks them."""
    def test_manifest_reaches_the_fusion_notebook(self):
        pool = [problem(f'p{i}', expected=12) for i in range(4)]
        problems = pool + self.heldout
        self.rate['pi'] = 0.5                                             # two of the four samples right: every problem pairs up
        local = self.root / 'model';local.mkdir()
        (local / 'tokenizer.json').write_text('{"t": 1}')
        (local / 'chat_template.jinja').write_text('{{ messages }}')
        env = self.env(problems=problems)
        env.update(STAGE='pairs', LLM='pi', SAMPLES_POOL=4, MAX_PAIR_RATIO=2.0, GPU_NAME='fake', LOCAL_MODEL=str(local),
                   SUBJECT_PIN={'repo': 's/s', 'revision': 'a' * 40, 'subfolder': ''},
                   PROMPT_IDS={p['pid']: [i % 4, 7] for i, p in enumerate(problems)})
        # samples k of a problem: right when k < 2 (the stand-in reads the first prompt id; give each sample its own)
        def generate(llm, prompt_ids, n, params, max_tokens, seeds):
            return [[{'text': '</think><answer>' + ('12' if k < n // 2 else '13') + '</answer>', 'token_ids': [1, 2, 3 + k],
                      'finish_reason': 'stop'} for k in range(n)] for _ in prompt_ids]
        env['cp'].generate = generate
        exec(compile(self.samples_cell, 'pairs-cell', 'exec'), env)
        work = self.root / 'work'
        manifest = json.loads((work / 'pairs.manifest.json').read_text())
        self.assertEqual(manifest['subject']['revision'], 'a' * 40)
        self.assertEqual(set(manifest['tokenizer']), {'tokenizer.json', 'chat_template.jinja'})
        self.assertEqual(manifest['pairs_sha256'], self.c.sha256_file(work / 'pairs.jsonl'))
        try:
            import test_tm2
            if not test_tm2.HAVE_TORCH:
                return
            pl = test_tm2.load()['qmerge_pipeline']
        except ImportError:
            return
        saved = pl.CONTRAST.get('tau')
        try:
            settings = {'contrast_pairs_file': str(work / 'pairs.jsonl')}
            rows = pl.contrast_setup(settings)
            self.assertEqual(len(rows), 8)                                    # four pairs
            pl.check_pairs_subject({**settings, 'S_repo': 's/s', 'S_revision': 'a' * 40, 'S_subfolder': ''}, local)
        finally:
            pl.CONTRAST['tau'] = saved
