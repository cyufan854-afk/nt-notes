"""The "lora" auxiliary source of qmerge_pipeline (2026-11-02): a LoRA adapter as one fixed term of D.

The adapter is read in its PEFT layout, each adapted module is matched to one backbone matrix of S, and the term is
scale * (B @ A) in float32. Run with numpy, torch and safetensors installed (the notebook's own dependencies).
"""
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tm2 import HAVE_TORCH, NOTEBOOK, load  # noqa: E402

if HAVE_TORCH:
    import torch
    from safetensors.torch import save_file

S_SHAPES = {
    'model.language_model.embed_tokens.weight': (32, 8),
    'lm_head.weight': (32, 8),
    'model.language_model.layers.0.mlp.down_proj.weight': (8, 12),
    'model.language_model.layers.0.mlp.up_proj.weight': (12, 8),
    'model.language_model.layers.1.linear_attn.in_proj_qkv.weight': (24, 8),
    'model.language_model.layers.1.input_layernorm.weight': (8,),
    'mtp.layers.0.mlp.down_proj.weight': (8, 12),
    'model.visual.blocks.0.mlp.down_proj.weight': (8, 12),
}
DOWN = 'model.language_model.layers.0.mlp.down_proj.weight'
QKV = 'model.language_model.layers.1.linear_attn.in_proj_qkv.weight'


