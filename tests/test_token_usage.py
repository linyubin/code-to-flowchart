from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
from token_usage import parse_usage,rough_tokens,append_event,report
from compact_ir import pack,unpack
from source_slice import select_functions
from incremental_pipeline import build

ROOT=Path(__file__).resolve().parents[1]
class TokenUsageTests(unittest.TestCase):
    def test_openai_reasoning_subset(self):
        v=parse_usage({'usage':{'input_tokens':100,'output_tokens':50,'total_tokens':150,'input_tokens_details':{'cached_tokens':20},'output_tokens_details':{'reasoning_tokens':30}}},'openai')
        self.assertEqual(v['total_tokens'],150);self.assertEqual(v['reasoning_tokens'],30)
    def test_anthropic_cache_separate(self):
        v=parse_usage({'usage':{'input_tokens':30,'cache_read_input_tokens':60,'cache_creation_input_tokens':10,'output_tokens':40}},'anthropic')
        self.assertEqual(v['input_tokens'],100);self.assertEqual(v['total_tokens'],140)
    def test_incomplete_usage_rejected(self):
        with self.assertRaises(ValueError):parse_usage({'usage':{'input_tokens':4}},'openai')
    def test_excess_reasoning_rejected(self):
        with self.assertRaises(ValueError):parse_usage({'input_tokens':4,'output_tokens':5,'output_tokens_details':{'reasoning_tokens':6}},'openai')
    def test_empty_estimator(self):self.assertEqual(rough_tokens(''),0)
    def test_ledger_mixed(self):
        with tempfile.TemporaryDirectory() as td:
            log=Path(td)/'usage.jsonl'
            append_event(log,{'stage':'read_source','measurement':'estimate','input_tokens':180,'output_tokens':0})
            append_event(log,{'stage':'write_ir','measurement':'exact','usage':{'input_tokens':100,'output_tokens':50,'cached_input_tokens':30,'reasoning_tokens':25}})
            append_event(log,{'stage':'render','measurement':'local'})
            data=report(log);self.assertEqual(data['measurement'],'mixed');self.assertEqual(data['totals']['exact_reasoning'],25)
    def test_provider_retry_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            log=Path(td)/'usages.jsonl'
            ev={'stage':'write_ir','run_id':'same','request_id':'response-abc','measurement':'exact','usage':{'input_tokens':30,'output_tokens':10,'cached_input_tokens':0,'reasoning_tokens':0}}
            append_event(log,ev);append_event(log,ev)
            self.assertEqual(report(log)['stages']['write_ir']['events'],1)

    def test_compact_roundtrip_preserves_sample(self):
        src=json.loads((ROOT/'examples/sample_flow.json').read_text())
        self.assertEqual(unpack(pack(src)),src)
    def test_compact_roundtrip_extended_metadata(self):
        src=json.loads((ROOT/'examples/sample_flow.json').read_text())
        src['functions'][0]['nodes'][0]['note']='optional metadata is retained'
        src['edges'][0]['reviewed']=True
        self.assertEqual(unpack(pack(src)),src)
    def test_python_slice_no_dynamic_claims(self):
        example='''def a():\n    b()\n    getattr(obj, "c")()\ndef b():\n    return 1\ndef c():\n    pass\n'''
        result=select_functions(example,['a'],1)
        self.assertEqual([x['name'] for x in result['functions']],['a','b'])
        self.assertEqual(result['unfollowed_local_calls'],[])
    def test_source_slice_boundary(self):
        example='''def a():\n    b()\ndef b():\n    c()\ndef c():\n    pass\n'''
        result=select_functions(example,['a'],1)
        self.assertEqual(result['unfollowed_local_calls'],['c'])
    def test_local_pipeline_cold_warm_and_invalidation(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'out';log=Path(td)/'events.jsonl';src=Path(td)/'source.py'
            src.write_text('VALUE=1\n')
            ir=ROOT/'examples/sample_flow.json'
            r1=build(ir,out,log,[src],request='test');r2=build(ir,out,log,[src],request='test')
            src.write_text('VALUE=2\n')
            with self.assertRaisesRegex(ValueError,'re-analyze code'):
                build(ir,out,log,[src],request='test')
            self.assertEqual([r1['cache_hit'],r2['cache_hit']],[False,True])
            totals=report(log)['totals'];self.assertEqual(totals['local_only'],1);self.assertEqual(totals['cache_hits'],1)
    def test_pipeline_viewer(self):
        with tempfile.TemporaryDirectory() as td:
            r=build(ROOT/'examples/sample_flow.json',Path(td),viewer_spec=ROOT/'examples/sample_explorer_spec.json')
            self.assertTrue(Path(r['viewer']).exists())
            self.assertIn('<svg',Path(r['viewer']).read_text())
if __name__=='__main__':unittest.main()
