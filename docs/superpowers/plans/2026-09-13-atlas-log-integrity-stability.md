# ATLAS Log Integrity Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the local ATLAS JSONL signal journal durable, enforce strict JSON records, and expose verification through the existing demo-status command.

**Architecture:** Preserve the append-only JSONL format. Validate a record before opening the file, synchronize every successful append before returning, verify existing data in binary mode so torn UTF-8 writes are reportable, and include the result in `scripts/atlas_demo_status.py` with distinct nonzero exit codes for corrupt and missing journals.

**Tech Stack:** Python 3.13, pathlib, json, pytest, GitHub Actions on Ubuntu and Windows

**Spec:** User request on 2026-09-13 to inspect ATLAS, rank three priorities, execute the first available stability improvement, and verify logs.

## Global Constraints

- Keep ATLAS in paper-demo mode; do not enable broker order submission.
- Do not expose credentials or account secrets.
- Preserve the existing JSONL representation and `append(record) -> dict` contract.
- Use TDD and inspect the complete CI logs before merge.

## Ranked Priorities

1. **Local audit durability and integrity verification.** A journal append returned without explicit disk synchronization, malformed lines were counted but not validated, and no operational status command checked journal integrity.
2. **Single-writer and crash-continuity enforcement.** The demo session has a socket lock, but alternate monitor entrypoints can still target the same ledger and journal without a shared file-level writer guard.
3. **Observable remote audit and heartbeat failures.** Supabase publication failures can return `None` silently, so local operators cannot distinguish a healthy remote audit stream from an unavailable one.

Priority 1 is first because it is independently available in the repository, does not require MT5 or credentials, and protects the evidence used to judge demo performance.

---

### Task 1: Durable and verifiable signal journal

**Files:**
- Modify: `app/intelligence/journal.py`
- Create: `tests/test_signal_journal_integrity.py`
- Modify: `scripts/atlas_demo_status.py`
- Create: `tests/test_atlas_demo_status_integrity.py`
- Modify: `.github/workflows/tests.yml`

**Interfaces:**
- `SignalJournal.append(record) -> dict` rejects non-finite numbers before creating a record, then performs write, flush, and fsync.
- `SignalJournal.verify() -> dict[str, object]` returns `OK`, `CORRUPT`, or `MISSING` plus valid/malformed counts and exact malformed physical line numbers.
- `scripts/atlas_demo_status.py` exits `0` for a valid existing journal, `2` for a missing ledger, `3` for a corrupt journal, and `4` for a missing journal when the ledger exists.

- [x] **Step 1: Write failing tests**

Tests cover malformed JSON, torn UTF-8, non-object JSON, `NaN`/`Infinity`/`-Infinity`, missing journals, read-only construction, valid records, and write/flush/fsync ordering.

- [x] **Step 2: Confirm RED**

Run: `python -m pytest tests/test_signal_journal_integrity.py tests/test_atlas_demo_status_integrity.py -q`

Observed through PR CI: tests failed for missing strict parsing, missing status handling, constructor side effects, missing `verify()`, and missing `fsync`, while unrelated pre-existing tests passed.

- [x] **Step 3: Implement the minimal journal fix**

Serialization uses `allow_nan=False` before the journal is opened. Parsing uses a rejecting `parse_constant` callback. Verification reads binary physical lines, strictly decodes UTF-8, accepts only JSON objects, and never creates parent directories. Successful append creates the parent directory, writes one record, flushes, and synchronizes it.

- [x] **Step 4: Expose verification operationally**

The existing demo-status command includes `signal_journal` with path, existence, status, counts, and malformed line numbers. Missing and corrupt journals produce distinct nonzero exit codes without touching MT5 execution.

- [x] **Step 5: Verify Linux, Windows, and public demo checks**

Run on Ubuntu: `python -m pytest -q`

Run on Windows: `python -m pytest tests/test_signal_journal_integrity.py tests/test_atlas_demo_status_integrity.py -q`

Observed at commit `7b715fbfecedb246cc9eb3dad4b0742ab51d848d`: Ubuntu `219 passed`; Windows `16 passed`; public website validation passed. One upstream GitHub Actions Node 20 deprecation warning remains and is unrelated to ATLAS runtime behavior.

- [ ] **Step 6: Verify the live Windows journal before operational sign-off**

Run on the Windows MT5 host from the repository directory:

```powershell
.\.venv\Scripts\python.exe .\scripts\atlas_demo_status.py
```

Accept only exit `0` with `signal_journal.exists` equal to `true` and `signal_journal.status` equal to `OK`. Exit `3` or `CORRUPT` requires preserving the file for investigation before restarting the worker. Exit `4` or `MISSING` means no audit journal exists and is not an operational pass.
