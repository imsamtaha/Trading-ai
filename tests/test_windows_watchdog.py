import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("watchdog", Path(__file__).parents[1] / "scripts" / "atlas_windows_watchdog.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_waits_for_three_failures():
    gate = module.FailureGate()
    assert not gate.observe(False, 0)
    assert not gate.observe(False, 30)
    assert gate.observe(False, 60)

def test_backoff_prevents_restart_storm():
    gate = module.FailureGate()
    for now in (0, 1): gate.observe(False, now)
    assert gate.observe(False, 2)
    assert not gate.observe(False, 3)
    assert gate.observe(False, 32)
    assert not gate.observe(False, 91)
    assert gate.observe(False, 92)
    assert not gate.observe(False, 211)
    assert gate.observe(False, 212)
    assert not gate.observe(False, 511)
    assert gate.observe(False, 512)

def test_healthy_probe_resets_failure_streak():
    gate = module.FailureGate()
    gate.observe(False, 0)
    gate.observe(False, 1)
    gate.observe(True, 2)
    assert not gate.observe(False, 3)
    assert not gate.observe(False, 4)
    assert gate.observe(False, 5)

def test_recovery_resets_backoff():
    gate = module.FailureGate()
    for now in (0, 1, 2, 32): gate.observe(False, now)
    gate.observe(True, 33)
    for now in (34, 35): gate.observe(False, now)
    assert gate.observe(False, 36)
    assert gate.observe(False, 66)

def test_state_survives_process_restart():
    gate = module.FailureGate()
    for now in (0, 1, 2): gate.observe(False, now)
    restored = module.FailureGate(gate.state)
    assert not restored.observe(False, 3)
    assert restored.observe(False, 32)

