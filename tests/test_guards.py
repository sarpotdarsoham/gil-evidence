import unittest
from guard_evidence import analyze_guards

class GuardTests(unittest.TestCase):
 def source(self,condition,helper='',body='assert not sys._is_gil_enabled()'):
  return 'import sys\nimport sysconfig\nimport pytest\n'+helper+'\n@pytest.mark.skipif('+condition+', reason="FT check")\ndef test_gil():\n    '+body+'\n'
 def masked(self,s):return any(r['status']=='SELF_MASKING_GIL_GUARD_CANDIDATE' for r in analyze_guards(s)['findings'])
 def test_direct_mask(self):self.assertTrue(self.masked(self.source('sys._is_gil_enabled()')))
 def test_build_guard(self):self.assertFalse(self.masked(self.source('not sysconfig.get_config_var("Py_GIL_DISABLED")')))
 def test_helper(self):
  h='def ft():\n    f = getattr(sys, "_is_gil_enabled", None)\n    return callable(f) and not f()\n'
  self.assertTrue(self.masked(self.source('not ft()',h)))
 def test_unknown_helper(self):self.assertFalse(self.masked(self.source('is_unsupported()')))
 def test_unknown_in_disjunction(self):self.assertFalse(self.masked(self.source('sys._is_gil_enabled() or unknown()')))
 def test_build_aware_runtime_guard(self):self.assertFalse(self.masked(self.source('not sysconfig.get_config_var("Py_GIL_DISABLED") and sys._is_gil_enabled()')))
 def test_print_not_assertion(self):self.assertFalse(self.masked(self.source('sys._is_gil_enabled()',body='print(sys._is_gil_enabled())')))
 def test_helper_rebound(self):
  h='def ft():\n    return not sys._is_gil_enabled()\nft = arbitrary\n'
  self.assertFalse(self.masked(self.source('not ft()',h)))
 def test_local_shadow(self):
  self.assertFalse(self.masked(self.source('sys._is_gil_enabled()',body='sys = arbitrary\n    assert not sys._is_gil_enabled()')))
 def test_class_guard(self):
  s='import sys\nimport pytest\n@pytest.mark.skipif(sys._is_gil_enabled(),reason="FT")\nclass TestGIL:\n    def test_gil(self):\n        assert not sys._is_gil_enabled()\n'
  self.assertTrue(self.masked(s))

 def test_truthy_integer_condition(self):
  self.assertTrue(self.masked(self.source('sys._is_gil_enabled() and sysconfig.get_config_var("Py_GIL_DISABLED")')))
 def test_string_condition(self):
  self.assertTrue(self.masked(self.source(repr('sys._is_gil_enabled()'))))
 def test_module_guard(self):
  s='import sys\nimport pytest\npytestmark = pytest.mark.skipif(sys._is_gil_enabled(),reason="FT")\ndef test_gil():\n    assert not sys._is_gil_enabled()\n'
  self.assertTrue(self.masked(s))
 def test_decorated_helper_unknown(self):
  h='def identity(f):\n    return f\n@identity\ndef ft():\n    return not sys._is_gil_enabled()\n'
  self.assertFalse(self.masked(self.source('not ft()',h)))
