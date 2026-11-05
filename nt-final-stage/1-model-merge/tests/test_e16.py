"""e16: the contrast-pair objective, its guard, the token-budgeted pair subsets, the GPU-oriented scoring changes
(windowed logits, windowed loss gradient, hidden states of the gradient pass in another directory, restart when they
are gone) and the generation-veto hand-off, on tiny random models and synthetic data.

    python3 -m unittest discover -s tests -v          (in 1-model-merge/)
"""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tm2 import HAVE_TORCH, NOTEBOOK, load  # noqa: E402
import test_contrast_pairs  # noqa: E402

try:
    import transformers  # noqa: F401
    HAVE_TRANSFORMERS = HAVE_TORCH
except ImportError:
    HAVE_TRANSFORMERS = False


def pair_rows(spec, wrong_first=()):
    """spec: [(category, right length, wrong length)] -> pair rows as Qwen38_pi_ContrastPairs.ipynb writes them."""
    rows = []
    for n, (category, right, wrong) in enumerate(spec):
        prompt = [1, 2, 3 + n]
        two = [{'id': f'p{n}/correct', 'pair': f'p{n}', 'role': 'correct', 'category': category, 'prompt_ids': prompt,
                'response_ids': list(range(10, 10 + right))},
               {'id': f'p{n}/wrong', 'pair': f'p{n}', 'role': 'wrong', 'category': category, 'prompt_ids': prompt,
                'response_ids': list(range(20, 20 + wrong))}]
        rows += two[::-1] if n in wrong_first else two
    return rows


