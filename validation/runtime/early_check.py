import sys
assert not sys._is_gil_enabled()
import legacy_fixture
print("CHECKPOINT", sys._is_gil_enabled())
