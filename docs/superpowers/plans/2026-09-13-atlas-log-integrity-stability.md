# ATLAS Log Integrity Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the local ATLAS JSONL signal journal durable and detect malformed or incomplete records before they are trusted as operational evidence.

**Architecture:** Keep the existing append-only JSONL format. Add a focused `verify()` reader on `SignalJournal` that validates every non-empty line as a JSON object and reports valid/malformed counts and exact malformed line numbers; make append durability explicit with flush and fsync before returning.

**Tech Stack:** Python 3.13, pathlib, json, pytest

**Spec:** User request on 2026-09-13 to inspect ATLAS, prioritize stability, improve it, and verify its logs.

## Global Constraints

- Keep ATLAS in paper-demo mode; do not enable broker order submission.
- Do not expose credentials or account secrets.
- Preserve the existing JSONL record format and `append(record) -> dict` contract.
- Make the smallest root-cause fix and run the entire existing test suite.

---

### Task 1: Durable and verifiable signal journal

**Files:**
- Modify: `app/intelligence/journal.py`
- Modify: `tests/test_intelligence_pipeline.py`

**Interfaces:**
- Consumes: Existing `SignalJournal(path=None)` and `append(record) -> dict`.
- Produces: `verify() -> dict[str, object]` with `status`, `records`, `malformed_records`, and `malformed_lines`.

- [ ] **Step 1: Write the failing tests**

Add tests using a real temporary JSONL file:

```python
def test_signal_journal_verify_reports_malformed_line(tmp_path):
    path = tmp_path / "signals.jsonl"
    path.write_text('{"status":"NO_TRADE"}\n{"status":\n{"status":"ERROR"}\n', encoding="utf-8")
    report = SignalJournal(str(path)).verify()
    assert report == {
        "status": "CORRUPT",
        "records": 2,
        "malformed_records": 1,
        "malformed_lines": [2],
    }


def test_signal_journal_verify_accepts_appended_records(tmp_path):
    journal = SignalJournal(str(tmp_path / "signals.jsonl"))
    journal.append({"symbol": "EURUSD", "status": "NO_TRADE"})
    assert journal.verify() == {
        "status": "OK",
        "records": 1,
        "malformed_records": 0,
        "malformed_lines": [],
    }
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run: `python -m pytest tests/test_intelligence_pipeline.py -q`

Expected: FAIL because `SignalJournal.verify` does not exist.

- [ ] **Step 3: Implement the minimal durable append and verifier**

In `append`, write one JSON line, call `handle.flush()`, then `os.fsync(handle.fileno())`.

Implement `verify` by reading each non-empty line, parsing JSON, accepting only JSON objects, and returning the literal report shape defined by the tests.

- [ ] **Step 4: Run focused and full verification**

Run: `python -m pytest tests/test_intelligence_pipeline.py -q`

Run: `python -m pytest -q`

Expected: all tests pass with no failures.

- [ ] **Step 5: Open a pull request**

Commit the test and implementation on `atlas/log-integrity-stability`, allow GitHub Actions to run, inspect the workflow log, and merge only after success.
