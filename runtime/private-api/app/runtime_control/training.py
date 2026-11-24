"""Read-only, owner-scoped training aggregates. Never mutates trading state."""
from collections import Counter
from datetime import datetime, timezone, timedelta
from functools import lru_cache
import json
import math
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[4]

def stamp(value):
    try:
        d=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (ValueError,TypeError): return None

def number(value):
    if isinstance(value,bool): return None
    try:
        v=float(value)
        return v if math.isfinite(v) else None
    except (TypeError,ValueError): return None

def read_json(path):
    try:
        if path.stat().st_size>8*1024*1024: return None
        d=json.loads(path.read_text(encoding="utf-8"))
        return d if isinstance(d,dict) else None
    except (OSError,ValueError): return None

def tail_events(path):
    try:
        with path.open("rb") as f:
            size=f.seek(0,2); start=max(0,size-512*1024); f.seek(start)
            raw=f.read()
        lines=raw.splitlines()
        if start: lines=lines[1:]
        events=[]
        invalid=0
        for line in lines[-1000:]:
            try:
                event=json.loads(line)
                if isinstance(event,dict): events.append(event)
                else: invalid+=1
            except (ValueError,UnicodeDecodeError): invalid+=1
        return events, bool(start or len(lines)>1000), invalid
    except OSError: return None,False,0

@lru_cache(maxsize=1)
def helpers():
    # Load the monitor's canonical classification and weight formula without
    # importing its broker adapters or colliding with private-api's app package.
    return (runpy.run_path(str(ROOT/"app/strategy/universe.py")),
            runpy.run_path(str(ROOT/"app/intelligence/council_training.py")))

def rejection_category(reason):
    s=reason.lower()
    if "concentration" in s: return "CONCENTRATION"
    if "maximum open" in s or "already open" in s: return "OPEN_LIMIT"
    if "daily" in s and "entr" in s: return "DAILY_LIMIT"
    if "quote" in s or "price" in s and ("stale" in s or "unavailable" in s): return "QUOTES"
    if "confidence" in s and "risk" in s: return "OTHER"
    if "confidence" in s: return "CONFIDENCE"
    if "risk" in s or "loss" in s: return "RISK"
    if "council" in s or "decision gate" in s: return "COUNCIL"
    if "strategy setup" in s: return "NO_SETUP"
    return "OTHER"

