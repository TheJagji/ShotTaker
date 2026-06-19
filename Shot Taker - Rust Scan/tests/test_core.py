"""
ShotTaker — unit tests for pure logic. Runs under pytest or directly:
    python tests/test_core.py
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
config.ensure_dirs()
import frames
import gamenames
import scanner
import capture_manager as cap


def test_config_deep_merge():
    merged = config._deep_merge({"a": 1, "b": {"x": 1, "y": 2}}, {"b": {"y": 9}, "c": 3})
    assert merged == {"a": 1, "b": {"x": 1, "y": 9}, "c": 3}


def test_settings_defaults_present():
    s = config.load_settings()
    for key in ("capture_mode", "interval", "dedupe_enabled", "achievement_burst"):
        assert key in s


def test_gamenames_prettify():
    assert gamenames.prettify("PathOfExile_x64.exe") == "Path Of Exile"
    assert gamenames.prettify("eldenring.exe") == "Eldenring"
    assert gamenames.prettify("Witcher3_Win64_Shipping.exe").startswith("Witcher3")


def test_scanner_skip_patterns():
    assert any(p in "unitycrashhandler64.exe" for p in scanner.SKIP_PATTERNS)
    assert any(p in "vcredist_x64.exe" for p in scanner.SKIP_PATTERNS)
    assert not any(p in "hades.exe" for p in scanner.SKIP_PATTERNS)


def test_counter_case_normalised():
    cap.reset_counters("CaseTestGame")
    a = cap.next_counter("CaseTestGame", "TimeLapse")
    b = cap.next_counter("casetestgame", "TimeLapse")  # different case
    assert b == a + 1, "counters must share a case-insensitive key"
    cap.reset_counters("CaseTestGame")


def test_score_diff_and_gate():
    a = np.zeros((180, 320, 3), dtype=np.uint8)
    b = np.zeros((180, 320, 3), dtype=np.uint8)
    assert frames.score_diff(a, b) == 0.0
    b[:] = 255
    assert frames.score_diff(a, b) > 100

    dark = np.full((180, 320, 3), 3, dtype=np.uint8)
    settings = config.DEFAULTS
    assert frames.quality_reject(dark, settings) == "dark"

    bright_flat = np.full((180, 320, 3), 200, dtype=np.uint8)
    assert frames.quality_reject(bright_flat, settings) == "low-detail"


def test_letterbox_detection():
    img = np.random.randint(40, 255, (180, 320, 3), dtype=np.uint8)
    img[:30] = 0
    img[-30:] = 0
    assert frames.is_letterboxed(img) is True


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:
            print(f"ERROR {fn.__name__}: {e}")
    print(f"\n{passed}/{len(fns)} tests passed")
    return passed == len(fns)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
