import sys
assert not sys._is_gil_enabled()
__import__("legacy_fixture")
print("CHECKPOINT", sys._is_gil_enabled())
