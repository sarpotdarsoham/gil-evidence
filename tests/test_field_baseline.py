import ast
import unittest
from validation.field_study import direct


class FieldBaselineTests(unittest.TestCase):
    def test_direct_function_and_class_are_detected(self):
        for source in [
            '@pytest.mark.skipif(sys._is_gil_enabled())\ndef test_x():\n assert not sys._is_gil_enabled()',
            '@pytest.mark.skipif(sys._is_gil_enabled())\nclass TestX:\n def test_x(self):\n  assert not sys._is_gil_enabled()',
        ]:
            with self.subTest(source=source):
                self.assertTrue(direct(ast.parse(source)))

    def test_unrelated_skip_and_helper_are_not_direct(self):
        for guard in ['sys.version_info < (3, 12)', 'helper()']:
            source = '@pytest.mark.skipif(' + guard + ')\ndef test_x():\n assert not sys._is_gil_enabled()'
            with self.subTest(guard=guard):
                self.assertFalse(direct(ast.parse(source)))
