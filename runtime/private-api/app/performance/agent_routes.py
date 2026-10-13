"""Owner-only advisory scoring. ML dependencies load on demand; health stays cheap."""
import os
import hmac
from datetime import datetime
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from app.runtime_control.routes import _require_owner

router = APIRouter(prefix="/api/runtime/agent-performance", tags=["agent-performance"])
_lock = threading.Lock()
_cached = None
_fingerprint = None
_training_lock = threading.Lock()


def _confirmed(value):
    if value is not True:
        raise ValueError("OBSERVED_CONFIRMATION_REQUIRED")
    return value


ConfirmedObserved = Annotated[Literal[True], BeforeValidator(_confirmed)]


def _authorize(request):
    supplied=request.headers.get("X-Atlas-Model-Bridge", "")
    if supplied:
        path=Path(os.getenv("ATLAS_AGENT_BRIDGE_TOKEN_FILE",str(Path.home()/"AppData/Local/ATLASDashboardBridge/bridge-token.txt")))
        try:
            token=path.read_text().strip()
        except OSError:
            token=""
        if len(token)>=40 and hmac.compare_digest(supplied.encode(),token.encode()):
            return
        raise HTTPException(status_code=401,detail="Invalid model bridge credential")
    _require_owner(request)


def _store():
    from app.performance.outcomes import OutcomeStore
    root=Path(__file__).resolve().parents[4]
    return OutcomeStore(os.getenv("ATLAS_AGENT_OUTCOMES_DB",str(root/".runtime/agent_performance_outcomes.sqlite3")))


class AgentFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    agent_id: str = Field(min_length=1, max_length=100)
    agent_experience_months: int = Field(ge=0)
    avg_handle_time_mins: float = Field(gt=0)
    historical_csat: float = Field(ge=1, le=5)
    total_chats_handled: int = Field(ge=0)
    current_workload: int = Field(ge=0)


class ScorePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    agents: list[AgentFeatures] = Field(min_length=1, max_length=100)
    w_sales: float = Field(default=.6, ge=0, le=1)
    w_csat: float = Field(default=.4, ge=0, le=1)
    allow_synthetic: bool = False


class OutcomePayload(AgentFeatures):
    interaction_id: str = Field(min_length=1,max_length=100)
    sale_success: int = Field(ge=0,le=1,strict=True)
    csat_outcome: float = Field(ge=1,le=5)
    feature_snapshot_at: datetime
    occurred_at: datetime
    confirmed_observed: ConfirmedObserved


class TrainPayload(BaseModel):
    model_config=ConfigDict(extra="forbid")
    confirmed_observed: ConfirmedObserved


