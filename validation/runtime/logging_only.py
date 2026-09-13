import sys
import legacy_fixture
print("LOG", sys._is_gil_enabled())
print("CHECKPOINT", sys._is_gil_enabled())
