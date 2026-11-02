"""StartLux_trace_LoRA.ipynb: the embedded module trace_lora.

Pure parts (records, messages, tools, rendering, loss labels, split, schedule, export check) run with the standard
library. The end-to-end part trains a LoRA on a tiny random Llama on the CPU (needs torch, transformers, peft), resumes
from a checkpoint, exports the adapter, and reads it back with the fusion notebook's "lora" source.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NOTEBOOK = HERE.parent / 'StartLux_trace_LoRA.ipynb'


def trace_source():
    nb = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
    for cell in nb['cells']:
        src = ''.join(cell['source'])
        if "TRACE_SOURCE = r'''" in src:
            start = src.index("TRACE_SOURCE = r'''") + len("TRACE_SOURCE = r'''")
            return src[start:src.index("'''", start)]
    raise AssertionError('no embedded trace_lora module')


def load_trace():
    if 'trace_lora' not in sys.modules:
        directory = Path(tempfile.mkdtemp(prefix='tracemod-'))
        (directory / 'trace_lora.py').write_text(trace_source(), encoding='utf-8')
        spec = importlib.util.spec_from_file_location('trace_lora', directory / 'trace_lora.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules['trace_lora'] = module
        spec.loader.exec_module(module)
    return sys.modules['trace_lora']


try:
    import torch
    import transformers  # noqa: F401
    import peft  # noqa: F401
    HAVE_STACK = True
except ImportError:
    HAVE_STACK = False


class FakeTokenizer:
    """ChatML rendering (tools, reasoning, tool calls, tool responses) and a character-level encoding whose special
    tokens are single tokens: enough to check which tokens carry the loss."""
    SPECIALS = ['<|im_start|>', '<|im_end|>', '<think>', '</think>', '<tool_call>', '</tool_call>', '<tool_response>', '</tool_response>']
    is_fast = True

    def apply_chat_template(self, messages, tools=None, tokenize=False, add_generation_prompt=False, **kw):
        out = []
        if tools:
            out.append('<|im_start|>system\n# Tools\n' + '\n'.join(json.dumps(t, sort_keys=True) for t in tools) + '<|im_end|>\n')
        last_user = max((k for k, m in enumerate(messages) if m['role'] == 'user'), default=-1)
        for k, m in enumerate(messages):
            if m['role'] == 'assistant':
                body = m['content']
                if k > last_user:
                    body = '<think>\n' + m.get('reasoning_content', '').strip() + '\n</think>\n\n' + body
                for c in m.get('tool_calls', []):
                    body += '<tool_call>\n' + json.dumps({'name': c['function']['name'], 'arguments': c['function']['arguments']}) + '\n</tool_call>'
                out.append('<|im_start|>assistant\n' + body + '<|im_end|>\n')
            elif m['role'] == 'tool':
                out.append('<|im_start|>user\n<tool_response>\n' + m['content'] + '\n</tool_response><|im_end|>\n')
            else:
                out.append(f'<|im_start|>{m["role"]}\n' + m['content'] + '<|im_end|>\n')
        return ''.join(out)

    def __call__(self, text, add_special_tokens=False, return_offsets_mapping=True):
        ids, offsets, pos = [], [], 0
        pattern = re.compile('|'.join(re.escape(s) for s in self.SPECIALS))
        while pos < len(text):
            m = pattern.match(text, pos)
            if m:
                ids.append(self.SPECIALS.index(m.group(0)))
                offsets.append((pos, m.end()))
                pos = m.end()
            else:
                ids.append(len(self.SPECIALS) + ord(text[pos]) % 200)
                offsets.append((pos, pos + 1))
                pos += 1
        return {'input_ids': ids, 'offset_mapping': offsets}


def record(task, answer, reward=1.0, reasoning='think it over'):
    return {'task_id': task, 'reward': reward, 'messages': [
        {'role': 'system', 'content': 'You are an agent.'},
        {'role': 'user', 'content': [{'type': 'text', 'text': f'Task {task}: compute the CAGR.'}]},
        {'role': 'assistant', 'content': '', 'provider_specific_fields': {'reasoning_content': reasoning},
         'tool_calls': [{'id': 'c1', 'type': 'function', 'function': {'name': 'code_exec', 'arguments': '{"code": "print(1)", "timeout": 30}'}}]},
        {'role': 'tool', 'tool_call_id': 'c1', 'content': [{'type': 'text', 'text': '{"output": "1"}'}]},
        {'role': 'assistant', 'content': f'The answer is {answer}.', 'reasoning_content': 'done'},
        {'role': 'user', 'content': 'trailing note that carries no loss'},
    ]}


class PureParts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = load_trace()

    def test_messages_are_normalized(self):
        msgs = self.t.normalize_messages(self.t.find_messages(record('a', 1)))
        self.assertEqual([m['role'] for m in msgs], ['system', 'user', 'assistant', 'tool', 'assistant'])   # trailing user dropped
        self.assertEqual(msgs[1]['content'], 'Task a: compute the CAGR.')
        self.assertEqual(msgs[2]['reasoning_content'], 'think it over')
        self.assertEqual(msgs[2]['tool_calls'][0]['function']['arguments'], {'code': 'print(1)', 'timeout': 30})
        self.assertEqual((msgs[3]['tool_call_id'], msgs[3]['content']), ('c1', '{"output": "1"}'))
        with self.assertRaisesRegex(ValueError, '没有助手回合'):
            self.t.normalize_messages([{'role': 'user', 'content': 'hi'}])
        with self.assertRaisesRegex(ValueError, '合法 JSON'):
            self.t.parse_arguments('{oops')
        with self.assertRaisesRegex(ValueError, '非文本'):
            self.t.text_of([{'type': 'image_url', 'image_url': 'x'}])
        self.assertEqual(self.t.find_messages({'trajectory': {'messages': [{'role': 'user'}]}}), [{'role': 'user'}])

    def test_tools(self):
        msgs = [self.t.normalize_messages(self.t.find_messages(record('a', 1)))]
        msgs[0][2]['tool_calls'].append({'type': 'function', 'function': {'name': 'code_exec', 'arguments': {'code': 'x'}}})
        tools = self.t.synthesize_tools(msgs)
        params = tools[0]['function']['parameters']
        self.assertEqual(tools[0]['function']['name'], 'code_exec')
        self.assertEqual(params['properties'], {'code': {'type': 'string'}, 'timeout': {'type': 'integer'}})
        self.assertEqual(params['required'], ['code'])
        mcp = self.t.normalize_tools([{'name': 'read_tab', 'description': 'd', 'inputSchema': {'type': 'object'}}])
        self.assertEqual(mcp[0]['function'], {'name': 'read_tab', 'description': 'd', 'parameters': {'type': 'object'}})

    def test_scores(self):
        self.assertEqual(self.t.record_score({'reward': 1}), 1.0)
        self.assertEqual(self.t.record_score({'passed': 'pass'}), 1.0)
        self.assertEqual(self.t.record_score({'grades': {'score': 0.25}}, 'grades.score'), 0.25)
        self.assertIsNone(self.t.record_score({'other': 1}))

    def test_spans_and_labels(self):
        text = ('<|im_start|>user\nhi<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\nHello<|im_end|>\n'
                '<|im_start|>assistant\n<think>\nplan\n</think>\n\nOK<|im_end|>\n')
        spans = self.t.assistant_spans(text)
        self.assertEqual([text[a:b] for a, b in spans], ['Hello<|im_end|>', '<think>\nplan\n</think>\n\nOK<|im_end|>'])
        kept = self.t.assistant_spans(text, mask_empty_think=False)
        self.assertTrue(text[kept[0][0]:kept[0][1]].startswith('<think>'))
        self.assertEqual(self.t.label_mask([(0, 2), (spans[0][0], spans[0][0] + 1), (spans[0][1] - 1, spans[0][1] + 1), (5, 5)], spans),
                         [False, True, False, False])
        with self.assertRaisesRegex(ValueError, '结束标记'):
            self.t.assistant_spans('<|im_start|>assistant\nno end')

    def test_prepare_trains_only_on_assistant_turns(self):
        tok = FakeTokenizer()
        recs = [('f:1', record('a', 1)), ('f:2', record('b', 2, reward=0.0)), ('f:3', {'nothing': 1}),
                ('f:4', record('c', 3) | {'reward': 1, 'messages': record('c', 3)['messages'] * 30})]
        examples, report = self.t.prepare(recs, tok, {'min_score': 1.0, 'max_tokens': 2000})
        self.assertEqual((report['kept'], report['below_min_score'], report['no_messages'], report['too_long']), (1, 1, 1, 1))
        self.assertEqual(report['scores'], {'1': 2, '0': 1})
        ex = examples[0]
        text = tok.apply_chat_template(self.t.normalize_messages(record('a', 1)['messages']),
                                       tools=self.t.synthesize_tools([self.t.normalize_messages(record('a', 1)['messages'])]))
        labelled = ''.join(text[a:b] for (a, b), y in zip(tok(text)['offset_mapping'], ex['labels']) if y != -100)
        self.assertIn('<tool_call>', labelled)
        self.assertIn('"code_exec"', labelled)
        self.assertIn('The answer is 1.', labelled)
        self.assertIn('done', labelled)                                # reasoning of the last turn carries loss
        self.assertNotIn('Task a', labelled)                           # the user's words do not
        self.assertNotIn('{"output": "1"}', labelled)                  # nor the tool's
        self.assertNotIn('# Tools', labelled)
        self.assertEqual(labelled.count('<|im_end|>'), 2)              # each assistant turn learns to stop
        everything, _ = self.t.prepare(recs[:2], tok, {'min_score': None, 'max_tokens': 2000})
        self.assertEqual(len(everything), 2)

    def test_split_schedule_plan(self):
        examples = [{'id': f'x{i}'} for i in range(40)]
        train, held = self.t.split(examples, 0.05, 64, seed=1)
        self.assertEqual((len(train), len(held)), (38, 2))
        self.assertEqual(held, self.t.split(examples, 0.05, 64, seed=1)[1])
        self.assertEqual(len(self.t.split(examples[:3], 0.05, 64)[1]), 1)
        lrs = [self.t.learning_rate(s, 100, 1e-4) for s in range(100)]
        self.assertAlmostEqual(lrs[4], 1e-4)                            # end of the 5-step warm-up
        self.assertAlmostEqual(lrs[-1], 1e-5, delta=2e-7)               # cosine down to 10%
        plan = self.t.step_plan(10, 4, 2, seed=0)
        self.assertEqual([len(g) for g in plan], [4, 4, 2, 4, 4, 2])
        self.assertEqual(sorted(sum(plan[:3], [])), list(range(10)))
        self.assertEqual(self.t.precision_for(80), 'bf16')
        self.assertEqual(self.t.precision_for(40), '4bit')
        self.assertIsNone(self.t.precision_for(24))

    def test_adapter_key_check(self):
        ok = ['base_model.model.model.language_model.layers.0.mlp.down_proj.lora_A.weight',
              'base_model.model.model.language_model.layers.0.mlp.down_proj.lora_B.weight']
        self.assertEqual(self.t.adapter_key_problems(ok), [])
        self.assertTrue(self.t.adapter_key_problems(ok[:1]))
        self.assertTrue(self.t.adapter_key_problems(['base_model.model.lm_head.lora_A.weight', 'base_model.model.lm_head.lora_B.weight']))
        self.assertTrue(self.t.adapter_key_problems(['base_model.model.model.visual.blocks.0.attn.qkv.lora_A.weight']))

    def test_notebook_metadata_matches_module(self):
        nb = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
        meta = nb['metadata']['trace_lora']
        self.assertEqual(meta['module_sha256'], hashlib.sha256(trace_source().encode()).hexdigest())
        self.assertEqual(meta['version'], self.t.VERSION)
        self.assertFalse(meta['real_27b_tested'])
        settings = next(''.join(c['source']) for c in nb['cells'] if 'BASE_REPO =' in ''.join(c['source']))
        self.assertIn('BASE_REPO = "Qwen/Qwen3.6-27B"', settings)
        self.assertIn('"min_score": 1.0', settings)


@unittest.skipUnless(HAVE_STACK, 'needs torch, transformers and peft')
class EndToEnd(unittest.TestCase):
    """A tiny Llama stands in for the 27B: the same calls, on the CPU."""

    @classmethod
    def setUpClass(cls):
        cls.t = load_trace()
        tok = FakeTokenizer()
        recs = [(f'f:{i}', record(chr(97 + i), i)) for i in range(6)]
        cls.examples, _ = cls.t.prepare(recs, tok, {'min_score': 1.0, 'max_tokens': 4000})

    def fresh(self, lora_seed=1):
        """The same base every time (as when it is loaded from the checkpoint); the LoRA initialisation may differ."""
        from transformers import LlamaConfig, LlamaForCausalLM
        torch.manual_seed(0)
        cfg = LlamaConfig(vocab_size=220, hidden_size=32, intermediate_size=64, num_hidden_layers=2, num_attention_heads=4,
                          num_key_value_heads=2, max_position_embeddings=4096, tie_word_embeddings=False)
        model = LlamaForCausalLM(cfg)
        targets = self.t.lora_targets(model)
        torch.manual_seed(lora_seed)
        return self.t.add_lora(model, targets, rank=4, alpha=8), targets

    def test_train_resume_export_and_read_back(self):
        t = self.t
        model, targets = self.fresh()
        self.assertEqual(len(targets), 14)                              # 7 linear layers in each of 2 decoder layers
        self.assertTrue(all(re.search(r'layers\.\d+\.(self_attn|mlp)\.', n) for n in targets))
        decoder, head = t.decoder_and_head(model)
        check = t.check_decoder(model, decoder, head, self.examples[0], torch.device('cpu'))
        self.assertTrue(check['ok'], check)
        loss, n = t.example_loss(decoder, head, self.examples[0], torch.device('cpu'), chunk=7)
        ids = torch.tensor([self.examples[0]['input_ids']])
        labels = torch.tensor([self.examples[0]['labels']])
        full = torch.nn.functional.cross_entropy(model(input_ids=ids).logits[0, :-1], labels[0, 1:], ignore_index=-100, reduction='sum')
        self.assertTrue(torch.allclose(loss, full, rtol=1e-4), (loss, full))        # chunked loss = the full loss
        opts = {'lr': 1e-2, 'epochs': 3, 'accumulation': 2, 'save_every': 2, 'seed': 0, 'chunk': 64}
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            before = t.evaluate(decoder, head, self.examples, torch.device('cpu'))['mean_loss']
            history, finished = t.train(model, self.examples, opts, tmp / 'straight', 'run', log=lambda *_: None)
            after = t.evaluate(decoder, head, self.examples, torch.device('cpu'))['mean_loss']
            self.assertTrue(finished)
            self.assertEqual(len(history), 9)
            self.assertLess(after, before)
            straight = t.trainable_state(model)
            self.assertEqual(sorted(p.name for p in (tmp / 'straight').iterdir()), ['ckpt-000008', 'ckpt-000009'])

            # the same run cut into two sessions gives the same adapter
            first, _ = self.fresh()
            h1, done1 = t.train(first, self.examples, {**opts, 'max_steps_per_session': 4}, tmp / 'cut', 'run', log=lambda *_: None)
            self.assertEqual((len(h1), done1), (4, False))
            second, _ = self.fresh(lora_seed=7)                         # another LoRA init: the checkpoint replaces it
            h2, done2 = t.train(second, self.examples, opts, tmp / 'cut', 'run', log=lambda *_: None)
            self.assertEqual((len(h2), done2), (5, True))
            resumed = t.trainable_state(second)
            for k in straight:
                self.assertTrue(torch.allclose(straight[k], resumed[k], atol=1e-6), k)
            _, start = t.latest_checkpoint(tmp / 'cut', 'other run')
            self.assertEqual(start, 0)                                  # another identity never resumes

            # export, then read it back with the fusion notebook's reader
            manifest = t.export_adapter(model, tmp / 'adapter', {'base_repo': 'tiny', 'base_revision': 'r'})
            self.assertEqual(manifest['adapter_sha256'], t.sha_file(tmp / 'adapter' / 'adapter_model.safetensors'))
            sys.path.insert(0, str(HERE))
            from test_tm2 import load
            pl = load()['qmerge_pipeline']
            base_state = {k: v.detach().clone() for k, v in model.get_base_model().state_dict().items() if 'lora_' not in k}
            subject = {k.replace('model.layers.', 'model.language_model.layers.').replace('.base_layer', ''): tuple(v.shape)
                       for k, v in base_state.items()}
            src = pl.LoraSource(tmp / 'adapter', subject, 'StartLuxLoRA')
            self.assertEqual(len(src.map), 14)
            merged = model.merge_and_unload().state_dict()
            for name in src.map:
                peft_name = name.replace('model.language_model.layers.', 'model.layers.')
                w = base_state[peft_name.replace('.weight', '.base_layer.weight')]
                rows = src.rows(name, 0, w.shape[0])
                self.assertTrue(torch.allclose(w + rows, merged[peft_name], atol=1e-6), name)


if __name__ == '__main__':
    unittest.main()
