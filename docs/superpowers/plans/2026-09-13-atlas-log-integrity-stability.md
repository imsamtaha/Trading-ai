# ATLAS Log Integrity Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the local ATLAS JSONL signal journal durable, detect syntactically malformed or non-object records, and expose the verification through the existing demo-status command.

**Architecture:** Preserve the append-only JSONL format. Synchronize every append before returning, verify the file in binary mode so torn UTF-8 writes are reportable, and include the structured result in `scripts/atlas_demo_status.py` with a nonzero corruption exit code.

**Tech Stack:** Python 3.13, pathlib, json, pytest, GitHub Actions on Ubuntu and Windows

**Spec:** User request on 2026-09-13 to inspect ATLAS, rank three priorities, execute the first available stability improvement, and verify logs.

## Global Constraints

- Keep ATLAS in paper-demo mode; do not enable broker order submission.
- Do not expose credentials or account secrets.
- Preserve the existing JSONL representation and `append(record) -> dict` contract.
- Use TDD and inspect the complete CI logs before merge.

## Ranked Priorities

1. **Local audit durability and integrity verification.** A journal append returned without an explicit disk synchronization, malformed lines were counted but not validated, and no operational status command checked the journal.
2. **Single-writer and crash-continuity enforcement.** The demo session has a socket lock, but alternate monitor entrypoints can still target the same ledger and journal without a shared file-level writer guard.
3. **Observable remote audit and heartbeat failures.** Supabase publication failures can return `None` silently, so local operators cannot distinguish a healthy remote audit stream from an unavailable one.

Priority 1 is first because it is independently available in the repository, does not require MT5 or credentials, and protects the evidence used to judge demo performance.

---

### Task 1: Durable and verifiable signal journal

**Files:**
- Modify: `app/intelligence/journal.py`
- Create: `tests/test_signal_journal_integrity.py`

**Interfaces:**
- Consumes: `SignalJournal(path=None)` and `append(record) -> dict`.
- Produces: `verify() -> dict[str, object]` with `status`, `records`, `malformed_records`, and `malformed_lines`.

- [x] **Step 1: Write failing tests**

Tests cover malformed JSON, invalid UTF-8, non-object JSON values, valid appended records, and write/flush/fsync ordering.

- [x] **Step 2: Confirm RED**

Run: `python -m pytest tests/test_signal_journal_integrity.py -q`

Observed through PR CI: missing `verify()`, missing `fsync`, and invalid UTF-8 handling failed for the intended reasons while the pre-existing tests passed.

- [x] **Step 3: Implement the minimal journal fix**

`append()` now writes one line, flushes it, and calls `os.fsync(handle.fileno())`. `verify()` reads binary physical lines, strictly decodes UTF-8, accepts only JSON objects, and reports exact malformed line numbers.

- [x] **Step 4: Expose verification operationally**

**Files:**
- Modify: `scripts/atlas_demo_status.py`
- Modify: `tests/test_mt5_monitor_recovery.py`

The existing status command includes `signal_journal` with path, existence, integrity counts, and line numbers. It exits `3` when the journal is corrupt, `2` when only the ledger is missing, and `0` when available records are structurally valid.

- [x] **Step 5: Verify Linux, Windows, and public demo checks**

**Files:**
- Modify: `.github/workflows/tests.yml`

Run on Ubuntu: `python -m pytest -q`

Run on Windows: `python -m pytest tests/test_signal_journal_integrity.py -q`

Observed at commit `15d88eb4419836338fa34a301371894163bc69d0`: Ubuntu `213 passed`; Windows `9 passed`; public website validation passed. One upstream GitHub Actions Node 20 deprecation warning remains and is unrelated to ATLAS runtime behavior.

- [ ] **Step 6: Verify the live Windows journal before operational sign-off**

Run on the Windows MT5 host from the repository directory:

```powershell
.\.venv\Scripts\python.exe .\scripts\atlas_demo_status.py
```

Accept exit `0` with `signal_journal.status` equal to `OK`. Exit `3` or `CORRUPT` requires preserving the file for investigation before restarting the worker.
