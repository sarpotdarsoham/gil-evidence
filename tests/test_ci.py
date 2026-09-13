import ast,unittest
from gil_evidence import analyze
from ci_evidence import inspect_script

class ProcessEvidenceTests(unittest.TestCase):
 def test_separate_processes(self):
  d=inspect_script("python -c 'import sys; assert not sys._is_gil_enabled()'\npython -m pytest\n")
  self.assertEqual(d['processes'][0]['end_evidence']['status'],'CHECK_COVERS_CHECKPOINT')
  self.assertEqual(d['processes'][1]['separate_process_checks'],[1])
  self.assertEqual(d['processes'][1]['entry_check'],'NOT_ESTABLISHED_FROM_THIS_COMMAND')
 def test_same_process(self):
  d=inspect_script("python -c 'import sys; import pytest; assert not sys._is_gil_enabled(); pytest.main()'")
  self.assertEqual(d['processes'][0]['checks'][0]['status'],'CHECK_COVERS_CHECKPOINT')
 def test_late_import(self):
  d=inspect_script("python -c 'import sys; assert not sys._is_gil_enabled(); import pytest; pytest.main()'")
  self.assertEqual(d['processes'][0]['checks'][0]['status'],'CHECK_NOT_ESTABLISHED')
 def test_optimized(self):
  d=inspect_script("python -O -c 'import sys; import pytest; assert not sys._is_gil_enabled(); pytest.main()'")
  self.assertEqual(d['processes'][0]['checks'][0]['status'],'CHECK_NOT_ESTABLISHED')
 def test_force_separate_from_check(self):
  d=inspect_script('PYTHON_GIL=0 python -m pytest')
  self.assertTrue(d['processes'][0]['forced_gil_disabled_requested'])
  self.assertEqual(d['processes'][0]['entry_check'],'NOT_ESTABLISHED_FROM_THIS_COMMAND')
 def test_expansion_abstains(self):
  self.assertEqual(inspect_script('python -c "$CODE"')['status'],'UNKNOWN')
 def test_quote_and_semicolon(self):
  d=inspect_script("python -c 'import sys; assert not sys._is_gil_enabled()' && pytest")
  self.assertEqual(len(d['processes']),2)
 def test_same_line_requires_column(self):
  s='import sys; assert not sys._is_gil_enabled(); checkpoint()'
  with self.assertRaises(ValueError):analyze(s,1)
  column=ast.parse(s).body[-1].col_offset
  self.assertEqual(analyze(s,1,column=column)['status'],'CHECK_COVERS_CHECKPOINT')
 def test_shadowed_pytest_not_claimed(self):
  d=inspect_script("python -c 'import pytest; pytest = fake; pytest.main()'")
  self.assertEqual(d['processes'][0]['checks'],[])
