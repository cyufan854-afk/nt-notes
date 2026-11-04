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
        self.assertTrue(c.grade(problem('u', 'code_reasoning', 'literal', "'abc'"), 'abc'))
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


class VetoCell(unittest.TestCase):
    """Section 7 of the notebook, run with stand-ins for vLLM: candidates in order, the first that passes is taken, and
    one model per process (a second one waits for a restarted session)."""
    def run_cell(self, root, request, accuracy):
        c = load()
        nb = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
        code = next(''.join(x['source']) for x in nb['cells'] if ''.join(x['source']).startswith('if STAGE == "veto":'))
        loaded = []
        heldout = [problem(f'h{i}', split='heldout') for i in range(4)]

        def run_samples(llm, problems, split, n, out_dir, tag):
            return {p['pid']: {'samples': [{'correct': i < accuracy[llm] * 4, 'finish_reason': 'stop', 'pred': 'x'}]}
                    for i, p in enumerate(problems)}

        def make_llm(path, *args):
            name = loaded_name[-1]
            loaded.append(name)
            return name
        loaded_name = []
        fake_cp = type(sys)('fake_cp')
        fake_cp.make_llm = make_llm
        fake_cp.accuracy = c.accuracy
        fake_cp.veto = c.veto
        fake_cp.atomic_json = c.atomic_json

        def copytree(src, dst):
            loaded_name.append(Path(src).name[4:])
            Path(dst).mkdir(parents=True, exist_ok=True)
        env = {'STAGE': 'veto', 'DRIVE_DIR': str(root), 'WORK': root / 'work', 'PROBLEMS': heldout, 'json': json, 'Path': Path,
               'shutil': type(sys)('fake_shutil'), 'cp': fake_cp, 'run_samples': run_samples, 'SAMPLES_HELDOUT': 2,
               'MAX_MODEL_LEN': 100, 'VLLM': {'gpu_memory_utilization': 0.9, 'quantization': 'fp8', 'max_num_seqs': 4}, 'SEED': 0,
               'VERSIONS': {}, 'VETO_MAX_DROP': 0.05}
        env['shutil'].copytree = copytree
        env['shutil'].rmtree = lambda *a, **k: None
        (root / 'veto').mkdir(parents=True, exist_ok=True)
        (root / 'veto' / 'request.json').write_text(json.dumps(request))
        subject = c.accuracy(heldout, {p['pid']: {'samples': [{'correct': i < 3, 'finish_reason': 'stop', 'pred': 'x'}]}
                                       for i, p in enumerate(heldout)})
        (root / 'work').mkdir(exist_ok=True)
        (root / 'work' / 'heldout_subject.json').write_text(json.dumps({'accuracy': subject}))
        exec(compile(code, 'veto-cell', 'exec'), env)
        result = root / 'veto' / 'result.json'
        return loaded, (json.loads(result.read_text()) if result.exists() else None)

    def request(self, root):
        return {'candidates': [{'name': n, 'directory': str(root / ('src-' + n)), 'fingerprint': n * 8} for n in ('selected', 'global')]}

    def test_first_passing_candidate_ends_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            loaded, result = self.run_cell(root, self.request(root), {'selected': 0.75, 'global': 0.75})
            self.assertEqual(loaded, ['selected'])
            self.assertEqual(result['approved'], 'selected')

    def test_one_model_per_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            loaded, result = self.run_cell(root, self.request(root), {'selected': 0.25, 'global': 0.75})
            self.assertEqual((loaded, result), (['selected'], None))           # stops for a restarted session
            loaded, result = self.run_cell(root, self.request(root), {'selected': 0.25, 'global': 0.75})
            self.assertEqual(loaded, ['global'])                               # 'selected' comes from its saved evaluation
            self.assertEqual(result['approved'], 'global')
            self.assertEqual([x['name'] for x in result['candidates']], ['selected', 'global'])

    def test_all_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_cell(root, self.request(root), {'selected': 0.25, 'global': 0.25})
            loaded, result = self.run_cell(root, self.request(root), {'selected': 0.25, 'global': 0.25})
            self.assertIsNone(result['approved'])
