import sys
assert not sys._is_gil_enabled()
import native_extension
run_tests()
