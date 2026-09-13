import sys
import native_extension
if sys._is_gil_enabled():
    raise RuntimeError('Expected GIL disabled')
run_tests()
