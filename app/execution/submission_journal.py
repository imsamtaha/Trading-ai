"""Durable delivery reservations. An uncertain result must never become a retry.

All local ATLAS processes must use the same database path. Reservations commit
before order_send, so a crash after delivery also leaves the account blocked.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import time
from datetime import datetime, time as day_time, timedelta
from zoneinfo import ZoneInfo
from uuid import uuid4


class SubmissionJournalError(RuntimeError):
    pass


class UnresolvedSubmission(SubmissionJournalError):
    pass


class SubmissionJournal:
    def __init__(self):
        self.path = Path(os.getenv('ATLAS_MT5_SUBMISSION_DB',
                                  str(Path.home() / '.atlas' / 'mt5-submissions.sqlite3')))

    @contextmanager
    def _connection(self):
        connection = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path, timeout=5)
            connection.row_factory = sqlite3.Row
            connection.execute('PRAGMA synchronous=FULL')
            connection.execute('''CREATE TABLE IF NOT EXISTS submissions (
                id TEXT PRIMARY KEY, account TEXT NOT NULL, symbol TEXT NOT NULL,
                requested_volume REAL NOT NULL, created_at REAL NOT NULL,
                state TEXT NOT NULL, request TEXT NOT NULL, detail TEXT,
                ticket INTEGER, deal INTEGER, position_identifier INTEGER)''')
            connection.execute('''CREATE UNIQUE INDEX IF NOT EXISTS unresolved_account
                ON submissions(account) WHERE state IN ('SUBMITTING', 'UNCERTAIN')''')
            connection.commit()
            yield connection
        except (OSError, sqlite3.Error) as exc:
            raise SubmissionJournalError('Submission journal unavailable; execution refused.') from exc
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def account_key(account):
        return json.dumps(account, sort_keys=True, separators=(',', ':'))

    def begin(self, account, request, *, position_identifier=None, max_daily_entries=None):
        identifier = uuid4().hex[:24]
        request = {**request, 'comment': 'ATLAS-' + identifier}
        with self._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            key = self.account_key(account)
            if connection.execute("SELECT 1 FROM submissions WHERE account=? AND state IN ('SUBMITTING','UNCERTAIN')",
                                  (key,)).fetchone():
                raise UnresolvedSubmission('Unresolved MT5 submission; reconcile before further execution.')
            if max_daily_entries is not None and 'position' not in request:
                if type(max_daily_entries) is not int or max_daily_entries <= 0:
                    raise SubmissionJournalError('Invalid daily demo entry limit.')
                zone = ZoneInfo('Asia/Beirut')
                today = datetime.now(zone).date()
                start = datetime.combine(today, day_time.min, zone).timestamp()
                end = datetime.combine(today + timedelta(days=1), day_time.min, zone).timestamp()
                rows = connection.execute(
                    "SELECT request FROM submissions WHERE account=? AND created_at>=? AND created_at<? AND state IN ('FILLED','SUBMITTING','UNCERTAIN')",
                    (key, start, end)).fetchall()
                entries = sum('position' not in json.loads(row['request']) for row in rows)
                if entries >= max_daily_entries:
                    raise SubmissionJournalError('Maximum daily demo entries reached.')
            connection.execute('INSERT INTO submissions(id,account,symbol,requested_volume,created_at,state,request,position_identifier) VALUES(?,?,?,?,?,?,?,?)',
                               (identifier, key, request['symbol'], request['volume'], time.time(),
                                'SUBMITTING', json.dumps(request, allow_nan=False), position_identifier))
            connection.commit()
        return identifier, request

    def finish(self, identifier, state, *, ticket=None, deal=None, detail=None):
        if state not in {'FILLED', 'UNCERTAIN'}:
            raise ValueError('Unsupported delivery state')
        with self._connection() as connection:
            cursor = connection.execute('UPDATE submissions SET state=?,ticket=?,deal=?,detail=? WHERE id=?',
                                        (state, ticket, deal, detail, identifier))
            if cursor.rowcount != 1:
                raise SubmissionJournalError('Submission reservation missing; execution refused.')
            connection.commit()

    def cancel_before_send(self, identifier):
        # Preserve an audit record rather than deleting the reservation.
        with self._connection() as connection:
            cursor = connection.execute("UPDATE submissions SET state='NOT_SENT' WHERE id=? AND state='SUBMITTING'",
                                        (identifier,))
            if cursor.rowcount != 1:
                raise SubmissionJournalError('Submission reservation missing; execution refused.')
            connection.commit()

    def status(self, account):
        with self._connection() as connection:
            rows = connection.execute('SELECT * FROM submissions WHERE account=? ORDER BY created_at DESC',
                                      (self.account_key(account),)).fetchall()
        attempts = [{**dict(row), 'request': json.loads(row['request'])} for row in rows]
        return {'blocked': any(row['state'] in {'SUBMITTING', 'UNCERTAIN'} for row in attempts),
                'attempts': attempts}
