"""Qwen38_pi_ContrastPairs.ipynb: the embedded module contrast_pairs (standard library only).

Problem parsing and selection, answer extraction and grading, pairing, the pairs-file check and the veto rule. The
vLLM parts need a GPU and are not run here.
"""
import hashlib
import importlib.util
import json
import re
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
        omni = c.omni_item({'domain': ['Mathematics -> Number Theory -> Divisibility'], 'difficulty': '5.5',
                            'problem': 'Find n.', 'answer': '$\\boxed{1{,}024}$'}, ['Number Theory'], 4.0)
        self.assertEqual((omni['expected'], omni['kind'], omni['group']), (1024, 'number', 'Number Theory -> Divisibility'))
        self.assertIsNone(c.omni_item({'domain': "['Mathematics -> Number Theory -> X']", 'difficulty': '3.0',
                                       'problem': 'p', 'answer': '5'}, ['Number Theory'], 4.0))   # too easy
        self.assertIsNone(c.omni_item({'domain': ['Mathematics -> Geometry -> X'], 'difficulty': '6',
                                       'problem': 'p', 'answer': '5'}, ['Number Theory'], 4.0))   # other domain
        self.assertIsNone(c.omni_item({'domain': ['Mathematics -> Number Theory -> X'], 'difficulty': '6',
                                       'problem': 'p', 'answer': '\\frac{1}{2}'}, ['Number Theory'], 4.0))
        nt = lambda q: c.omni_item({'domain': ['Mathematics -> Number Theory -> X'], 'difficulty': 5, 'problem': q, 'answer': '7'},
                                   ['Number Theory'], 4.0)
        self.assertIsNone(nt('Find the greatest GOOD number and the smallest BAD number.'))   # two answers asked, one given
        self.assertIsNotNone(nt('How many n are there such that n and 2n are both palindromes?'))
        jee = lambda **kw: {'subject': 'phy', 'description': 'JEE Adv 2016 Paper 1', 'index': '3', 'question': 'Q (A) a (B) b', **kw}
        self.assertEqual(c.jee_item(jee(type='MCQ', gold='B'), ['phy'])['kind'], 'letter')
        self.assertEqual(c.jee_item(jee(type='MCQ(multiple)', gold='DAB'), ['phy'])['expected'], 'ABD')
        self.assertEqual(c.jee_item(jee(type='Integer', gold='7'), ['phy'])['expected'], 7)
        self.assertEqual(c.jee_item(jee(type='Numeric', gold='0.83'), ['phy'])['kind'], 'numeric')
        self.assertIsNone(c.jee_item(jee(type='MCQ', gold='B', subject='math'), ['phy', 'chem']))
        m = c.musr_item({'narrative': 'A story.', 'question': 'Who?', 'choices': "['Ann', 'Bob', 'Cy']",
                         'answer_index': 1, 'answer_choice': 'Bob'}, 'murder_mystery.csv')
        self.assertEqual((m['expected'], m['options'], m['group']), ('B', 3, 'murder_mystery'))
        self.assertIn('C. Cy', m['question'])
        self.assertIsNone(c.musr_item({'narrative': 'A', 'question': 'Q', 'choices': "['x', 'y']", 'answer_index': 1,
                                       'answer_choice': 'x'}, 'f.csv'))                    # inconsistent row
        x = c.lcb_item({'question_id': '1', 'id': 'sample_0', 'code': 'def f(a):\n    return a', 'input': 'f(a = 1)',
                        'output': '1', 'difficulty': 'medium'}, ['medium', 'hard'])
        self.assertEqual((x['expected'], x['kind']), ('1', 'literal'))
        self.assertIsNone(c.lcb_item({'question_id': '1', 'id': 's', 'code': 'def f(a): return a', 'input': 'f(1)',
                                      'output': '1', 'difficulty': 'easy'}, ['medium', 'hard']))
        z = c.ceval_item({'id': 3, 'question': '问', 'A': '1', 'B': '2', 'C': '3', 'D': '4', 'answer': 'D'}, 'college_physics')
        self.assertEqual((z['expected'], z['kind'], z['lang']), ('D', 'letter_zh', 'zh'))

    def test_candidates_read_every_source(self):
        c = self.c
        rows = {
            'test.jsonl': [{'domain': ['Mathematics -> Number Theory -> Primes'], 'difficulty': 4.5, 'problem': 'a', 'answer': '5'}],
            'test.json': [{'subject': 'chem', 'description': 'd', 'index': 1, 'type': 'Integer', 'gold': '3', 'question': 'q'}],
            'murder_mystery.csv': [{'narrative': 'n', 'question': 'q', 'choices': "['a', 'b']", 'answer_index': 0, 'answer_choice': 'a'}],
            'object_placements.csv': [], 'team_allocation.csv': [],
            'data/test-00000-of-00001.parquet': [{'question_id': 1, 'id': 's', 'code': 'def f(): return 2', 'input': 'f()',
                                                  'output': '2', 'difficulty': 'hard'}],
        }
        fetch = lambda repo, rev, name: name
        read = lambda path: rows.get(path, [{'id': 1, 'question': '问', 'A': '1', 'B': '2', 'C': '3', 'D': '4', 'answer': 'A'}])
        got = {cat: c.candidates(cat, fetch, read) for cat in c.SOURCES}
        self.assertEqual([i['expected'] for i in got['math']], [5])
        self.assertEqual([i['expected'] for i in got['science']], [3])
        self.assertEqual([i['expected'] for i in got['code_reasoning']], ['2'])
        self.assertEqual(len(got['chinese_mc']), 2 * len(c.CEVAL_HARD))          # val and dev of every hard subject
        self.assertEqual(len(got['logic']), 1)
        self.assertTrue(all('source' in i for items in got.values() for i in items))

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
        multi = problem('m', 'science', 'letters', 'ABD')
        for text, want in (('ABD', True), ('A, B, D', True), ('(A)(B)(D)', True), ('D B A', True), ('A and B and D', True),
                           ('AB', False), ('ABCD', False), ('E', None), ('None of these', None), ('', None)):
            self.assertEqual(c.grade(multi, text), want, text)
        num = problem('n', 'science', 'numeric', 0.83)
        for text, want in (('0.83', True), ('0.835', True), ('0.82', True), ('0.85', False), ('about 0.8', None)):
            self.assertEqual(c.grade(num, text), want, text)
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


