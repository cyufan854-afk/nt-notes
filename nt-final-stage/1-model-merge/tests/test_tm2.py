"""Unit tests for the e15 additions (qmerge_tm2 and the nu2 term in qmerge_pipeline), on random small tensors.

The module sources are taken from the notebook itself, so the tests check exactly the embedded code.
Needs numpy, torch and safetensors (the notebook's own dependencies); nothing is downloaded and no model is loaded.

    python3 -m unittest discover -s tests -v          (in 1-model-merge/)
"""
import json
import math
from pathlib import Path
import re
import sys
import tempfile
import types
import unittest

HERE = Path(__file__).resolve().parent
NOTEBOOK = next(HERE.parent.glob('Qwen38_pi_AuxMix_e15*.ipynb'))
MODULES = ('qmerge_core', 'qmerge_runtime', 'qmerge_components', 'qmerge_gguf', 'qmerge_della', 'qmerge_tm', 'qmerge_tm2',
           'qmerge_pipeline')

try:
    import numpy as np
    import torch
    import safetensors  # noqa: F401
    HAVE_TORCH = True
except ImportError:
    HAVE_TORCH = False


def embedded_sources(path=NOTEBOOK):
    nb = json.loads(Path(path).read_text(encoding='utf-8'))
    out = {}
    for cell in nb['cells']:
        src = ''.join(cell['source'])
        m = re.search(r"load_embedded_module\('(\w+)', (\w+)\)", src)
        if not m:
            continue
        var = m.group(2)
        start = src.index(var + " = r'''") + len(var + " = r'''")
        out[m.group(1)] = src[start:src.index("'''", start)]
    return out


_LOADED = {}


def load():
    if not _LOADED:
        directory = Path(tempfile.mkdtemp(prefix='nbmods-'))
        for name, source in embedded_sources().items():
            (directory / (name + '.py')).write_text(source, encoding='utf-8')
        sys.path.insert(0, str(directory))
        import importlib
        for name in MODULES:
            _LOADED[name] = importlib.import_module(name)
    return _LOADED


@unittest.skipUnless(HAVE_TORCH, 'needs numpy, torch and safetensors')
class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m = load()
        cls.tm, cls.tm2, cls.pl, cls.core = m['qmerge_tm'], m['qmerge_tm2'], m['qmerge_pipeline'], m['qmerge_core']


