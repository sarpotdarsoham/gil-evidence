import shlex
import unittest

from ci_evidence import inspect_script
from gil_evidence import analyze


class BindingRegressionTests(unittest.TestCase):
    def test_walrus_cannot_preserve_sys_identity(self):
        for statement in ['(sys := fake)', 'assert (sys := fake)', 'if (sys := fake):\n    pass', 'other = (sys := fake)']:
            with self.subTest(statement=statement):
                source = 'import sys\n' + statement + '\nassert not sys._is_gil_enabled()\ncheckpoint()\n'
                self.assertNotEqual(analyze(source, len(source.splitlines()))['status'],
                                    'CHECK_COVERS_CHECKPOINT')

    def test_walrus_cannot_preserve_query_alias(self):
        source = 'from sys import _is_gil_enabled as query\n(query := fake)\nassert not query()\ncheckpoint()\n'
        self.assertEqual(analyze(source, 4)['status'], 'CHECK_NOT_ESTABLISHED')

    def test_pytest_rebindings_not_test_invocations(self):
        for statement in ['pytest: object = fake', 'pytest += fake', 'del pytest',
                          '(pytest := fake)', 'def pytest():\n    pass',
                          'class pytest:\n    pass', 'if flag:\n    pytest = fake',
                          'from anything import *']:
            with self.subTest(statement=statement):
                source = 'import pytest\n' + statement + '\npytest.main()'
                result = inspect_script('python -c ' + shlex.quote(source))
                self.assertEqual(result['processes'][0]['checks'], [])
