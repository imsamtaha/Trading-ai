"""Owner-recorded interaction outcomes. No generated rows or customer text."""
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager
import json
import math
from pathlib import Path
import re
import sqlite3

FEATURES=("agent_experience_months","avg_handle_time_mins","historical_csat","total_chats_handled","current_workload")
FIELDS=set(FEATURES)|{"interaction_id","agent_id","sale_success","csat_outcome","feature_snapshot_at","occurred_at","confirmed_observed"}

def normalized_outcome(data):
    if not isinstance(data,dict) or set(data)!=FIELDS or data["confirmed_observed"] is not True:
        raise ValueError("OBSERVED_CONFIRMATION_REQUIRED")
    row=dict(data)
    for key in ("interaction_id","agent_id"):
        if not isinstance(row[key],str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}",row[key]):
            raise ValueError("INVALID_IDENTIFIER")
    for key in FEATURES+("csat_outcome",):
        value=row[key]
        if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=1e12:
            raise ValueError("INVALID_FEATURES")
    if row["avg_handle_time_mins"]<=0 or not 1<=row["historical_csat"]<=5 or not 1<=row["csat_outcome"]<=5:
        raise ValueError("INVALID_CSAT_OR_HANDLE_TIME")
    if any(row[key]!=int(row[key]) for key in ("agent_experience_months","total_chats_handled","current_workload")):
        raise ValueError("INVALID_COUNT")
    if type(row["sale_success"]) is not int or row["sale_success"] not in (0,1):
        raise ValueError("INVALID_SALE_OUTCOME")
    dates=[]
    for key in ("feature_snapshot_at","occurred_at"):
        try:
            stamp=datetime.fromisoformat(row[key].replace("Z","+00:00"))
            if stamp.tzinfo is None:raise ValueError()
            stamp=stamp.astimezone(timezone.utc)
        except (ValueError,TypeError,AttributeError) as exc:
            raise ValueError("TIMEZONE_REQUIRED") from exc
        dates.append(stamp)
        row[key]=stamp.isoformat()
    if dates[0]>=dates[1] or dates[1]>datetime.now(timezone.utc)+timedelta(minutes=2):
        raise ValueError("FEATURES_MUST_PRECEDE_OUTCOME")
    return row


class OutcomeStore:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            schema="(interaction_id TEXT PRIMARY KEY, occurred_at TEXT NOT NULL, sale_success INTEGER NOT NULL, recorded_at TEXT NOT NULL, payload TEXT NOT NULL)"
            db.execute("CREATE TABLE IF NOT EXISTS outcomes "+schema)
            # Preserve early intake records while removing timestamp uniqueness.
            # Distinct interactions can legitimately finish at the same instant.
            for index in db.execute("PRAGMA index_list(outcomes)").fetchall():
                name=index['name'].replace('"','""')
                columns=[row['name'] for row in db.execute('PRAGMA index_info("'+name+'")')]
                if index['unique'] and columns==['occurred_at']:
                    db.execute("CREATE TABLE outcomes_migrated "+schema)
                    db.execute("INSERT INTO outcomes_migrated SELECT * FROM outcomes")
                    db.execute("DROP TABLE outcomes")
                    db.execute("ALTER TABLE outcomes_migrated RENAME TO outcomes")
                    break

    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=5)
        db.row_factory=sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def record(self,data):
        row=normalized_outcome(data)
        payload=json.dumps(row,sort_keys=True,allow_nan=False)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            prior=db.execute("SELECT payload FROM outcomes WHERE interaction_id=?",(row["interaction_id"],)).fetchone()
            if prior:
                if prior["payload"]!=payload:raise ValueError("INTERACTION_CONFLICT")
            else:
                if db.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]>=10000:
                    raise ValueError("DATASET_LIMIT_REACHED")
                db.execute("INSERT INTO outcomes VALUES (?,?,?,?,?)",(row["interaction_id"],row["occurred_at"],row["sale_success"],datetime.now(timezone.utc).isoformat(),payload))
        return self.summary()

    def rows(self):
        with self._connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT payload FROM outcomes ORDER BY occurred_at,interaction_id")]

    def summary(self):
        with self._connect() as db:
            row=db.execute("SELECT COUNT(*) AS rows,COALESCE(SUM(sale_success),0) AS positive,MAX(recorded_at) AS latest FROM outcomes").fetchone()
        return {"source":"owner_recorded","rows":row["rows"],"sales_positive":row["positive"],"sales_negative":row["rows"]-row["positive"],"minimum_rows":50,"last_recorded_at":row["latest"],"max_rows":10000}