class StartVllm(unittest.TestCase):
    """make_llm with a stand-in for vllm.LLM: a failed start is tried again with the same (text-only) settings; only an
    argument vLLM rejects, or a second failure, drops the text-only setting."""
    def start(self, outcomes):
        c = load()
        calls = []

        class LLM:
            def __init__(self, **kw):
                calls.append('limit_mm_per_prompt' in kw)
                outcome = outcomes[len(calls) - 1]
                if outcome is not None:
                    raise outcome
        fake = type(sys)('vllm');fake.LLM = LLM
        saved = sys.modules.get('vllm');sys.modules['vllm'] = fake
        try:
            c.make_llm('/m', 100)
        finally:
            if saved is None:
                sys.modules.pop('vllm', None)
            else:
                sys.modules['vllm'] = saved
        return calls

    def test_retry_same_settings_first(self):
        self.assertEqual(self.start([RuntimeError('Engine core initialization failed'), None]), [True, True])

    def test_then_without_text_only(self):
        self.assertEqual(self.start([RuntimeError('x'), RuntimeError('x'), None]), [True, True, False])

    def test_rejected_argument(self):
        self.assertEqual(self.start([TypeError('unexpected keyword limit_mm_per_prompt'), None]), [True, False])


class AutoDisconnect(unittest.TestCase):
    """The cells both notebooks share: with AUTO_DISCONNECT, a finished run and an error both flush Drive and release the
    runtime (an error is saved to DRIVE_DIR/run_logs first); without it nothing is released. Colab and IPython are
    stand-ins here."""
    NOTEBOOKS = (NOTEBOOK, HERE.parent / 'Qwen38_pi_AuxMix_e16_FP8.ipynb')

    def cells(self, path):
        nb = json.loads(Path(path).read_text(encoding='utf-8'))
        src = [''.join(c['source']) for c in nb['cells']]
        arm = next(s for s in src if s.startswith('# 夜里无人看着时用'))
        final = next(s for s in src if s.startswith('if AUTO_DISCONNECT:'))
        settings = next(s for s in src if re.search(r'^AUTO_DISCONNECT = (True|False)', s, re.M))
        self.assertLess(src.index(settings), src.index(arm))
        self.assertEqual(src.index(final), len(src) - 1)                      # the very last cell
        return arm, final

    def run_cells(self, path, enabled, error=None):
        arm, final = self.cells(path)
        events = []
        colab = type(sys)('google.colab')
        colab.drive = type(sys)('google.colab.drive');colab.drive.flush_and_unmount = lambda: events.append('flush')
        colab.runtime = type(sys)('google.colab.runtime');colab.runtime.unassign = lambda: events.append('unassign')
        google = type(sys)('google');google.colab = colab
        handlers = []

        class Shell:
            def set_custom_exc(self, kinds, handler):
                handlers.append((kinds, handler))

            def showtraceback(self, *a, **k):
                events.append('traceback')
        ipython = type(sys)('IPython');shell = Shell();ipython.get_ipython = lambda: shell
        names = ('google', 'google.colab', 'google.colab.drive', 'google.colab.runtime', 'IPython')
        saved = {n: sys.modules.get(n) for n in names}
        sys.modules.update({'google': google, 'google.colab': colab, 'google.colab.drive': colab.drive,
                            'google.colab.runtime': colab.runtime, 'IPython': ipython})
        try:
            with tempfile.TemporaryDirectory() as tmp:
                env = {'DRIVE_DIR': tmp, 'AUTO_DISCONNECT': enabled, 'NOTEBOOK_TAG': 'test'}
                exec(compile(arm, 'arm', 'exec'), env)
                if error is not None:
                    self.assertEqual(len(handlers), 1)
                    kinds, handler = handlers[0]
                    self.assertNotIn(KeyboardInterrupt, kinds)                    # the stop button does not release it
                    handler(shell, type(error), error, None)
                    logs = list((Path(tmp) / 'run_logs').glob('test-*-error.txt'))
                    self.assertEqual(len(logs), 1)
                    self.assertIn(str(error), logs[0].read_text(encoding='utf-8'))
                else:
                    exec(compile(final, 'final', 'exec'), env)
                return events, handlers
        finally:
            for n, m in saved.items():
                if m is None:
                    sys.modules.pop(n, None)
                else:
                    sys.modules[n] = m

    def test_both_notebooks(self):
        for path in self.NOTEBOOKS:
            with self.subTest(path.name):
                events, handlers = self.run_cells(path, True)
                self.assertEqual(events, ['flush', 'unassign'])
                events, handlers = self.run_cells(path, True, ValueError('vLLM failed'))
                self.assertEqual(events, ['traceback', 'flush', 'unassign'])
                events, handlers = self.run_cells(path, False)
                self.assertEqual((events, handlers), ([], []))


class AutoDisconnectTestNotebook(AutoDisconnect):
    """AutoDisconnect_test.ipynb carries exactly the cells of the two real notebooks, and its own cells run."""
    def test_same_cells_as_the_real_notebooks(self):
        test_nb = HERE.parent / 'AutoDisconnect_test.ipynb'
        mine = self.cells(test_nb)
        for path in self.NOTEBOOKS:
            self.assertEqual(self.cells(path), mine, path.name)
        nb = json.loads(test_nb.read_text(encoding='utf-8'))
        src = [''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code']
        self.assertIn('MODE = "finish"', src[0])
        self.assertIn('raise RuntimeError', src[3])

    def test_both_notebooks(self):            # covered by the parent class; not repeated here
        pass
