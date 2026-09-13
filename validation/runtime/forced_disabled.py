import sys
import legacy_fixture
assert not sys._is_gil_enabled()
print("CHECKPOINT", sys._is_gil_enabled())
