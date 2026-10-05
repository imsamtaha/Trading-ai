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

def test_running_unhealthy_web_tasks_are_restarted_after_threshold(tmp_path, monkeypatch):
    import json
    calls = []
    monkeypatch.setattr(module, "http_health", lambda url: False)
    monkeypatch.setattr(module, "check_mt5", lambda: {"state": "OBSERVED"})
    monkeypatch.setattr(module.time, "time", lambda: 100)

    def task_operation(command):
        calls.append(command)
        return "Running"

    monkeypatch.setattr(module, "powershell", task_operation)
    for _ in range(2):
        assert module.check_cycle(tmp_path)["actions"] == []
    status = module.check_cycle(tmp_path)
    assert status["actions"] == ["RESTARTED ATLAS Private Backend", "RESTARTED ATLAS Web Frontend"]
    assert status["components"]["backend"]["state"] == "RECOVERING"
    restart_commands = [command for command in calls if "Stop-ScheduledTask" in command]
    assert len(restart_commands) == 2
    assert all("Start-ScheduledTask" in command and "AddSeconds(10)" in command for command in restart_commands)
    assert all("Council" not in command and "MT5" not in command for command in calls)
    assert json.loads((tmp_path / "status.json").read_text())["actions"] == status["actions"]

def test_restart_failure_is_reported_without_success_action(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "http_health", lambda url: False)
    monkeypatch.setattr(module, "check_mt5", lambda: {"state": "OBSERVED"})
    monkeypatch.setattr(module.time, "time", lambda: 100)

    def fail_restart(command):
        if "Stop-ScheduledTask" in command:
            raise RuntimeError("failed")
        return "Running"

    monkeypatch.setattr(module, "powershell", fail_restart)
    for _ in range(3):
        status = module.check_cycle(tmp_path)
    assert status["actions"] == []
    assert status["components"]["backend"]["state"] == "TASK_OPERATION_FAILED"

def test_restart_budget_prevents_endless_recovery(tmp_path, monkeypatch):
    import json
    (tmp_path / "recovery-state.json").write_text(json.dumps({
        name: {"failures": 10, "attempts": 5, "restarts": 5, "next": 0}
        for name in ("backend", "frontend")
    }))
    calls = []
    monkeypatch.setattr(module, "http_health", lambda url: False)
    monkeypatch.setattr(module, "check_mt5", lambda: {"state": "OBSERVED"})
    monkeypatch.setattr(module, "powershell", lambda command: calls.append(command) or "Running")
    status = module.check_cycle(tmp_path)
    assert status["actions"] == []
    assert status["components"]["backend"]["state"] == "RECOVERY_EXHAUSTED"
    assert not any("Stop-ScheduledTask" in command for command in calls)

def test_legacy_probe_attempts_do_not_spend_restart_budget(tmp_path, monkeypatch):
    import json
    (tmp_path / "recovery-state.json").write_text(json.dumps({
        "backend": {"failures": 200, "attempts": 20, "next": 0}
    }))
    monkeypatch.setattr(module, "http_health", lambda url: False)
    monkeypatch.setattr(module, "check_mt5", lambda: {"state": "OBSERVED"})
    monkeypatch.setattr(module, "powershell", lambda command: "Running")
    status = module.check_cycle(tmp_path)
    assert "RESTARTED ATLAS Private Backend" in status["actions"]
    state = json.loads((tmp_path / "recovery-state.json").read_text())
    assert state["backend"]["restarts"] == 1