def write_adapter(directory, factors, rank=4, alpha=8, prefix='base_model.model.model.layers.', **config):
    """factors: {module suffix after 'layers.': (A, B)}. Writes the three files LoraSource reads."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    tensors = {}
    for module, (a, b) in factors.items():
        tensors[f'{prefix}{module}.lora_A.weight'] = a.contiguous()
        tensors[f'{prefix}{module}.lora_B.weight'] = b.contiguous()
    save_file(tensors, str(directory / 'adapter_model.safetensors'))
    cfg = {'peft_type': 'LORA', 'r': rank, 'lora_alpha': alpha, 'bias': 'none', 'use_rslora': False, 'use_dora': False,
           'fan_in_fan_out': False, 'rank_pattern': {}, 'alpha_pattern': {}, 'modules_to_save': None, **config}
    (directory / 'adapter_config.json').write_text(json.dumps(cfg), encoding='utf-8')
    sha = hashlib.sha256((directory / 'adapter_model.safetensors').read_bytes()).hexdigest()
    manifest = {'kind': 'trace_lora', 'base_repo': 'Qwen/Qwen3.6-27B', 'base_revision': 'a' * 40, 'adapter_sha256': sha}
    (directory / 'trace_lora_manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    return directory


@unittest.skipUnless(HAVE_TORCH, 'needs numpy, torch and safetensors')
class LoraSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m = load()
        cls.pl, cls.core = m['qmerge_pipeline'], m['qmerge_core']

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / 'adapter'
        torch.manual_seed(0)
        self.a_down, self.b_down = torch.randn(4, 12), torch.randn(8, 4) * 0.01
        self.a_qkv, self.b_qkv = torch.randn(4, 8), torch.randn(24, 4) * 0.01

    def tearDown(self):
        self.tmp.cleanup()

    def adapter(self, **kw):
        return write_adapter(self.dir, {'0.mlp.down_proj': (self.a_down, self.b_down),
                                        '1.linear_attn.in_proj_qkv': (self.a_qkv, self.b_qkv)}, **kw)

    # ------------------------------------------------------------ pieces
    def test_scale(self):
        self.assertEqual(self.pl.lora_check_config({'r': 16, 'lora_alpha': 32}), 2.0)
        self.assertAlmostEqual(self.pl.lora_check_config({'r': 16, 'lora_alpha': 32, 'use_rslora': True}), 8.0)
        for bad in ({'use_dora': True}, {'rank_pattern': {'x': 2}}, {'modules_to_save': ['lm_head']},
                    {'fan_in_fan_out': True}, {'bias': 'all'}, {'peft_type': 'IA3'}):
            with self.assertRaisesRegex(ValueError, '不能作为辅料'):
                self.pl.lora_check_config({'r': 8, 'lora_alpha': 8, **bad})

    def test_pairs(self):
        pairs = self.pl.lora_pairs(['base_model.model.model.layers.0.mlp.down_proj.lora_A.weight',
                                    'base_model.model.model.layers.0.mlp.down_proj.lora_B.weight',
                                    'model.layers.1.self_attn.q_proj.lora_A.default.weight',
                                    'model.layers.1.self_attn.q_proj.lora_B.default.weight'])
        self.assertEqual(set(pairs), {'model.layers.0.mlp.down_proj', 'model.layers.1.self_attn.q_proj'})
        with self.assertRaisesRegex(ValueError, '只有 lora_A'):
            self.pl.lora_pairs(['model.layers.0.mlp.down_proj.lora_A.weight'])
        with self.assertRaisesRegex(ValueError, '不认识'):
            self.pl.lora_pairs(['model.layers.0.mlp.down_proj.weight'])

    def test_targets_skip_mtp_vision_and_head(self):
        got = self.pl.lora_target_names(['model.layers.0.mlp.down_proj', 'model.language_model.layers.1.linear_attn.in_proj_qkv'],
                                        S_SHAPES)
        self.assertEqual(got, {DOWN: 'model.layers.0.mlp.down_proj', QKV: 'model.language_model.layers.1.linear_attn.in_proj_qkv'})
        with self.assertRaisesRegex(ValueError, '0 个主干矩阵'):
            self.pl.lora_target_names(['model.layers.5.mlp.down_proj'], S_SHAPES)
        with self.assertRaisesRegex(ValueError, '解码层'):
            self.pl.lora_target_names(['lm_head'], S_SHAPES)
        with self.assertRaisesRegex(ValueError, '0 个主干矩阵'):                     # a norm is not a backbone matrix
            self.pl.lora_target_names(['model.layers.1.input_layernorm'], S_SHAPES)

    # ------------------------------------------------------------ the source
    def test_rows_are_scale_b_a_in_float32(self):
        src = self.pl.LoraSource(self.adapter(rank=4, alpha=8), S_SHAPES, 'StartLuxLoRA')
        self.assertEqual(src.scale, 2.0)
        self.assertEqual(set(src.map), {DOWN, QKV})
        self.assertTrue(src.has(DOWN) and not src.has('model.language_model.layers.0.mlp.up_proj.weight'))
        rows = src.rows(DOWN, 2, 6)
        self.assertEqual(rows.dtype, torch.float32)
        self.assertTrue(torch.allclose(rows, 2.0 * (self.b_down @ self.a_down)[2:6]))
        self.assertTrue(torch.allclose(src.rows(QKV, 0, 24), 2.0 * self.b_qkv @ self.a_qkv))
        self.assertTrue(bool(src.support(DOWN, 0, 3).all()))
        self.assertFalse(bool(src.support('lm_head.weight', 0, 3).any()))
        ident = src.identity
        self.assertEqual((ident['kind'], ident['rank'], ident['matrices']), ('lora', 4, 2))
        self.assertEqual(ident['base']['repo'], 'Qwen/Qwen3.6-27B')
        self.assertIsNone(src.repo)                                    # read as a local store, not a repository

    def test_refuses_a_changed_adapter_and_wrong_shapes(self):
        d = self.adapter()
        manifest = json.loads((d / 'trace_lora_manifest.json').read_text())
        (d / 'trace_lora_manifest.json').write_text(json.dumps({**manifest, 'adapter_sha256': '0' * 64}))
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            self.pl.LoraSource(d, S_SHAPES)
        write_adapter(self.dir, {'0.mlp.down_proj': (torch.randn(4, 9), torch.randn(8, 4))})
        with self.assertRaisesRegex(ValueError, '对不上'):
            self.pl.LoraSource(self.dir, S_SHAPES)
        (self.dir / 'trace_lora_manifest.json').unlink()
        with self.assertRaisesRegex(ValueError, '缺少'):
            self.pl.LoraSource(self.dir, S_SHAPES)

    # ------------------------------------------------------------ aux_plan
    def test_plan_waits_for_an_empty_path_and_checks_fields(self):
        base = {'donor_weight': 10, 'lambda_grid': [0.05]}
        item = {'tag': 'StartLuxLoRA', 'format': 'lora', 'path': '', 'weight': 4, 'required': True, 'late': True}
        _, ready, pending, _ = self.pl.aux_plan({**base, 'aux_extras': [item]})
        self.assertEqual(([c['tag'] for c in pending], ready), (['StartLuxLoRA'], []))
        _, ready, pending, _ = self.pl.aux_plan({**base, 'aux_extras': [{**item, 'required': False}]})
        self.assertEqual((ready, pending), ([], []))
        _, ready, pending, _ = self.pl.aux_plan({**base, 'aux_extras': [{**item, 'path': '/drive/adapter'}]})
        self.assertEqual((ready[0]['path'], ready[0]['coefficient'], pending), ('/drive/adapter', 0.4, []))
        with self.assertRaisesRegex(ValueError, '只填 path'):
            self.pl.aux_plan({**base, 'aux_extras': [{**item, 'repo': 'x/y'}]})
        with self.assertRaisesRegex(ValueError, 'path 只用于'):
            self.pl.aux_plan({**base, 'aux_extras': [{'tag': 'X', 'repo': 'x/y', 'path': '/p', 'weight': 1}]})

    # ------------------------------------------------------------ the term inside D
    def test_term_is_added_onto_an_earlier_d(self):
        src = self.pl.LoraSource(self.adapter(rank=4, alpha=8), S_SHAPES, 'StartLuxLoRA')
        torch.manual_seed(3)
        earlier = {n: torch.randn(*S_SHAPES[n]) * 0.01 for n in (DOWN, 'model.language_model.layers.0.mlp.up_proj.weight')}

        class Earlier:                                                 # a complete D without the LoRA term
            tags = {'Winery'}
            directory = 'earlier'

            def rows(self, name, i, j):
                return earlier[name][i:j].reshape(j - i, -1).float()

        class Subject:
            shapes = S_SHAPES

        ctx = {'S': Subject(), 'B': None, 'M': None, 'settings': {'rows_mib': 64}}
        sources = [{'tag': 'Winery', 'format': 'gguf'},
                   {'tag': 'StartLuxLoRA', 'format': 'lora', 'node': src, 'reference': None, 'coefficient': 0.4}]
        out, stats = self.pl.aux_delta_tensor(ctx, sources, DOWN, base_node=Earlier())
        want = (earlier[DOWN] + 0.4 * 2.0 * (self.b_down @ self.a_down)).to(torch.float16)
        self.assertTrue(torch.equal(out, want))
        self.assertGreater(stats['component_sq']['StartLuxLoRA'], 0)
        name = 'model.language_model.layers.0.mlp.up_proj.weight'    # not adapted: D stays the earlier D
        out, stats = self.pl.aux_delta_tensor(ctx, sources, name, base_node=Earlier())
        self.assertTrue(torch.equal(out, earlier[name].to(torch.float16)))
        self.assertEqual(stats['component_sq']['StartLuxLoRA'], 0.)

    def test_summary_and_inputs(self):
        src = self.pl.LoraSource(self.adapter(rank=4, alpha=8), S_SHAPES, 'StartLuxLoRA')
        sources = [{'tag': 'StartLuxLoRA', 'format': 'lora', 'node': src, 'coefficient': 0.4}]
        out = self.pl._summarize_delta([{'component_sq': {'StartLuxLoRA': 4.0}}], sources)
        self.assertEqual(out['component_norms']['StartLuxLoRA'], 2.0)
        self.assertAlmostEqual(out['lora']['StartLuxLoRA']['delta_norm_before_coefficient'], 5.0)
        self.assertEqual(out['lora']['StartLuxLoRA']['matrices'], 2)
        self.assertNotIn('lora', self.pl._summarize_delta([{'component_sq': {}}], []))
        ctx = {'S_repo': 's/s', 'M_repo': 'm/m', 'B_repo': 'b/b', 'sources': [{**sources[0], 'repo': ''}], 'searched': []}
        self.assertEqual(self.pl.source_repos(ctx), ['s/s', 'm/m', 'b/b'])   # a local adapter has no repository to list


class SettingsCellLora(unittest.TestCase):
    def test_startlux_lora_takes_startlux_place(self):
        nb = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
        cell = next(''.join(c['source']) for c in nb['cells'] if 'SETTINGS = {' in ''.join(c['source']))
        self.assertIn('STARTLUX_REQUIRED = False', cell)
        self.assertRegex(cell, r'TRACE_LORA_DIR = "[^"]*"')
        self.assertIn('TRACE_LORA_REQUIRED = True', cell)
        self.assertRegex(cell, r'\{"tag": "StartLuxLoRA", "format": "lora", "path": TRACE_LORA_DIR, "weight": 4, '
                               r'"required": TRACE_LORA_REQUIRED, "late": True\}')
        self.assertTrue(re.search(r'"tag": "StartLux", "repo": STARTLUX_REPO', cell))


if __name__ == '__main__':
    unittest.main()
