import unittest
from gil_evidence import analyze

class EvidenceTests(unittest.TestCase):
    def result(self, body, optimized=False):
        source=body+'\ncheckpoint()\n'
        return analyze(source,len(source.splitlines()),optimized=optimized)['status']
    def test_semantic_boundaries(self):
        cases={
          'fresh':('import sys\nimport native\nassert not sys._is_gil_enabled()', 'CHECK_COVERS_CHECKPOINT'),
          'early':('import sys\nassert not sys._is_gil_enabled()\nimport native','CHECK_NOT_ESTABLISHED'),
          'printed':('import sys\nprint(sys._is_gil_enabled())','CHECK_NOT_ESTABLISHED'),
          'wrong_polarity':('import sys\nassert sys._is_gil_enabled()','CHECK_NOT_ESTABLISHED'),
          'buildflag':('import sysconfig\nassert sysconfig.get_config_var("Py_GIL_DISABLED")','CHECK_NOT_ESTABLISHED'),
          'onebranch':('import sys\nif flag:\n    assert not sys._is_gil_enabled()','CHECK_NOT_ESTABLISHED'),
          'bothbranches':('import sys\nif flag:\n    assert not sys._is_gil_enabled()\nelse:\n    assert sys._is_gil_enabled() is False','CHECK_COVERS_CHECKPOINT'),
          'guard':('import sys\nif sys._is_gil_enabled():\n    raise RuntimeError()','CHECK_COVERS_CHECKPOINT'),
          'late_call':('import sys\nassert not sys._is_gil_enabled()\nopaque()','CHECK_NOT_ESTABLISHED'),
          'rechecked':('import sys\nassert not sys._is_gil_enabled()\nopaque()\nassert not sys._is_gil_enabled()','CHECK_COVERS_CHECKPOINT'),
          'aliased':('import sys as runtime\nassert not runtime._is_gil_enabled()','CHECK_COVERS_CHECKPOINT'),
          'from_alias':('from sys import _is_gil_enabled as enabled\nassert not enabled()','CHECK_COVERS_CHECKPOINT'),
          'shadowed':('import sys\nsys = fake\nassert not sys._is_gil_enabled()','CHECK_NOT_ESTABLISHED'),
          'constant_exit':('assert False','UNREACHABLE_IN_MODEL'),
          'dead_branch':('import sys\nif False:\n    import native\nelse:\n    assert not sys._is_gil_enabled()','CHECK_COVERS_CHECKPOINT'),
          'swallowed':('import sys\ntry:\n    assert not sys._is_gil_enabled()\nexcept AssertionError:\n    pass','UNKNOWN'),
          'loop':('import sys\nwhile flag:\n    assert not sys._is_gil_enabled()','UNKNOWN'),
          'no_alias':('assert not sys._is_gil_enabled()','CHECK_NOT_ESTABLISHED'),
          'deleted':('import sys\ndel sys\nassert not sys._is_gil_enabled()','CHECK_NOT_ESTABLISHED'),
          'star':('from sys import *','UNKNOWN'),
        }
        for name,(source,expected) in cases.items():
            with self.subTest(name=name): self.assertEqual(self.result(source),expected)
    def test_optimization(self):
        self.assertEqual(self.result('import sys\nassert not sys._is_gil_enabled()',True),'CHECK_NOT_ESTABLISHED')
        self.assertEqual(self.result('import sys\nif sys._is_gil_enabled():\n    raise RuntimeError()',True),'CHECK_COVERS_CHECKPOINT')
    def test_branch_checkpoint_does_not_require_other_path(self):
        s='import sys\nif flag:\n    assert not sys._is_gil_enabled()\n    checkpoint()\n'
        self.assertEqual(analyze(s,4)['status'],'CHECK_COVERS_CHECKPOINT')
    def test_function_requires_own_binding(self):
        s='def test():\n    import sys\n    assert not sys._is_gil_enabled()\n    checkpoint()\n'
        self.assertEqual(analyze(s,4,function='test')['status'],'CHECK_COVERS_CHECKPOINT')
    def test_reject_invalid_checkpoint(self):
        with self.assertRaises(ValueError):analyze('pass\n',2)

if __name__=='__main__':unittest.main()
