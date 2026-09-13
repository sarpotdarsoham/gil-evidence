import sys
import legacy_fixture
if sys._is_gil_enabled():
    raise RuntimeError("GIL enabled")
print("CHECKPOINT", sys._is_gil_enabled())
