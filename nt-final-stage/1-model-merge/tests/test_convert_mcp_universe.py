"""convert_mcp_universe.py: rebuilding standard conversations from the MCP-Universe raw logs (standard library only)."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import convert_mcp_universe as cm  # noqa: E402

TASK = 'You are an agent. ## Your Task\nCompute the return.'


def call(ts, request, reasoning, content='', tool_calls=None, finish='tool_calls'):
    message = {'role': 'assistant', 'content': content or None, 'reasoning_content': reasoning,
               'tool_calls': [{'id': i, 'type': 'function', 'function': {'name': n, 'arguments': a}} for i, n, a in (tool_calls or [])] or None}
    return {'timestamp': ts, 'data': {'type': 'llm', 'class': 'OpenAIModel', 'messages': request,
                                      'response': {'choices': [{'message': message, 'finish_reason': finish}]}}}


def framework_history():
    """Three model calls the way the framework records them: each answer is written back as two assistant messages
    (the reasoning as plain text, then the tool calls), the tool results follow, then a reminder."""
    r1 = [{'role': 'user', 'content': TASK}]
    step1 = [{'role': 'assistant', 'content': 'look up prices'},
             {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'c1', 'type': 'function', 'function': {'name': 'yfinance__get', 'arguments': '{"ticker": "MSFT"}'}},
                                                                    {'id': 'c2', 'type': 'function', 'function': {'name': 'calc__calculate', 'arguments': '{"expression": "1+1"}'}}]},
             {'role': 'tool', 'tool_call_id': 'c1', 'content': 'REWRITTEN price table'},
             {'role': 'tool', 'tool_call_id': 'c2', 'content': [{'type': 'text', 'text': '2'}]},
             {'role': 'user', 'content': 'You have 19 steps remaining. Please continue.'}]
    r2 = r1 + step1
    step2 = [{'role': 'assistant', 'content': 'compute'},
             {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'c3', 'type': 'function', 'function': {'name': 'calc__calculate', 'arguments': '{"expression": 2.5}'}}]},
             {'role': 'tool', 'tool_call_id': 'c3', 'content': '2.5'},
             {'role': 'user', 'content': 'You have 18 steps remaining. Please continue.'}]
    r3 = r2 + step2
    return [call(1.0, r1, 'look up prices', tool_calls=[('c1', 'yfinance__get', '{"ticker": "MSFT"}'), ('c2', 'calc__calculate', '{"expression": "1+1"}')]),
            call(2.0, r2, 'compute', tool_calls=[('c3', 'calc__calculate', '{"expression": 2.5}')]),
            call(3.0, r3, 'done', content='{"answer": "90"}', finish='stop')]


class Convert(unittest.TestCase):
    def test_rebuild_uses_responses_and_what_the_model_saw(self):
        records = framework_history()
        spans = [{'trace_id': 't', 'records': [r], 'timestamp': r['timestamp']} for r in reversed(records)]   # out of order on disk
        calls = cm.model_calls([spans], {'t'})
        msgs = cm.rebuild(calls)
        self.assertEqual([m['role'] for m in msgs], ['user', 'assistant', 'tool', 'tool', 'assistant', 'tool', 'assistant'])
        self.assertEqual(msgs[1]['reasoning_content'], 'look up prices')
        self.assertEqual([c['id'] for c in msgs[1]['tool_calls']], ['c1', 'c2'])
        self.assertEqual(msgs[2]['content'], 'REWRITTEN price table')          # the text in the next request, not the raw tool output
        self.assertEqual(msgs[3]['content'], '2')
        self.assertEqual(msgs[-1], {'role': 'assistant', 'content': '{"answer": "90"}', 'reasoning_content': 'done'})
        kept = cm.rebuild(calls, keep_reminders=True)
        self.assertEqual(sum(m['role'] == 'user' for m in kept), 3)

    def test_mismatches_are_refused(self):
        records = framework_history()
        records[1]['data']['messages'] = [m for m in records[1]['data']['messages'] if m.get('tool_call_id') != 'c2']
        with self.assertRaisesRegex(ValueError, '没有返回'):
            cm.rebuild(cm.model_calls([[{'trace_id': 't', 'records': records}]], {'t'}))
        with self.assertRaisesRegex(ValueError, '没有模型调用'):
            cm.rebuild([])

    def test_several_json_documents_and_other_traces(self):
        records = framework_history()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'trace.json'
            path.write_text(json.dumps([{'trace_id': 't', 'records': records[:2]}]) + '\n' +
                            json.dumps([{'trace_id': 't', 'records': records[2:]}, {'trace_id': 'other', 'records': records}]), encoding='utf-8')
            docs = cm.load_documents(path)
        self.assertEqual(len(docs), 2)
        self.assertEqual(len(cm.model_calls(docs, {'t'})), 3)

    def test_domain_tools(self):
        msgs = cm.rebuild(cm.model_calls([[{'trace_id': 't', 'records': framework_history()}]], {'t'}))
        tools = cm.domain_tools([{'domain': 'financial_analysis', 'messages': msgs}])['financial_analysis']
        by = {t['function']['name']: t['function']['parameters'] for t in tools}
        self.assertEqual(sorted(by), ['calc__calculate', 'yfinance__get'])
        self.assertEqual(by['calc__calculate']['properties'], {'expression': {'type': ['number', 'string']}})
        self.assertEqual(by['calc__calculate']['required'], ['expression'])


if __name__ == '__main__':
    unittest.main()