class Structure(Base):
    def card(self):
        tm2 = self.tm2
        full = [i for i in range(32) if i % 4 == 3]
        return {'order': tm2.expected_order(tm2.EXPECT), 'layers': 32, 'hidden': 4096, 'ffn': 12288, 'heads': 16,
                'kv_heads': 4, 'head_dim': 256, 'vocab': 248320, 'full_layers': full}

    def test_model_card_order_has_56_executions(self):
        order = self.tm2.expected_order(self.tm2.EXPECT)
        self.assertEqual(len(order), 56)
        self.assertEqual(order[:5], [0, 1, 2, 3, 4])
        self.assertEqual(order[27:30], [27, 4, 5])
        self.assertEqual(order[-4:], [28, 29, 30, 31])
        execs = self.tm2.schedule(order)
        self.assertEqual([x for x in execs if x[1] == 4], [(4, 4, 1), (28, 4, 2)])
        self.assertEqual(self.tm2.check_structure(self.card(), self.tm2.EXPECT), [])

    def test_any_difference_from_the_card_stops(self):
        tm2 = self.tm2
        for change, word in (({'order': tm2.expected_order({**tm2.EXPECT, 'loop_times': 3})}, '执行顺序'),
                             ({'hidden': 3584}, 'hidden'), ({'vocab': None}, 'vocab'),
                             ({'full_layers': [0, 1, 2, 3]}, '全注意力'), ({'full_layers': None}, '全注意力')):
            with self.subTest(change=change):
                problems = tm2.check_structure({**self.card(), **change}, tm2.EXPECT)
                self.assertTrue(any(word in p for p in problems), problems)
        # a 3:1 pattern with another phase is still the card's pattern
        shifted = {**self.card(), 'full_layers': [i for i in range(32) if i % 4 == 0]}
        self.assertEqual(tm2.check_structure(shifted, tm2.EXPECT), [])

    def test_candidates_per_module(self):
        tm2 = self.tm2
        execs = tm2.schedule(tm2.expected_order(tm2.EXPECT))
        full = [i for i in range(32) if i % 4 == 3]
        c = tm2.donor_candidates(execs, full, ['self_attn.v_proj', 'mlp.down_proj'], 2)
        self.assertEqual(len(c['self_attn.v_proj']), 1 + 6 * 2 + 1)        # full layers 3; 7..27 twice; 31
        phys = {e: p for e, p, _ in execs}
        self.assertEqual(sorted({phys[e] for e in c['self_attn.v_proj']}), full)
        self.assertEqual(c['mlp.down_proj'], list(range(0, 56, 2)))
        shared = [e for e in c['self_attn.v_proj'] if phys[e] == 7]
        self.assertEqual(shared, [7, 31])                                  # one weight, two candidate donor layers

    def test_full_layers_from_layer_types(self):
        types_ = ['linear_attention'] * 3 + ['full_attention']
        self.assertEqual(self.tm2.full_attention_layers(types_ * 8, 32), [i for i in range(32) if i % 4 == 3])
        self.assertIsNone(self.tm2.full_attention_layers(None, 32))
        with self.assertRaises(ValueError):
            self.tm2.full_attention_layers(types_, 32)

    def test_rope_compatibility_for_k_proj(self):
        base = {'hidden_size': 5120, 'num_attention_heads': 24, 'head_dim': 256,
                'rope_parameters': {'rope_theta': 1e7, 'partial_rotary_factor': 0.25, 'mrope_section': [11, 11, 10]}}
        donor = {'text_config': {**base, 'hidden_size': 4096, 'num_attention_heads': 16}}
        ok, why = self.tm2.rope_compatible(donor, {'text_config': base})
        self.assertTrue(ok, why)
        donor['text_config']['rope_parameters'] = {**base['rope_parameters'], 'rope_theta': 5e6}
        ok, why = self.tm2.rope_compatible(donor, base)
        self.assertTrue(ok)
        self.assertIn('rope_theta', why)
        for change in ({'head_dim': 128}, {'rope_parameters': {**base['rope_parameters'], 'partial_rotary_factor': 0.5}},
                       {'rope_parameters': {**base['rope_parameters'], 'mrope_section': [16, 8, 8]}}):
            ok, why = self.tm2.rope_compatible({**base, **change}, base)
            self.assertFalse(ok, change)