def training_overview(root=None, now=None):
    root=Path(root or ROOT); now=now or datetime.now(timezone.utc)
    paper=root/".runtime/paper"
    result={"checked_at":now.isoformat(),"mode":"PAPER","portfolio":None,
            "selector":None,"agents":[],"asset_classes":[],
            "paper_trades":[],"training_sessions":[],"sklearn_review":None,
            "rejections":None,"unavailable":[],"comparison":"START_OF_CURRENT_UTC_DAY",
            "costs":"SPREAD_INCLUDED_FEES_EXCLUDED"}
    universe, trainer=helpers()
    ledger=read_json(paper/"atlas_demo_ledger.json")
    valid=[]; opened=[]; excluded=0; seen=set()
    if ledger and isinstance(ledger.get("closed_trades"),list) and isinstance(ledger.get("open_positions"),list):
        for closed,rows in ((True,ledger["closed_trades"]),(False,ledger["open_positions"])):
            for row in rows:
                if not isinstance(row,dict): excluded+=1; continue
                entry=stamp(row.get("opened_at")); end=stamp(row.get("closed_at")) if closed else None
                key=row.get("id")
                if not key or key in seen or not entry or entry>now or row.get("broker_execution_allowed",False) or (closed and (row.get("status")!="CLOSED" or not end or not entry<=end<=now or number(row.get("r_multiple")) is None)):
                    excluded+=1;continue
                seen.add(key)
                (valid if closed else opened).append(row)
        result["portfolio"]={"closed":len(valid),"open":len(opened),
            "entries_today_utc":sum(stamp(x["opened_at"]).date()==now.date() for x in valid+opened),
            "daily_ceiling":100,"sum_r":round(sum(number(x["r_multiple"]) for x in valid),4),
            "excluded_records":excluded}
        result["paper_trades"] = [
            {"id": str(row["id"])[:100], "symbol": str(row.get("symbol", ""))[:40],
             "status": "CLOSED" if closed else "OPEN",
             "opened_at": row["opened_at"], "closed_at": row.get("closed_at") if closed else None,
             "result_r": number(row.get("r_multiple")) if closed else None}
            for rows, closed in ((list(reversed(opened)), False), (list(reversed(valid)), True))
            for row in rows
        ]
        groups={}
        for row in valid+opened:
            info=universe["classify_symbol"](universe["normalize_symbol"](str(row.get("symbol",""))))
            category=info[0] if info else "OTHER"
            g=groups.setdefault(category,{"category":category,"closed":0,"open":0,"wins":0,"sum_r":0.0})
            if row.get("status")=="CLOSED":
                g["closed"]+=1; g["wins"]+=number(row["r_multiple"])>0; g["sum_r"]+=number(row["r_multiple"])
            else: g["open"]+=1
        result["asset_classes"]=[dict(g,sum_r=round(g["sum_r"],4),win_rate=round(g["wins"]/g["closed"],4) if g["closed"] else None) for _,g in sorted(groups.items())]
    else: result["unavailable"].append("ledger")
    shadow=read_json(paper/"atlas_shadow_report.json")
    if shadow and shadow.get("mode")=="SHADOW" and not shadow.get("broker_execution_allowed",False) and all(number(shadow.get(k)) is not None for k in ("samples","independent_days","minimum_samples","minimum_days")):
        result["selector"]={"samples":shadow["samples"],"minimum_samples":shadow["minimum_samples"],
            "days":shadow["independent_days"],"minimum_days":shadow["minimum_days"],
            "data_gates_met":shadow["samples"]>=shadow["minimum_samples"] and shadow["independent_days"]>=shadow["minimum_days"],
            "status":str(shadow.get("status","UNKNOWN"))[:64],"generated_at":shadow.get("generated_at")}
    else: result["unavailable"].append("selector")
    journal_path = paper / "atlas_council_training.jsonl"
    try:
        if journal_path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError("oversize")
        sessions = Counter()
        evidence = {}
        conflicts = set()
        for line in journal_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict) or row.get("execution_environment") != "PAPER" or row.get("broker_execution_allowed") is not False:
                continue
            when = stamp(row.get("timestamp"))
            snapshot = row.get("snapshot_id")
            if not isinstance(snapshot, str) or not snapshot.strip() or not when or when > now or row.get("realized_direction") not in ("BUY", "SELL", "HOLD"):
                continue
            day = when.date().isoformat()
            item = (day, row.get("realized_direction"))
            if evidence.setdefault(snapshot.strip(), item) != item:
                conflicts.add(snapshot.strip())
        sessions.update(day for key, (day, _) in evidence.items() if key not in conflicts)
        result["training_sessions"] = [{"date_utc": day, "settled_examples": count} for day, count in sorted(sessions.items(), reverse=True)]
    except (OSError, ValueError):
        result["unavailable"].append("training_sessions")

    report = read_json(paper / "council-agent-scores.json")
    if (report and report.get("training_environment") == "PAPER_RESEARCH_ONLY"
            and report.get("source_kind") == "SETTLED_PAPER_COUNCIL_JOURNAL"
            and all(report.get(key) is False for key in ("broker_execution_allowed", "active_council_weights_changed", "live_trading_enabled"))):
        result["sklearn_review"] = {"status": str(report.get("status", "UNKNOWN"))[:40],
                                    "generated_at": report.get("generated_at") if stamp(report.get("generated_at")) else None,
                                    "samples": number(report.get("unique_snapshots"))}
    else:
        result["unavailable"].append("sklearn_review")

    profile=read_json(paper/"atlas_council_profile.json")
    if profile and profile.get("training_environment")=="PAPER" and not profile.get("broker_execution_allowed",False) and isinstance(profile.get("agents"),dict):
        baseline={}; journal_path=paper/"atlas_council_training.jsonl"
        try:
            if journal_path.stat().st_size>8*1024*1024: raise ValueError("oversize")
            examples=[]; snapshots=set()
            for line in journal_path.read_text(encoding="utf-8").splitlines():
                d=json.loads(line); t=stamp(d.get("timestamp"))
                if t and t<now.replace(hour=0,minute=0,second=0,microsecond=0) and d.get("snapshot_id") not in snapshots:
                    examples.append(trainer["PaperTrainingExample"].from_dict(d));snapshots.add(d["snapshot_id"])
            # No historical baseline is invented when there are no earlier examples.
            if examples: baseline=trainer["AtlasCouncilTrainer"]().fit(examples)["agents"]
        except (OSError,ValueError,TypeError,KeyError): result["unavailable"].append("weight_history")
        for name,row in sorted(profile["agents"].items()):
            if not isinstance(row,dict): continue
            w=number(row.get("weight")); b=number(row.get("brier_score"))
            if w is None or not 0.5<=w<=1.5 or b is None or not 0<=b<=1: continue
            old=baseline.get(name,{}).get("weight")
            result["agents"].append({"agent":str(name)[:80],"weight":w,
                "weight_change":round(w-old,4) if old is not None else None,
                "samples":number(row.get("samples")),"brier_score":b})
        result["profile_generated_at"]=profile.get("generated_at")
    else: result["unavailable"].append("profile")
    events,truncated,invalid=tail_events(root/"data/atlas_signals.jsonl")
    if events is not None:
        recent=[x for x in events if (t:=stamp(x.get("timestamp"))) and now-timedelta(hours=24)<=t<=now]
        rejected=[x for x in recent if x.get("status") in {"NO_TRADE","SKIPPED","MT5_ERROR","RISK_REJECTED","REJECTED"}]
        c=Counter(rejection_category(str(x.get("reason",""))) for x in rejected)
        times=[stamp(x.get("timestamp")) for x in recent]
        result["rejections"]={"total":len(rejected),"counts":[{"category":k,"count":v} for k,v in c.most_common()],
            "events_sampled":len(recent),"truncated":truncated,"invalid_lines":invalid,
            "from":min(times).isoformat() if times else None,"through":max(times).isoformat() if times else None,
            "stale":not times or (now-max(times)).total_seconds()>180}
    else: result["unavailable"].append("rejections")
    return result