def _load():
    global _cached, _fingerprint
    default = Path(__file__).resolve().parents[4] / ".runtime" / "models" / "agent_performance"
    prefix = Path(os.getenv("ATLAS_AGENT_PERFORMANCE_MODEL", str(default)))
    if not Path(str(prefix) + ".bundle.zip").exists():
        prefix = Path(str(prefix) + "_demo")
    path = Path(str(prefix) + ".bundle.zip")
    with _lock:
        try:
            stat = path.stat()
            fingerprint = (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
            if fingerprint != _fingerprint:
                from app.performance.agent_xgb import AgentPerformanceXGBoost
                replacement = AgentPerformanceXGBoost.load_models(prefix)
                _cached, _fingerprint = replacement, fingerprint
            return _cached, None
        except FileNotFoundError:
            # Do not serve a different path's model after a configuration change.
            if _fingerprint and _fingerprint[0] == str(path.resolve()):
                return _cached, "MODEL_FILE_UNAVAILABLE"
            return None, "UNTRAINED"
        except Exception:
            if _fingerprint and _fingerprint[0] == str(path.resolve()):
                return _cached, "MODEL_RELOAD_FAILED"
            return None, "MODEL_UNAVAILABLE"


def _status(model, error):
    meta = dict(model.metadata) if model else None
    try:
        dataset=_store().summary()
    except (OSError,sqlite3.Error):
        dataset={"source":"owner_recorded","rows":None,"minimum_rows":50,"error":"STORAGE_UNAVAILABLE"}
    return {"status": "DEGRADED" if model and error else
            "DEMO_READY" if model and meta["source"] == "synthetic" else
            "ADVISORY_READY" if model else error,
            "error": error, "metadata": meta, "dataset":dataset,"production_ready": False,
            "changes_trading_weights": False, "broker_execution_allowed": False}


@router.get("/status")
def status(request: Request):
    _authorize(request)
    model, error = _load()
    return JSONResponse(_status(model, error), headers={"Cache-Control": "private, no-store"})


@router.post("/scores")
def scores(payload: ScorePayload, request: Request):
    _authorize(request)
    model, error = _load()
    if model is None:
        raise HTTPException(status_code=503, detail=error)
    if model.metadata["source"] == "synthetic" and not payload.allow_synthetic:
        raise HTTPException(status_code=409, detail="Synthetic model requires allow_synthetic=true")
    ids = [agent.agent_id for agent in payload.agents]
    if len(set(ids)) != len(ids):
        raise HTTPException(status_code=422, detail="Agent IDs must be unique")
    import pandas as pd
    X = pd.DataFrame([row.model_dump(exclude={"agent_id"}) for row in payload.agents])
    try:
        composite, sales, csat = model.predict_composite_score(X, payload.w_sales, payload.w_csat)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    rows = [{"agent_id": key, "composite_score": float(score),
             "sales_probability": float(probability), "predicted_csat": float(satisfaction)}
            for key, score, probability, satisfaction in zip(ids, composite, sales, csat)]
    rows.sort(key=lambda row: row["composite_score"], reverse=True)
    return JSONResponse({**_status(model, error), "agents": rows,
                         "best_agent_id": rows[0]["agent_id"]},
                        headers={"Cache-Control": "private, no-store"})


@router.get("/outcomes")
def outcomes_status(request: Request):
    _authorize(request)
    try:
        return JSONResponse({"dataset":_store().summary()},headers={"Cache-Control":"private, no-store"})
    except (OSError,sqlite3.Error) as exc:
        raise HTTPException(status_code=503,detail="OUTCOME_STORAGE_UNAVAILABLE") from exc


@router.post("/outcomes")
def record_outcome(payload: OutcomePayload, request: Request):
    _authorize(request)
    try:
        dataset=_store().record(payload.model_dump(mode="json"))
    except ValueError as exc:
        raise HTTPException(status_code=409 if "CONFLICT" in str(exc) else 422,detail=str(exc)) from exc
    except (OSError,sqlite3.Error) as exc:
        raise HTTPException(status_code=503,detail="OUTCOME_STORAGE_UNAVAILABLE") from exc
    return JSONResponse({"dataset":dataset,"recorded":True},headers={"Cache-Control":"private, no-store"})


@router.post("/train")
def train_observed(payload: TrainPayload, request: Request):
    _authorize(request)
    if not _training_lock.acquire(blocking=False):
        raise HTTPException(status_code=409,detail="TRAINING_BUSY")
    try:
        try:
            store=_store()
            data=store.summary()
        except (OSError,sqlite3.Error) as exc:
            raise HTTPException(status_code=503,detail="OUTCOME_STORAGE_UNAVAILABLE") from exc
        if data["rows"]<50 or not data["sales_positive"] or not data["sales_negative"]:
            raise HTTPException(status_code=409,detail="TRAINING_DATA_NOT_READY")
        root=Path(__file__).resolve().parents[4]
        prefix=os.getenv("ATLAS_AGENT_PERFORMANCE_MODEL",str(root/".runtime/models/agent_performance"))
        try:
            result=subprocess.run([sys.executable,str(root/"train_agent_performance.py"),"--observed-store",str(store.path),"--output-prefix",prefix],cwd=root,capture_output=True,text=True,timeout=25)
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(status_code=503,detail="TRAINING_TIMED_OUT") from exc
        if result.returncode:
            if "TRAINING_BUSY" in result.stderr:
                raise HTTPException(status_code=409,detail="TRAINING_BUSY")
            raise HTTPException(status_code=422,detail="TRAINING_DATA_REJECTED")
        model,error=_load()
        return JSONResponse(_status(model,error),headers={"Cache-Control":"private, no-store"})
    finally:
        _training_lock.release()