class Settings(Base):
    def test_shared_corpus_and_inherited_options(self):
        settings = {'tm_extra': {'act_repo': 'u/acts', 'pair_keep': 3}, 'tm_extra2': {'code_sha256': 'a' * 64}}
        o = self.tm2.options(settings)
        self.assertEqual(o['act_repo'], 'u/acts')
        self.assertEqual(o['pair_keep'], 3)                 # N's OT setting unless N2 overrides it
        self.assertEqual(o['alpha'], self.tm.DEFAULTS['alpha'])
        self.assertTrue(o['require_all_donors'])
        with self.assertRaisesRegex(ValueError, '共用'):
            self.tm2.options({'tm_extra2': {'act_repo': 'other/acts'}})
        for bad in ({'nu_grid': [0, 0.5]}, {'k_proj': 'yes'}, {'modules': ['self_attn.q_proj']}, {'code_sha256': 'short'},
                    {'unknown': 1}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.tm2.options({'tm_extra2': bad})

    def test_pick_nu(self):
        tried = [{'nu': 0.25, 'mean_nll': 1.10, 'feasible': True}, {'nu': 0.5, 'mean_nll': 1.05, 'feasible': False},
                 {'nu': 1.0, 'mean_nll': 1.08, 'feasible': True}]
        self.assertEqual(self.tm2.pick_nu(tried, 1.00, True), 1.0)        # best feasible, even if worse than without
        self.assertEqual(self.tm2.pick_nu(tried, 1.00, False), 0.)        # optional: must beat the winner
        self.assertEqual(self.tm2.pick_nu(tried, 1.09, False), 1.0)
        infeasible = [dict(t, feasible=False) for t in tried]
        self.assertEqual(self.tm2.pick_nu(infeasible, 1.0, True), 0.5)    # required: the lowest NLL overall


class CodeReview(Base):
    class Engine:
        def __init__(self, files):
            self.content, self.revisions = files, {}

        def files(self, repo):
            return list(self.content) + ['model-00001.safetensors', 'sub/inner.py']

        def _small_bytes(self, repo, name):
            return self.content[name]

        def pin(self, repo):
            return 'c' * 40

    def run_for(self, files, digest=''):
        o = self.tm2.options({'tm_extra2': {'code_sha256': digest}})
        return types.SimpleNamespace(eng=self.Engine(files), o=o)

    def test_code_is_reviewed_before_it_runs(self):
        files = {'modeling_loop.py': b'import torch\nimport subprocess\n', 'configuration_loop.py': b'X = 1\n'}
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError) as cm:
                self.tm2._code(self.run_for(files), d)
            message = str(cm.exception)
            self.assertIn('code_sha256', message)
            self.assertIn('subprocess', message)
            digest = re.search(r'"([0-9a-f]{64})"', message).group(1)
            got, rows = self.tm2._code(self.run_for(files, digest), d)
            self.assertEqual(got, digest)
            self.assertEqual([r[0] for r in rows], ['configuration_loop.py', 'modeling_loop.py'])
            files['modeling_loop.py'] += b'# changed upstream\n'
            with self.assertRaises(RuntimeError):
                self.tm2._code(self.run_for(files, digest), d)

    def test_tokenizer_digest(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / 'a.json', Path(d) / 'b.json'
            tok = {'model': {'vocab': {'a': 0, 'b': 1}, 'merges': ['a b']}, 'added_tokens': [], 'normalizer': None,
                   'pre_tokenizer': None, 'post_processor': {'x': 1}}
            a.write_text(json.dumps(tok))
            b.write_text(json.dumps({**tok, 'post_processor': {'x': 2}}))
            self.assertEqual(self.tm2.tokenizer_digest(a), self.tm2.tokenizer_digest(b))
            b.write_text(json.dumps({**tok, 'model': {'vocab': {'a': 0, 'c': 1}, 'merges': []}}))
            self.assertNotEqual(self.tm2.tokenizer_digest(a), self.tm2.tokenizer_digest(b))


# ---------------------------------------------------------------- the worker's float32 path and per-execution hooks
def tiny_loop_model(torch):
    """A recurrent-depth toy: 6 layers, layers [2, 4) run twice; inside the loop two residual streams, each layer reading
    an FP32-weighted mix of them and writing back through FP32 maps (mHC-like), so each execution runs the layer once."""
    nn = torch.nn

    class Layer(nn.Module):
        def __init__(self, full):
            super().__init__()
            self.mlp = nn.Module()
            self.mlp.gate_proj, self.mlp.up_proj, self.mlp.down_proj = nn.Linear(8, 12, bias=False), nn.Linear(8, 12, bias=False), nn.Linear(12, 8, bias=False)
            self.norm = nn.LayerNorm(8)
            if full:
                self.self_attn = nn.Module()
                self.self_attn.v_proj, self.self_attn.o_proj = nn.Linear(8, 4, bias=False), nn.Linear(4, 8, bias=False)

        def forward(self, h):
            x = self.norm(h)
            if hasattr(self, 'self_attn'):
                h = h + self.self_attn.o_proj(torch.tanh(self.self_attn.v_proj(x)))
            return h + self.mlp.down_proj(torch.nn.functional.silu(self.mlp.gate_proj(x)) * self.mlp.up_proj(x))

    class Model(nn.Module):
        def __init__(self):
            super().__init__()
            self.embed = nn.Embedding(20, 8)
            self.layers = nn.ModuleList([Layer(i % 2 == 1) for i in range(6)])
            self.mix = nn.Parameter(torch.tensor([[0.9, 0.1], [0.2, 0.8]], dtype=torch.float32))
            self.pre = nn.Parameter(torch.tensor([0.6, 0.4], dtype=torch.float32))
            self.post = nn.Parameter(torch.tensor([1.0, 0.5], dtype=torch.float32))
            self.head = nn.Linear(8, 20, bias=False)

        def forward(self, input_ids, **kw):
            h = self.embed(input_ids)
            for i in (0, 1):
                h = self.layers[i](h)
            streams = [h, h]
            for _ in range(2):
                for i in (2, 3):
                    x = self.pre[0] * streams[0] + self.pre[1] * streams[1]
                    y = self.layers[i](x) - x
                    streams = [self.mix[r, 0] * streams[0] + self.mix[r, 1] * streams[1] + self.post[r] * y for r in range(2)]
            h = (streams[0] + streams[1]) / 2
            for i in (4, 5):
                h = self.layers[i](h)
            return types.SimpleNamespace(logits=self.head(h))
    return Model


@unittest.skipUnless(HAVE_TORCH, 'needs numpy, torch and safetensors')
class Worker(Base):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.w = {}
        exec(compile(cls.tm2.WORKER_SOURCE, 'tm2_donor_worker.py', 'exec'), cls.w)

    def model(self):
        torch.manual_seed(0)
        m = tiny_loop_model(torch)()
        for name, p in m.named_parameters():
            if name not in ('mix', 'pre', 'post'):
                p.data = p.data.to(torch.bfloat16)
        m.eval()
        for p in m.parameters():
            p.requires_grad_(False)
        return m

    def float32_reference(self, m, ids):
        import copy
        ref = copy.deepcopy(m).float()
        return ref, ref(ids).logits

    def prepare(self, m):
        for name, p in m.named_parameters():
            if not name.startswith('layers.') and p.is_floating_point():
                p.data = p.data.to(torch.float32)

    def test_float32_compute_with_bf16_storage(self):
        m = self.model()
        ids = torch.randint(0, 20, (3, 5))
        ref, want = self.float32_reference(m, ids)
        self.prepare(m)
        fp = self.w['Fp32Layers'](m.layers)
        with torch.no_grad():
            got = m(ids).logits
        self.assertTrue(torch.allclose(got, want, atol=1e-5, rtol=1e-5), (got - want).abs().max())
        self.assertEqual(fp.order, [0, 1, 2, 3, 2, 3, 4, 5])                # [2, 4) twice: 8 executions
        self.assertTrue(all(p.dtype == torch.bfloat16 for p in m.layers.parameters()))
        self.assertTrue(all(torch.equal(a.to(torch.bfloat16), b) for a, b in zip(ref.layers.parameters(), m.layers.parameters())))

    def test_recorder_keeps_each_execution_of_a_shared_layer_apart(self):
        m = self.model()
        self.prepare(m)
        fp = self.w['Fp32Layers'](m.layers)
        order = [0, 1, 2, 3, 2, 3, 4, 5]
        wanted = {'mlp.down_proj': [(e, order[e]) for e in (2, 4)], 'self_attn.v_proj': [(e, order[e]) for e in (3, 5)]}
        rec = self.w['Recorder'](m.layers, fp, wanted, {}, 4)
        # reference: plain hooks that log every call in order
        calls = []
        h = m.layers[2].mlp.down_proj.register_forward_hook(lambda mod, a, o: calls.append((a[0].float().mean(1), o.float().mean(1))))
        ids = torch.randint(0, 20, (2, 6))
        fp.reset()
        rec.rows = torch.tensor([1, 3])
        with torch.no_grad():
            m(ids)
        h.remove()
        self.assertEqual(len(calls), 2)          # physical layer 2 ran once per pass
        # executions 2 and 4 are the two calls of physical layer 2, in order
        for k, e in enumerate((2, 4)):
            self.assertTrue(torch.allclose(rec.acc[(e, 'mlp.down_proj')]['in_mean'][[1, 3]], calls[k][0]))
            self.assertTrue(torch.allclose(rec.acc[(e, 'mlp.down_proj')]['out_mean'][[1, 3]], calls[k][1]))
        self.assertFalse(torch.allclose(rec.acc[(2, 'mlp.down_proj')]['in_mean'][[1, 3]], rec.acc[(4, 'mlp.down_proj')]['in_mean'][[1, 3]]))
        self.assertTrue(bool(rec.acc[(5, 'self_attn.v_proj')]['out_mean'][[1, 3]].abs().sum() > 0))
        self.assertTrue(bool((rec.acc[(2, 'mlp.down_proj')]['in_mean'][[0, 2]] == 0).all()))   # rows of other batches untouched
        self.assertNotIn((6, 'mlp.down_proj'), rec.acc)

    def test_stop_after_last_needed_execution(self):
        m = self.model()
        self.prepare(m)
        fp = self.w['Fp32Layers'](m.layers, stop_after=4)
        with torch.no_grad(), self.assertRaises(self.w['_Stop']):
            m(torch.randint(0, 20, (1, 4)))
        self.assertEqual(fp.order, [0, 1, 2, 3, 2])
        self.assertTrue(all(p.dtype == torch.bfloat16 for p in m.layers.parameters()))

    def test_fp32_checkpoint_tensors_are_restored(self):
        from safetensors.torch import save_file
        m = self.model()
        true_mix = torch.tensor([[0.123456789, 0.876543211], [0.3, 0.7]], dtype=torch.float32)
        m.mix.data = true_mix.to(torch.bfloat16)                   # what a loader casting everything to BF16 would do
        with tempfile.TemporaryDirectory() as d:
            save_file({'model.mix': true_mix, 'model.pre': m.pre.data.clone(), 'model.head.weight': m.head.weight.data.clone()},
                      str(Path(d) / 'model.safetensors'))
            self.assertEqual(self.w['restore_fp32'](m, d), 1)
        self.assertEqual(m.mix.dtype, torch.float32)
        self.assertTrue(torch.equal(m.mix.data, true_mix))
        self.assertEqual(m.head.weight.dtype, torch.bfloat16)

    def test_find_layers_and_split_lists(self):
        m = self.model()
        name, layers = self.w['find_layers'](m, 6)
        self.assertEqual((name, len(layers)), ('layers', 6))
        m.before, m.loop = torch.nn.ModuleList(list(m.layers)[:2]), torch.nn.ModuleList(list(m.layers)[2:])
        del m.layers
        name, layers = self.w['find_layers'](m, 6, ['before', 'loop'])
        self.assertEqual((name, len(layers)), ('before+loop', 6))

    def test_equal_length_batches_without_padding(self):
        def tok(texts, truncation, max_length, padding):
            return {'input_ids': [list(range(min(len(t.split()), max_length))) for t in texts]}
        texts = ['a b c', 'a b', 'a b c', 'a b c d e f g', 'x y']
        batches, tokens = self.w['ids_batches'](tok, texts, 1, 5, 4, 2)
        self.assertEqual(tokens, 2 + 3 + 4 + 2)
        shapes = sorted(tuple(ids.shape) for _, ids in batches)
        self.assertEqual(shapes, [(1, 3), (1, 4), (2, 2)])
        self.assertEqual(sorted(int(r) for rows, _ in batches for r in rows), [0, 1, 2, 3])


# ---------------------------------------------------------------- verdict -> pairs -> fusion over executions
class FakeActs:
    def __init__(self, data):
        self.data = data

    def raw(self, layer, module, suffix):
        return self.data[(layer, module, suffix)]

    def z(self, layer, module, suffix):
        import qmerge_tm
        return qmerge_tm.zstd(self.raw(layer, module, suffix))

    def clear(self):
        pass


@unittest.skipUnless(HAVE_TORCH, 'needs numpy, torch and safetensors')
class TransportFlow(Base):
    def setUp(self):
        rng = np.random.default_rng(7)
        self.T, self.n_in, self.n_out, self.m_in, self.m_out = 300, 10, 12, 6, 8
        self.mod = 'mlp.down_proj'
        latent_in, latent_out = rng.standard_normal((self.T, 6)), rng.standard_normal((self.T, 8))
        mix = lambda base, width, seed: base @ np.random.default_rng(seed).standard_normal((base.shape[1], width)) + 0.05 * rng.standard_normal((self.T, width))
        tdata, sdata = {}, {}
        for li in (0, 4):
            tdata[(li, self.mod, 'in_mean')] = mix(latent_in, self.n_in, 1).astype(np.float32)
            tdata[(li, self.mod, 'out_mean')] = mix(latent_out, self.n_out, 2).astype(np.float32)
            tdata[(li, self.mod, 'out_abs')] = np.abs(tdata[(li, self.mod, 'out_mean')]) + li
        # executions 0 and 2 run the same physical layer (a loop): different activations, one weight
        for e in (0, 2):
            sdata[(e, self.mod, 'in_mean')] = mix(latent_in, self.m_in, 3 + e).astype(np.float32)
            sdata[(e, self.mod, 'out_mean')] = mix(latent_out, self.m_out, 4 + e).astype(np.float32)
        self.tgt, self.src = FakeActs(tdata), FakeActs(sdata)
        o = self.tm2.options({'tm_extra2': {'topk': 4, 'pair_keep': 1, 'iters_inner': 300, 'chunk_rows': 64}})
        self.tmp = tempfile.TemporaryDirectory()
        self.run_ = types.SimpleNamespace(o=o, root=Path(self.tmp.name), say=lambda text: None)
        self.inp = {'modules': [self.mod], 'full': [], 'rec': [0, 4], 'target_layers': 8,
                    'targets': {(self.mod, 0): 'model.layers.0.mlp.down_proj.weight', (self.mod, 4): 'model.layers.4.mlp.down_proj.weight'}}
        self.plan = {'cands': {self.mod: [0, 2]}, 'phys': {0: 5, 2: 5}, 'n_exec': 4}
        self.WB = {5: np.random.default_rng(11).standard_normal((self.m_out, self.m_in)).astype(np.float32)}
        self.WA = {n: np.random.default_rng(12 + k).standard_normal((self.n_out, self.n_in)).astype(np.float32)
                   for k, n in enumerate(self.inp['targets'].values())}

    def tearDown(self):
        self.tmp.cleanup()

    def test_verdict_pairs_and_fusion_use_one_weight_for_both_executions(self):
        tm, tm2 = self.tm, self.tm2
        v = tm2.verdict(self.run_, self.inp, self.plan, {'x': 1}, self.tgt, self.src)
        self.assertIn(self.mod, v['modules'])
        self.assertIn(v['modules'][self.mod]['verdict'], ('GO', 'MARGINAL', 'NO-GO', 'SKIP'))
        v = {**v, 'go': [self.mod]}
        state = tm2.pair_ot(self.run_, self.inp, self.plan, {'x': 1}, self.tgt, self.src, self.mod, store=False)
        self.assertEqual(set(state['kept']), {0, 4})
        asked = []

        def weight_of(mod, phys):
            asked.append(phys)
            return self.WB[phys]
        out, diag, plans = tm2.fuse(self.run_, self.inp, self.plan, v, {self.mod: state}, self.tgt, self.src,
                                    weight_of, lambda name: self.WA[name])
        self.assertEqual(set(asked), {5})                                   # only the physical layer's weight is read
        for name in self.inp['targets'].values():
            rows, delta = out[name + '|rows'], out[name + '|delta']
            self.assertEqual(delta.shape, (4, self.n_in))
            # recompute by hand with qmerge_tm's primitives: N rows = alpha * (inject(sum_w transport) - B rows)
            li = int(name.split('.')[2])
            picks = diag[name]['donor_executions']
            acc = np.zeros((4, self.n_in), dtype=np.float32)
            for w, e, phys in picks:
                self.assertEqual(phys, 5)
                r = state['done'][(li, e)]
                po = (self.tgt.z(li, self.mod, 'out_mean'), self.src.z(e, self.mod, 'out_mean'), r['out']['u'], r['out']['v'], r['out']['eps'])
                pi = (self.tgt.z(li, self.mod, 'in_mean'), self.src.z(e, self.mod, 'in_mean'), r['in']['u'], r['in']['v'], r['in']['eps'])
                acc += np.float32(w) * tm.transport_rows(rows, self.WB[5], po, pi, self.n_in, 64)
            new, _ = tm.inject(acc, self.WA[name][rows], self.run_.o)
            self.assertTrue(np.allclose(delta, self.run_.o['alpha'] * (new - self.WA[name][rows]), atol=1e-6))
            self.assertTrue(np.all(np.isin(rows, np.argsort(-self.tgt.raw(li, self.mod, 'out_abs').mean(0))[:4])))
        self.assertEqual(plans[self.mod]['phys'], [5] * len(plans[self.mod]['ST']))


# ---------------------------------------------------------------- the pipeline's nu2 term
class FakeDelta:
    def __init__(self, entries, fingerprint):
        self.entries, self.fingerprint = entries, fingerprint

    def has(self, name):
        return name in self.entries

    def rows(self, name, i, j):
        return self.entries[name][i:j].float()


@unittest.skipUnless(HAVE_TORCH, 'needs numpy, torch and safetensors')
class PipelineNu2(Base):
    NAME = 'model.language_model.layers.3.mlp.down_proj.weight'

    def context(self):
        torch.manual_seed(1)
        S = (torch.randn(6, 4) * 4).to(torch.bfloat16).float()
        N = torch.zeros(6, 4)
        N[1] = torch.randn(4) * 0.05
        N2 = torch.zeros(6, 4)
        N2[[1, 4]] = torch.randn(2, 4) * 0.05

        class Subject:
            shapes = {self.NAME: (6, 4)}

            def rows(self, name, i, j):
                return S[i:j].clone()

        class Engine:
            def is_float(self, repo, name):
                return True

            def tensor(self, repo, name):
                return S.clone()
        return {'S': Subject(), 'S_repo': 's', 'engine': Engine(), 'N': FakeDelta({self.NAME: N}, 'n1'),
                'N2': FakeDelta({self.NAME: N2}, 'n2'), 'D': FakeDelta({}, 'd'), 'tied': False, 'num_layers': 8,
                'settings': {'rows_mib': 64, 'max_relative_change': None}, 'searched': []}, S, N, N2

    def recipe(self, **kw):
        return self.pl.canonical_recipe({'lambda_backbone': 0., 'lambda_head': 0., 'kappa': 0., 'group_scales': [1., 1., 1., 1.],
                                         'high_fraction': .2, **kw})

    def test_recipe_fields(self):
        pl = self.pl
        r = self.recipe(nu=0.5, nu2=0.25)
        self.assertEqual((r['nu'], r['nu2']), (0.5, 0.25))
        self.assertNotIn('nu2', self.recipe(nu=0.5, nu2=0.))
        self.assertTrue(pl.is_baseline(self.recipe()))
        self.assertFalse(pl.is_baseline(self.recipe(nu2=0.25)))
        with self.assertRaisesRegex(ValueError, 'nu2'):
            pl.validate_recipe({**self.recipe(), 'nu2': 3.0})
        self.assertEqual(self.recipe(nu=0.5), pl.canonical_recipe({**self.recipe(), 'nu': 0.5}))   # e14 recipes unchanged

    def test_candidate_adds_nu2_times_n2(self):
        ctx, S, N, N2 = self.context()
        got, info = self.pl.candidate_tensor(ctx, self.NAME, self.recipe(nu=0.5, nu2=0.25))
        want = (S + 0.5 * N + 0.25 * N2).to(torch.bfloat16)
        self.assertTrue(torch.equal(got, want))
        only_n = self.pl.candidate_tensor(ctx, self.NAME, self.recipe(nu=0.5))[0]
        self.assertTrue(torch.equal(only_n, (S + 0.5 * N).to(torch.bfloat16)))
        ctx['N2'] = None
        with self.assertRaisesRegex(ValueError, 'N₂'):
            self.pl.candidate_tensor(ctx, self.NAME, self.recipe(nu2=0.25))

    def test_cache_identities_name_n2(self):
        ctx, *_ = self.context()
        ident = self.pl.layer_identity(ctx, self.recipe(nu=0.5, nu2=0.25), 3)
        self.assertEqual((ident['nu2'], ident['tm2_delta'], ident['tm_delta']), (0.25, 'n2', 'n1'))
        self.assertNotIn('nu2', self.pl.layer_identity(ctx, self.recipe(nu=0.5), 3))

    def test_nu2_line_runs_on_the_winner_with_n(self):
        pl = self.pl
        ctx, *_ = self.context()
        ctx['tm2'] = {'repo': 'sensenova/x', 'modules': ['mlp.down_proj']}
        ctx['settings'] = {**ctx['settings'], 'tm_extra2': {'nu_grid': [0.25, 0.5, 1.0]}, 'require_all_donors': True,
                           'proxy_max_category_drop': 0.1}
        base_recipe = self.recipe(nu=0.5, lambda_backbone=0.05)
        best = {'recipe': base_recipe, 'mean_nll': 1.0}
        scores = {0.25: 1.02, 0.5: 0.99, 1.0: 1.01}
        evaluated = []

        def fake_trial(context, recipe, rows):
            evaluated.append(recipe)
            return {'recipe': recipe, 'mean_nll': scores[recipe['nu2']]}
        old = (pl.evaluate_trial, pl.proxy_feasible)
        pl.evaluate_trial, pl.proxy_feasible = fake_trial, lambda trial, base, drop: True
        try:
            chosen, report = pl.evaluate_nu2_line(ctx, best, [{'recipe': self.recipe(), 'mean_nll': 1.1}], [])
        finally:
            pl.evaluate_trial, pl.proxy_feasible = old
        self.assertEqual(report['selected_nu2'], 0.5)
        self.assertEqual(chosen['recipe']['nu2'], 0.5)
        self.assertEqual(chosen['recipe']['nu'], 0.5)                       # nu from the first line is kept
        self.assertEqual(len(evaluated), 3)
        ctx['N2'] = None
        self.assertEqual(pl.evaluate_nu2_line(ctx, best, [], []), (best, None))


@unittest.skipUnless(HAVE_TORCH, 'needs numpy, torch and safetensors')
class SettingsCell(Base):
    def test_settings_written_in_section_1_are_valid(self):
        import ast
        nb = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
        cell = next(''.join(c['source']) for c in nb['cells'] if '"tm_extra2": {' in ''.join(c['source']))
        found = {}
        for node in ast.walk(ast.parse(cell)):
            if isinstance(node, ast.Dict):
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, ast.Constant) and k.value in ('tm_extra', 'tm_extra2', 'require_all_donors'):
                        found[k.value] = ast.literal_eval(v)
        o2 = self.tm2.options(found)
        self.assertEqual(o2['repo'], 'sensenova/SenseNova-Loop-9B-Preview')
        self.assertEqual(o2['act_repo'], self.tm.options(found)['act_repo'])
        self.assertEqual(o2['code_sha256'], '')            # first run stops for the code review
        self.assertTrue(all(x > 0 for x in o2['nu_grid']))
        self.assertTrue(o2['require_all_donors'])


