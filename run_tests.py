"""Run this project's own tests, independent of the caller's current directory."""
from pathlib import Path
import sys,unittest
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root))
suite=unittest.defaultTestLoader.discover(str(root/'tests'),pattern='test_*.py')
if suite.countTestCases()==0:raise SystemExit('No project tests discovered')
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
