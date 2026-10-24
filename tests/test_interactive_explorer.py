"""Reusable, public test coverage for the offline flow explorer."""
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
SCRIPT=BASE/'scripts'/'interactive_explorer.py'
spec=importlib.util.spec_from_file_location('interactive_explorer',SCRIPT)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ExplorerTests(unittest.TestCase):
  def setUp(self):
    self.model=json.loads((BASE/'examples/sample_explorer_spec.json').read_text(encoding='utf-8'))
  def test_generic_spec_is_valid(self):
    self.assertTrue(module.validate_views(self.model))
  def test_reject_unknown_node_in_trace(self):
    self.model['tracks'][0]['steps'][0]['node']='missing'
    with self.assertRaises(ValueError):module.validate_views(self.model)
  def test_reject_unknown_function_jump(self):
    self.model['views'][0]['nodes'][0]['jump']='unknown'
    with self.assertRaises(ValueError):module.validate_views(self.model)
  def test_reject_invalid_stage_node(self):
    self.model['views'][0]['stages'][0]['items'].append('missing')
    with self.assertRaises(ValueError):module.validate_views(self.model)
  @unittest.skipUnless(shutil.which('dot'),'Graphviz not installed')
  def test_self_contained_html(self):
    doc=module.render_html(self.model['views'],self.model['source'],self.model['tracks'],BASE/'templates/explorer.html')
    self.assertIn('const TRACKS=',doc)
    self.assertIn('function renderBoard()',doc)
    self.assertIn('function fitWidthTop()',doc)
    self.assertIn('<svg ',doc)
    self.assertNotIn('<script src=',doc)
    self.assertNotIn('cdn.jsdelivr',doc)
    # The PUBLIC sample must not include details from any private demonstration.
    self.assertNotIn('private-company/private-source',doc)
    self.assertNotIn('confidential_parameter',doc)

if __name__=='__main__':unittest.main()
