import sys
import pytest

@pytest.mark.skipif(sys._is_gil_enabled(), reason="Illustrative runtime-state guard")
def test_gil_disabled():
    assert not sys._is_gil_enabled()
