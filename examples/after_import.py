import sys
import native_extension
assert not sys._is_gil_enabled()
run_tests()