class NotebookLayout(unittest.TestCase):
    def test_cells_and_versions(self):
        nb = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
        sources = [''.join(c['source']) for c in nb['cells']]
        order = [re.search(r"load_embedded_module\('(\w+)'", s).group(1) for s in sources if re.search(r"load_embedded_module\('(\w+)'", s)]
        self.assertLess(order.index('qmerge_tm'), order.index('qmerge_tm2'))
        self.assertLess(order.index('qmerge_tm2'), order.index('qmerge_pipeline'))
        self.assertTrue(any('BOOTSTRAP_VERSION = "qwen38-auxmix-2026-10-31.e15"' in s for s in sources))
        meta = nb['metadata']['qwen38_efficientthink']
        self.assertTrue(meta['revision'].endswith('e15'))
        import hashlib
        src = embedded_sources()
        for name, digest in meta['module_sha256'].items():
            self.assertEqual(hashlib.sha256(src[name].encode()).hexdigest(), digest, name)

    def test_unchanged_modules_keep_their_e14_fingerprints(self):
        e14 = {'qmerge_core': '45cfcb5b175df4b1bf593ba889e3f98a4e1838bd4e6297b59357cb23b58b886a',
               'qmerge_runtime': '656874a80b5573f6c0d74bb92bcfbf8b3b5633c4538d0dfe1a7a72f4c36078e8',
               'qmerge_components': '79ce5523116424293bd37061210406fbb5bd589dc3672e2103a5636d58fdea5b',
               'qmerge_tm': 'b22359670a0523b567944af6cd1833eb00ed8aff74e919547b0c7f0182bfa850'}
        meta = json.loads(NOTEBOOK.read_text(encoding='utf-8'))['metadata']['qwen38_efficientthink']['module_sha256']
        for name, digest in e14.items():
            self.assertEqual(meta[name], digest, name)


if __name__ == '__main__':
    unittest.main()