@unittest.skipUnless(HAVE_TORCH, 'needs numpy, torch and safetensors')
class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m = load()
        cls.core, cls.rt, cls.comp, cls.pl = m['qmerge_core'], m['qmerge_runtime'], m['qmerge_components'], m['qmerge_pipeline']

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='e16-'))
        self.saved_tau = self.pl.CONTRAST.get('tau')

    def tearDown(self):
        self.pl.CONTRAST['tau'] = self.saved_tau
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_pairs(self, rows, name='pairs.jsonl', subject=None, tokenizer=None):
        path = self.tmp / name
        path.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
        manifest = {'subject': subject or {'repo': 's/s', 'revision': 'a' * 40, 'subfolder': ''}, 'tokenizer': tokenizer or {},
                    'pairs_sha256': self.core.sha_file(path)}
        (self.tmp / 'pairs.manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        return path


class PairFile(Base):
    def test_read_and_check(self):
        rows = pair_rows([('math', 3, 4), ('logic', 2, 2)])
        self.assertEqual(self.core.read_jsonl(self.write_pairs(rows), 'pairs'), rows)
        bad = [
            rows[:3],                                                            # a pair without its wrong trace
            [rows[0], {**rows[1], 'prompt_ids': [9]}] + rows[2:],                # two different problems
            [rows[0], {**rows[1], 'category': 'logic'}] + rows[2:],
            [rows[0], {**rows[1], 'role': 'correct'}] + rows[2:],                # the same role twice
            [rows[0], {**rows[1], 'response_ids': [1.5]}] + rows[2:],
            [rows[0], {**rows[1], 'response_ids': []}] + rows[2:],
            [rows[0], {**rows[1], 'role': 'maybe'}] + rows[2:],
        ]
        for n, case in enumerate(bad):
            with self.assertRaises(ValueError, msg=n):
                self.core.validate_pair_rows(case)

    def test_rows_written_by_the_contrast_notebook_pass(self):
        c = test_contrast_pairs.load()
        probs = [test_contrast_pairs.problem('mixed'), test_contrast_pairs.problem('other', category='logic', kind='letter', expected='A')]
        sample = test_contrast_pairs.sample
        results = {'mixed': {'samples': [sample(0, True, 100), sample(1, False, 130)]},
                   'other': {'samples': [sample(0, True, 40, pred='A'), sample(1, False, 50, pred='B')]}}
        rows, report = c.build_pairs(probs, results, {p['pid']: [7, 8, 9] for p in probs}, max_ratio=2.0, seed=0)
        self.assertEqual(report['pairs'], 2)
        self.core.validate_pair_rows(rows)
        questions, where = self.pl.pair_view(rows)
        self.assertEqual([q['id'] for q in questions], ['mixed', 'other'])
        self.assertTrue(all(rows[c]['role'] == 'correct' and rows[w]['role'] == 'wrong' for c, w in where))

    def test_stored_ids_are_scored_as_they_are(self):
        row = pair_rows([('math', 5, 3)])[0]
        ids, p, info = self.core.pack_reference(None, row, {}, 100, 50)      # no tokenizer needed
        self.assertEqual(ids.tolist(), [row['prompt_ids'] + row['response_ids']])
        self.assertEqual((p, info['prompt_tokens'], info['response_tokens']), (3, 3, 5))
        self.assertIn('not re-tokenized', info['encoding'])
        with self.assertRaises(ValueError):
            self.core.pack_reference(None, row, {}, 100, 4)                    # never truncated


class Objective(Base):
    def setUp(self):
        super().setUp()
        self.rows = pair_rows([('math', 3, 3), ('math', 3, 3), ('logic', 3, 3)], wrong_first=(1,))
        # traces in file order: p0 c, p0 w, p1 w, p1 c, p2 c, p2 w
        self.trace = [1.0, 1.5, 0.9, 0.6, 2.0, 2.2]

    def test_questions_are_pairs(self):
        pl = self.pl
        questions, where = pl.pair_view(self.rows)
        self.assertEqual([q['id'] for q in questions], ['p0', 'p1', 'p2'])
        self.assertEqual(where, [(0, 1), (3, 2), (4, 5)])
        _, values = pl.question_values(self.rows, self.trace)
        self.assertEqual([round(v, 6) for v in values], [-0.5, -0.3, -0.2])
        import numpy as np
        _, arr = pl.question_values(self.rows, np.asarray(self.trace))
        self.assertTrue(np.allclose(arr, [-0.5, -0.3, -0.2]))
        plain = [{'id': 'a', 'category': 'x'}, {'id': 'b', 'category': 'y'}]
        self.assertEqual(pl.question_values(plain, [1.0, 2.0])[1], [1.0, 2.0])
        self.assertIsNone(pl.guard_value(plain, [1.0, 2.0]))

    def test_summary_and_guard(self):
        s = self.pl.summarize_losses(self.rows, self.trace)
        self.assertAlmostEqual(s['category_nll']['math'], -0.4)
        self.assertAlmostEqual(s['category_nll']['logic'], -0.2)
        self.assertAlmostEqual(s['mean_nll'], -0.3)                             # categories weigh the same
        self.assertAlmostEqual(s['guard'], ((1.0 + 0.6) / 2 + 2.0) / 2)         # the right traces only
        self.assertEqual(s['trace_losses'], self.trace)
        self.assertEqual(self.pl.trace_losses_of(s), self.trace)
        self.assertNotIn('guard', self.pl.summarize_losses([{'id': 'a', 'category': 'x'}], [1.0]))

    def test_guard_decides_feasibility(self):
        pl = self.pl
        base = {'category_nll': {'math': -0.4}, 'guard': 1.0, 'mean_nll': -0.4}
        better = {'category_nll': {'math': -0.6}, 'mean_nll': -0.6}
        pl.CONTRAST['tau'] = 0.05
        self.assertTrue(pl.proxy_feasible({**better, 'guard': 1.04}, base, 0.01))
        self.assertFalse(pl.proxy_feasible({**better, 'guard': 1.06}, base, 0.01))
        self.assertFalse(pl.proxy_feasible({**better, 'category_nll': {'math': -0.38}, 'guard': 1.0}, base, 0.01))
        self.assertIn('超出', pl.trial_text({**better, 'guard': 1.06}, base))
        self.assertIn('提升 +0.20000', pl.trial_text({**better, 'guard': 1.0}, base))
        self.assertAlmostEqual(pl.search_value({**better, 'guard': 1.04}, base), -0.6)
        self.assertAlmostEqual(pl.search_value({**better, 'guard': 1.10}, base), -0.6 + 10 * 0.05)   # the surrogate avoids the excess
        pl.CONTRAST['tau'] = None                                               # the old objective: no guard
        self.assertTrue(pl.proxy_feasible({**better, 'guard': 9.0}, base, 0.01))
        self.assertAlmostEqual(pl.search_value({**better, 'guard': 9.0}, base), -0.6)


class Subsets(Base):
    def test_whole_pairs_within_the_budget(self):
        pl = self.pl
        rows = pair_rows([('math', 10, 12), ('math', 30, 30), ('math', 5, 6), ('logic', 8, 8), ('logic', 50, 40), ('code', 7, 9)])
        size = lambda rs: sum(len(r['prompt_ids']) + len(r['response_ids']) for r in rs)
        for budget in (40, 60, 80, 100, 150):
            sub = pl.pair_subset(rows, budget, 0)
            self.assertLessEqual(size(sub), budget)
            self.core.validate_pair_rows(sub)                                    # both traces of every pair
            self.assertEqual(sub, [r for r in rows if r in sub])                 # file order kept
            self.assertEqual(sub, pl.pair_subset(rows, budget, 0))               # deterministic
            if budget >= 80:                                                     # room for the smallest pair of each
                self.assertEqual({r['category'] for r in sub}, {'math', 'logic', 'code'})   # every category gets a turn
        self.assertEqual(pl.pair_subset(rows, None), rows)
        self.assertEqual(pl.pair_subset(rows, 10 ** 9, 0), rows)
        plain = [{'id': 'a', 'category': 'x'}]
        self.assertEqual(pl.pair_subset(plain, 1), plain)


class Setup(Base):
    def options(self):
        return {'device': 'auto', 'dtype': 'auto', 'attention': 'eager', 'max_tokens': 1024, 'max_response_tokens': 512,
                'token_chunk': 32, 'engine': 'auto', 'template_kwargs': {'enable_thinking': False}}

    def test_contrast_setup(self):
        pl = self.pl
        rows = pair_rows([('math', 3, 4)] * 4 + [('logic', 2, 2)] * 3)
        settings = {'contrast_pairs_file': str(self.write_pairs(rows)), 'contrast_options': {'tau': 0.1}}
        got = pl.contrast_setup(settings)
        self.assertEqual(got, rows)
        self.assertEqual(pl.CONTRAST['tau'], 0.1)
        self.assertEqual((settings['proxy_max_category_drop'], settings['search_min_items'], settings['search_min_per_category']),
                         (0.01, 40, 3))
        self.assertEqual(settings['component_options']['rows'], 'search')
        small = {'contrast_pairs_file': settings['contrast_pairs_file'], 'contrast_options': {'search_max_tokens': 30}}
        self.assertLess(len(pl.contrast_setup(small)), len(rows))
        for wrong in ({'tau': 0}, {'tau': 1.5}, {'taus': 0.1}):
            with self.assertRaises(ValueError):
                pl.contrast_setup({'contrast_pairs_file': settings['contrast_pairs_file'], 'contrast_options': wrong})
        self.assertIsNone(pl.contrast_setup({'contrast_pairs_file': ''}))
        self.assertIsNone(pl.CONTRAST['tau'])
        # the old objective ignores a pairs file that is still filled in
        self.assertIsNone(pl.contrast_setup({'contrast_pairs_file': settings['contrast_pairs_file'], 'objective': 'reference_nll'}))
        old, _ = pl.resolve_runtime({'proxy_options': self.options(), 'contrast_pairs_file': 'x.jsonl', 'objective': 'reference_nll'})
        self.assertEqual(old['proxy_options']['max_tokens'], 1024)

    def test_thin_categories_are_left_out(self):
        rows = pair_rows([('math', 3, 4)] * 4 + [('logic', 2, 2)] * 3 + [('code', 2, 2)])
        settings = {'contrast_pairs_file': str(self.write_pairs(rows))}
        got = self.pl.contrast_setup(settings)
        self.assertEqual({r['category'] for r in got}, {'math', 'logic'})        # one code pair: below 3
        self.assertEqual(len(got), 14)

    def test_runtime_options_for_long_traces(self):
        settings, info = self.pl.resolve_runtime({'proxy_options': self.options(), 'contrast_pairs_file': 'x.jsonl'})
        o = settings['proxy_options']
        self.assertEqual((o['max_tokens'], o['max_response_tokens'], o['engine'], o['dtype']), (12288, 10240, 'layerwise', 'float32'))
        if info['kind'] == 'cpu':
            self.assertEqual((o['device'], o['attention']), ('cpu', 'eager'))
        else:
            self.assertEqual((o['attention'], o['matmul']), ('sdpa', 'tf32'))
        old, _ = self.pl.resolve_runtime({'proxy_options': self.options()})
        self.assertEqual(old['proxy_options']['max_tokens'], 1024)

    def test_contrast_selection_needs_a_gpu(self):
        rows = pair_rows([('math', 3, 4)] * 4)
        settings = {'work': str(self.tmp / 'work'), 'run': True, 'objective': 'contrast', 'proxy_options': self.options(),
                    'contrast_pairs_file': str(self.write_pairs(rows))}
        _, info = self.pl.resolve_runtime({'proxy_options': self.options()})
        if info['kind'] != 'cpu':
            self.skipTest('this machine has a GPU')
        out = self.pl.run_pipeline(settings, None, None, '')
        self.assertEqual(out['status'], 'needs_gpu_runtime')
        self.assertFalse(out['heavy_computation_started'])

    def test_no_pairs_no_fallback(self):
        settings = {'work': str(self.tmp / 'work'), 'run': True, 'objective': 'contrast', 'proxy_options': self.options()}
        out = self.pl.run_pipeline(settings, None, None, '')
        self.assertEqual(out['status'], 'waiting_for_contrast_pairs')
        self.assertFalse(out['heavy_computation_started'])


@unittest.skipUnless(HAVE_TRANSFORMERS, 'needs transformers')
class TinyModel(Base):
    """A two-layer random Llama, saved as a checkpoint, scored by the real LayerwiseScorer."""
    def model(self):
        import torch
        from transformers import LlamaConfig, LlamaForCausalLM
        torch.manual_seed(0)
        cfg = LlamaConfig(vocab_size=50, hidden_size=32, intermediate_size=64, num_hidden_layers=2, num_attention_heads=4,
                          num_key_value_heads=2, max_position_embeddings=128, tie_word_embeddings=False)
        return LlamaForCausalLM(cfg).eval()

    def checkpoint(self, model, name):
        path = self.tmp / name
        model.save_pretrained(path, safe_serialization=True)
        return path

    def scorer(self, path, window):
        options = {'device': 'cpu', 'dtype': 'float32', 'attention': 'eager', 'token_chunk': 4, 'logits_window': window}
        return self.rt.LayerwiseScorer(path, options, self.rt.checkpoint_catalogue(path))

    def ids(self, n, seed):
        import torch
        g = torch.Generator().manual_seed(seed)
        return torch.randint(0, 50, (1, n), generator=g)

    def test_windowed_logits_give_the_same_nll(self):
        model = self.model();ids = self.ids(40, 1)
        whole = self.rt.score_forward(model, ids, 7, 'cpu', 4)
        for window in (1, 5, 31, 32, 200):
            part = self.rt.score_forward(model, ids, 7, 'cpu', 4, window=window)
            self.assertAlmostEqual(part['nll'], whole['nll'], places=5)
            self.assertEqual(part['tokens'], whole['tokens'])
        path = self.checkpoint(model, 'S')
        weights = self.rt.CheckpointWeights(path)
        try:
            for window in (5, 10 ** 6):
                got = self.scorer(path, window).run(weights, [('a', ids, 7), ('b', self.ids(25, 2), 3)], progress=False)
                self.assertAlmostEqual(got['a']['nll'], whole['nll'], places=5)
        finally:
            weights.close()

    def test_ram_memo_serves_a_head_only_rescore(self):
        model = self.model();path = self.checkpoint(model, 'S')
        weights = self.rt.CheckpointWeights(path)
        sc = self.scorer(path, 5);items = [('a', self.ids(30, 8), 6), ('b', self.ids(20, 9), 3)]
        store = {};calls = []
        layer = sc._layer
        def counted(i, call, hidden):
            calls.append(i)
            return layer(i, call, hidden)
        sc._layer = counted
        try:
            first = sc.run(weights, items, memo=self.rt.RamLayerMemo(store, {0: 'mid', 1: 'last'}, reserve=0), digests={}, progress=False)
            self.assertEqual(list(store), ['last']);self.assertEqual(len(calls), 4)
            again = sc.run(weights, items, memo=self.rt.RamLayerMemo(store, {0: 'mid', 1: 'last'}, reserve=0), digests={}, progress=False)
            self.assertEqual(len(calls), 4)                                    # no decoder layer ran the second time
            self.assertEqual(again, first)
            other = sc.run(weights, items, memo=self.rt.RamLayerMemo(store, {0: 'mid2', 1: 'last2'}, reserve=0), progress=False)
            self.assertEqual(list(store), ['last2'])                            # only the latest run is kept
            self.assertEqual(other, first)
        finally:
            weights.close()

    def test_windowed_loss_gradient(self):
        import torch
        path = self.checkpoint(self.model(), 'S')
        weights = self.rt.CheckpointWeights(path)
        ids = self.ids(40, 3);hidden = torch.randn(1, 40, 32, generator=torch.Generator().manual_seed(4))
        out = {}
        try:
            for window in (5, 10 ** 6):
                sc = self.scorer(path, window)
                sc._load(sc.outer, weights, None)
                out[window] = self.comp._loss_and_grad(sc, hidden, ids, 7)
                sc._release(sc.outer)
        finally:
            weights.close()
        (v1, c1, g1), (v2, c2, g2) = out[5], out[10 ** 6]
        self.assertAlmostEqual(v1, v2, places=5)
        self.assertAlmostEqual(c1, c2, places=5)
        self.assertAlmostEqual(v1, c1, places=4)
        self.assertTrue(torch.allclose(g1, g2, rtol=1e-4, atol=1e-7))

    def gradient_pass(self, store, states=None):
        import torch
        S = self.model();sp = self.checkpoint(S, 'S') if not (self.tmp / 'S').is_dir() else self.tmp / 'S'
        if not (self.tmp / 'F').is_dir():
            F = self.model()
            with torch.no_grad():
                g = torch.Generator().manual_seed(5)
                for name, p in F.named_parameters():
                    if '.layers.' in name and p.ndim == 2:p.add_(0.02 * torch.randn(p.shape, generator=g))
            self.checkpoint(F, 'F')
        sc = self.scorer(sp, 5)
        cat = self.rt.checkpoint_catalogue(sp)
        targets = {k: 'matrix' for k in cat if '.layers.' in k and k.endswith(('q_proj.weight', 'down_proj.weight'))}
        items = [('q1', self.ids(30, 6), 5), ('q2', self.ids(22, 7), 4)]
        options = {'bands': [2, 4], 'subject_rank': 0, 'whiten': True, 'input_tokens': 64, 'seed': 0, 'damp': 1e-2,
                   'preflight': False, 'segment': 1}
        f, s = self.rt.CheckpointWeights(self.tmp / 'F'), self.rt.CheckpointWeights(sp)
        try:
            return self.comp.gradient_components(sc, f, s, items, targets, store, options, progress=False, states=states)
        finally:
            f.close();s.close()

    def test_states_elsewhere_and_restart(self):
        ref = self.gradient_pass(self.tmp / 'store1')
        moved = self.gradient_pass(self.tmp / 'store2', states=self.tmp / 'states2')
        self.assertEqual(moved['scores'], ref['scores'])
        self.assertEqual(moved['nll'], ref['nll'])
        for place in ('store1', 'store2', 'states2'):
            self.assertEqual(sorted(p.name for p in (self.tmp / place).glob('*.safetensors') if not p.name.startswith('decomp')), [], place)
        # A new session: the progress says "backward", but the kept states were on the old session's disk.
        store3 = self.tmp / 'store3';store3.mkdir()
        (store3 / 'progress.json').write_text(json.dumps({'phase': 'backward', 'next_segment': 0, 'segment': 1}))
        again = self.gradient_pass(store3, states=self.tmp / 'states3')
        self.assertEqual(again['scores'], ref['scores'])


class Veto(Base):
    def setUp(self):
        super().setUp()
        pl = self.pl
        self.saved = pl.build_chosen, pl.persist_candidate
        self.built = []

        def build(context, record):
            path = self.tmp / 'local' / record['variant'];path.mkdir(parents=True, exist_ok=True)
            self.built.append(record['variant'])
            return path, {}

        def persist(context, path, store=None, keep_others=False, prefix=''):
            self.assertTrue(keep_others)
            fp = (prefix.strip('-') * 64)[:64]
            (Path(store) / (prefix + fp[:24])).mkdir(parents=True, exist_ok=True)
            return fp
        pl.build_chosen, pl.persist_candidate = build, persist
        self.saved_fp = pl.runtime.checkpoint_fingerprint
        self.tampered = False

        def fingerprint(directory, strict=False):
            name = Path(directory).name.split('-', 1)[0]
            return ('tampered' if self.tampered else (name * 64)[:64]), {}
        pl.runtime.checkpoint_fingerprint = fingerprint
        self.context = {'root': self.tmp / 'work', 'identity': {'inputs': 'x'}}
        self.record = {'recipe': {'lambda_backbone': 0.1}, 'pruning': {'p': 1}, 'variant': 'step:1', 'tensor_digests': {'t': 'sel'},
                       'checkpoint_fingerprint': None, 'proxy_mean_nll': -0.2, 'subject_proxy_mean_nll': 0.0,
                       'category_nll': {'math': -0.2}, 'global_candidate': {
                           'mean_nll': -0.1, 'category_nll': {'math': -0.1}, 'guard': 1.0, 'tensor_digests': {'t': 'glob'},
                           'checkpoint_fingerprint': 'fpg'}}

    def tearDown(self):
        self.pl.build_chosen, self.pl.persist_candidate = self.saved
        self.pl.runtime.checkpoint_fingerprint = self.saved_fp
        super().tearDown()

    def answer(self, approved, request=None):
        folder = self.tmp / 'work' / 'veto'
        request = request or json.loads((folder / 'request.json').read_text())
        (folder / 'result.json').write_text(json.dumps({'request': request, 'approved': approved, 'subject': {'overall': 0.8},
                                                        'candidates': [], 'max_drop': 0.05}))

    def test_hand_off(self):
        pl = self.pl
        first = pl.veto_stage(self.context, self.record)
        self.assertEqual(first['status'], 'waiting_for_veto')
        self.assertEqual([c['name'] for c in first['candidates']], ['selected', 'global'])
        self.assertEqual(self.built, ['step:1', 'global'])
        self.assertEqual(pl.veto_stage(self.context, self.record)['status'], 'waiting_for_veto')
        self.assertEqual(len(self.built), 2)                                    # not built again while waiting
        self.answer('global')
        done = pl.veto_stage(self.context, self.record)
        self.assertEqual(done['status'], 'approved')
        r = done['record']
        self.assertEqual((r['variant'], r['pruning'], r['tensor_digests'], r['checkpoint_fingerprint']), ('global', None, {'t': 'glob'}, 'fpg'))
        self.assertAlmostEqual(r['gain_nll'], 0.1)
        self.assertTrue(done['directory'].endswith('global-' + ('global' * 11)[:24]))
        self.answer(None)
        self.assertEqual(pl.veto_stage(self.context, self.record)['status'], 'veto_rejected')

    def test_a_new_selection_asks_again(self):
        pl = self.pl
        pl.veto_stage(self.context, self.record)
        self.answer('selected')
        changed = {**self.record, 'recipe': {'lambda_backbone': 0.2}}
        out = pl.veto_stage(self.context, changed)
        self.assertEqual(out['status'], 'waiting_for_veto')                     # the old answer was for another request
        self.assertFalse((self.tmp / 'work' / 'veto' / 'result.json').exists())
        only = {**self.record, 'global_candidate': None}
        self.assertEqual([n for n, _ in pl.veto_candidates(only)], ['selected'])

    def test_other_weights_ask_again(self):
        pl = self.pl
        pl.veto_stage(self.context, self.record)
        self.answer('selected')
        # same recipe and pruning, other weights (e.g. another max_relative_change): the old answer does not count
        changed = {**self.record, 'tensor_digests': {'t': 'other'}}
        self.assertEqual(pl.veto_stage(self.context, changed)['status'], 'waiting_for_veto')
        self.assertEqual(self.built[-2:], ['step:1', 'global'])
        self.answer('selected')
        self.tampered = True                                                    # the copy on Drive is not what was judged
        with self.assertRaises(ValueError):
            pl.veto_stage(self.context, changed)


class ComponentStageOverPairs(Base):
    """component_stage with the expensive passes replaced by a linear model of each trace's loss in the coefficients:
    'bad' raises the right traces' NLL and lowers the wrong ones' (it hurts the objective), 'good' the opposite."""
    NAMES = ('L0-3.mlp.bad', 'L0-3.attn.good', 'L4-7.mlp.noise')

    def setUp(self):
        super().setUp()
        import numpy as np
        pl = self.pl
        self.saved = {k: getattr(pl, k) for k in ('check_backward', 'evaluate_trial', 'component_gradients', 'component_targets',
                                                 'component_effects', 'pruning_spec', 'evaluate_variant')}
        rng = np.random.default_rng(0)
        self.rows = pair_rows([(('math', 'logic', 'code')[n % 3], 10, 10) for n in range(24)])
        sign = {r['id']: (1. if r['role'] == 'correct' else -1.) for r in self.rows}
        self.f = {r['id']: 1.0 + 0.1 * rng.standard_normal() for r in self.rows}
        self.s = {r['id']: self.f[r['id']] + (0.02 if r['role'] == 'correct' else -0.02) for r in self.rows}   # F is a bit better than S
        bad, good, noise = self.NAMES
        self.effect = {bad: {k: 0.05 * v for k, v in sign.items()}, good: {k: -0.05 * v for k, v in sign.items()},
                       noise: {r['id']: 0.002 * rng.standard_normal() for r in self.rows}}
        self.calls = {'check': None, 'variants': []}
        test = self

        def check_backward(context, rows):
            test.calls['check'] = [r['id'] for r in rows]
            return {'ok': True}

        def evaluate_trial(context, recipe, rows):
            return pl.summarize_losses(rows, [test.s[r['id']] for r in rows])

        def component_gradients(context, base, traces, opts):
            test.calls['traces'] = [r['id'] for r in traces]
            return {'id': 'g', 'questions': [r['id'] for r in traces], 'nll': [test.f[r['id']] for r in traces], 'scores': {}}

        def component_effects(grads, num_layers, blocks):
            ids = grads['questions']
            return ({c: np.asarray([test.effect[c][i] for i in ids]) for c in test.NAMES},
                    {c: [('k.' + c, 'all')] for c in test.NAMES}, {c: 1.0 for c in test.NAMES})

        def evaluate_variant(context, base, spec, rows, label):
            test.calls['variants'].append([r['id'] for r in rows])
            coef = spec['coefficients']
            values = [test.f[r['id']] + sum((float(coef.get(c, 1.)) - 1.) * test.effect[c][r['id']] for c in test.NAMES) for r in rows]
            return {**pl.summarize_losses(rows, values), 'tensor_digests': {'t': label}}

        pl.check_backward, pl.evaluate_trial, pl.component_gradients = check_backward, evaluate_trial, component_gradients
        pl.component_targets = lambda context, recipe: {}
        pl.component_effects, pl.evaluate_variant = component_effects, evaluate_variant
        pl.pruning_spec = lambda grads, members, coefficients: {'coefficients': dict(coefficients)}

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(self.pl, k, v)
        super().tearDown()

    def test_pairs_are_the_questions(self):
        pl = self.pl
        pl.CONTRAST['tau'] = 0.05
        cfg = {'component_options': {'rows': 'search', 'bootstrap': 300, 'plans': ['lenient', 'step:0.5', 'step:1'], 'adopt_probability': 0.6},
               'proxy_options': {}, 'proxy_max_category_drop': 0.01, 'contrast_options': {'component_max_tokens': 26 * 16},
               'require_all_donors': False, 'max_relative_change': 0.1}
        context = {'settings': cfg, 'scoring_engine': 'layerwise', 'num_layers': 8, 'root': self.tmp}
        base = {'recipe': {'lambda_backbone': 0.1}, 'tensor_digests': {'t': 'F'}, 'weights_digest': 'w',
                **pl.summarize_losses(self.rows, [self.f[r['id']] for r in self.rows])}
        out = pl.component_stage(context, base, self.rows, [])
        self.assertEqual(out['status'], 'done', out)
        self.assertEqual(self.calls['check'], [r['id'] for r in self.rows])            # the cached S scores of the whole search set
        traces = self.calls['traces']
        self.assertEqual(len(traces), 32)                                              # 16 whole pairs within the token budget
        sub = [r for r in self.rows if r['id'] in traces]
        self.core.validate_pair_rows(sub)
        for ids in self.calls['variants']:
            self.core.validate_pair_rows([r for r in self.rows if r['id'] in ids])    # every variant is scored on whole pairs
        self.assertEqual(out['rows'], 16)
        chosen = out['chosen']
        self.assertNotEqual(chosen['name'], 'global')
        self.assertLess(float(chosen['coefficients'].get(self.NAMES[0], 1.)), 1.)      # the harmful component goes (or shrinks)
        self.assertGreaterEqual(float(chosen['coefficients'].get(self.NAMES[1], 1.)), 1.)
        self.assertLess(chosen['mean_nll'], out['subject']['mean_nll'])
        self.assertLessEqual(chosen['guard'], out['subject']['guard'] * 1.05)
        report = json.loads((self.tmp / 'component_selection.json').read_text())
        self.assertIn('contrast', report['objective'])
        self.assertIsNotNone(report['subject']['guard'])


class HardGuard(Base):
    """F02: with contrast pairs no candidate that breaks the guard is ever taken, not even for require_all_donors."""
    def setUp(self):
        super().setUp()
        pl = self.pl
        self.saved_eval = pl.evaluate_trial
        pl.CONTRAST['tau'] = 0.05
        self.limit = 0.125                                                      # nu up to this keeps the guard

        def evaluate_trial(context, recipe, rows):
            nu = float(recipe.get('nu', 0) or 0)
            guard = 1.0 if nu <= self.limit else 1.2
            return {'recipe': recipe, 'mean_nll': -0.1 - nu, 'category_nll': {'math': -0.1 - nu}, 'guard': guard}
        pl.evaluate_trial = evaluate_trial
        self.subject = {'recipe': pl.baseline_recipe(), 'mean_nll': 0.0, 'category_nll': {'math': 0.0}, 'guard': 1.0}
        self.base = {'recipe': pl.canonical_recipe({'lambda_backbone': 0.05, 'lambda_head': 0.0, 'kappa': 0.0,
                                                    'group_scales': [1., 1., 1., 1.], 'high_fraction': .2, 'mu': 0.25}),
                     'mean_nll': -0.1, 'category_nll': {'math': -0.1}, 'guard': 1.0}
        self.context = {'settings': {'proxy_max_category_drop': 0.01, 'require_all_donors': True}}

    def tearDown(self):
        self.pl.evaluate_trial = self.saved_eval
        super().tearDown()

    def tried(self, values):
        return [{'nu': v, 'mean_nll': -0.1 - v, 'feasible': v <= self.limit} for v in values]

    def test_smaller_values_are_tried(self):
        records = [self.subject]
        good = self.pl.hard_line(self.context, self.base, records, [], self.tried([0.25, 0.5, 1.0]), 'nu', 'ν')
        self.assertEqual([t['nu'] for t in good], [0.125])
        self.assertTrue(all(t['feasible'] for t in good))

    def test_nothing_feasible_stops(self):
        self.limit = 0.01
        with self.assertRaises(self.pl.NoFeasibleCandidate):
            self.pl.hard_line(self.context, self.base, [self.subject], [], self.tried([0.25, 0.5, 1.0]), 'nu', 'ν')

    def test_old_objective_unchanged(self):
        self.pl.CONTRAST['tau'] = None
        self.assertFalse(self.pl.strict_guard())


class TmCacheChecks(Base):
    """F07 / F08 in the cross-architecture steps (their cached results on Drive stay valid)."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tm = load()['qmerge_tm']

    def test_fuse_cache_needs_the_same_inner_ot(self):
        tm = self.tm
        o = dict(tm.DEFAULTS)
        self.assertTrue(tm.fuse_cache_usable({'sha256': 'x'}, {'m': 'p1'}, o))          # an old record, default settings
        self.assertFalse(tm.fuse_cache_usable({'sha256': 'x'}, {'m': 'p1'}, {**o, 'eps_delta': 0.02}))
        self.assertTrue(tm.fuse_cache_usable({'pair_identities': {'m': 'p1'}}, {'m': 'p1'}, o))
        self.assertFalse(tm.fuse_cache_usable({'pair_identities': {'m': 'p0'}}, {'m': 'p1'}, o))
        self.assertFalse(tm.fuse_cache_usable(None, {'m': 'p1'}, o))

    def test_underflowed_plan_is_refused(self):
        import numpy as np
        tm = self.tm
        rng = np.random.default_rng(0)
        base = rng.standard_normal((128, 1))
        X = np.hstack([base + 1e-3 * rng.standard_normal((128, 1)) for _ in range(2)]).astype(np.float32)
        Y = np.hstack([base + 1e-3 * rng.standard_normal((128, 1)) for _ in range(2)] + [rng.standard_normal((128, 1))]).astype(np.float32)
        Xn, Yn = tm.zstd(X), tm.zstd(Y)
        with self.assertRaises(RuntimeError):
            tm.inner_ot(Xn, Yn, dict(tm.DEFAULTS))
        good = tm.inner_ot(tm.zstd(rng.standard_normal((128, 6)).astype(np.float32)),
                           tm.zstd(rng.standard_normal((128, 5)).astype(np.float32)), dict(tm.DEFAULTS))
        self.assertLess(good['marginal_residual'], 0.05)

    def test_cache_identities_do_not_hash_the_code(self):
        # why changing qmerge_tm / qmerge_tm2 keeps N and N2 on Drive valid: their caches are keyed by version constants
        from test_tm2 import embedded_sources
        src = embedded_sources()
        for name in ('qmerge_tm', 'qmerge_tm2'):
            self.assertNotIn('__file__', src[name])
        self.assertIn("TM_VERSION = 'tm-cpu-2026-10-26.1'", src['qmerge_tm'])
        self.assertIn("OT_VERSION = 'tm-ot-2026-10-26.1'", src['qmerge_tm'])
        self.assertIn("TM2_VERSION = 'tm2-cpu-2026-10-31.1'", src['qmerge_tm2'])
        self.assertIn("OT2_VERSION = 'tm2-ot-2026-10-31.1'", src['qmerge_tm2'])


class DevicesOnGpu(unittest.TestCase):
    """F01: no CUDA here, so the device flow is checked in the source: the gradient pass meets each gradient with the delta
    and the decomposition on sc.device, and the backward check brings its gradients to the CPU."""
    def test_device_flow(self):
        from test_tm2 import embedded_sources
        src = embedded_sources()['qmerge_components']
        self.assertEqual(src.count("parts=read_decomposition(store/f'decomp-{i:03d}.safetensors',device=sc.device)"), 2)
        self.assertEqual(src.count("deltas={n:(values[n].float()-subject.tensor(sc.mapping[n]).float()).to(sc.device) for n in names}"), 2)
        self.assertIn("p.grad.detach().float().to('cpu',copy=True)", src)
        self.assertNotIn("p.grad.detach().float().clone()", src)


class PairsManifest(Base):
    """F05: the traces must be S's own."""
    def test_subject_and_tokenizer_are_checked(self):
        pl = self.pl
        rows = pair_rows([('math', 3, 4)] * 4)
        meta = self.tmp / 'meta';meta.mkdir()
        (meta / 'tokenizer.json').write_text('{"v": 1}')
        path = self.write_pairs(rows, tokenizer={'tokenizer.json': self.core.sha_file(meta / 'tokenizer.json')})
        settings = {'contrast_pairs_file': str(path)}
        pl.contrast_setup(settings)
        here = {**settings, 'S_repo': 's/s', 'S_revision': 'a' * 40, 'S_subfolder': ''}
        pl.check_pairs_subject(here, meta)
        with self.assertRaises(ValueError):
            pl.check_pairs_subject({**here, 'S_revision': 'b' * 40})
        (meta / 'tokenizer.json').write_text('{"v": 2}')
        with self.assertRaises(ValueError):
            pl.check_pairs_subject(here, meta)
        path.write_text(path.read_text() + '\n')                               # the file no longer matches its manifest
        with self.assertRaises(ValueError):
            pl.contrast_setup({'contrast_pairs_file': str(path)})
        (self.tmp / 'pairs.manifest.json').unlink()
        with self.assertRaises(ValueError):
            pl.contrast_setup({'contrast_pairs_file': str(path)})


class NotebookE16(unittest.TestCase):
    def test_settings_and_messages(self):
        nb = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
        sources = [''.join(c['source']) for c in nb['cells']]
        cell = next(s for s in sources if 'SETTINGS = {' in s)
        for text in ('CONTRAST_PAIRS_FILE = ""', '"objective": "contrast"', '"contrast_pairs_file": CONTRAST_PAIRS_FILE',
                     '"plans": ["lenient", "step:0.5", "step:1"]', '"logits_window": 2048', '"veto": True', 'AUTO_EVAL_DATA = False'):
            self.assertIn(text, cell)
        run = next(s for s in sources if 'RESULT = qmerge_pipeline.run_pipeline' in s)
        for status in ('waiting_for_contrast_pairs', 'waiting_for_veto', 'veto_rejected'):
            self.assertIn(f'"{status}"', run)
        meta = nb['metadata']['qwen38_efficientthink']
        self.assertIn('NLL(right) - NLL(wrong)', meta['objective'])
        self.assertFalse(meta['real_27b_tested'])


if __name__ == '__main__':
    unittest.main()
