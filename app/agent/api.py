from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.core import AtlasAgent
from app.agent.models import AgentRequest, MULTI_TIMEFRAMES
from app.agent.tools import TOOLS, paper_execute


router = APIRouter(prefix="/agent", tags=["atlas-agent"])


class DecisionPayload(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    interval: str = Field(default="1h", min_length=1, max_length=10)
    limit: int = Field(default=100, ge=50, le=500)
    account_balance: float = Field(default=10000.0, gt=0)
    risk_percent: float = Field(default=1.0, gt=0, le=2.0)
    multi_timeframe: bool = False


class PaperExecutionPayload(BaseModel):
    account_id: int = Field(gt=0)
    symbol: str = Field(min_length=1, max_length=40)
    trade: dict
    confirmed: bool = False


@router.get("/capabilities")
def capabilities():
    return {
        "mode": "paper_only",
        "live_execution": False,
        "multi_timeframes": list(MULTI_TIMEFRAMES),
        "multi_timeframe_policy": "unanimous_signals_and_all_risk_approved",
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "risk": tool.risk,
            }
            for tool in TOOLS.values()
        ],
    }


@router.post("/decision")
def decision(payload: DecisionPayload):
    try:
        agent = AtlasAgent()
        assess = agent.assess_multi_timeframe if payload.multi_timeframe else agent.assess
        result = assess(
            AgentRequest(
                symbol=payload.symbol.upper(),
                interval=payload.interval,
                limit=payload.limit,
                account_balance=payload.account_balance,
                risk_percent=payload.risk_percent,
            )
        )
        return result.to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/paper/execute")
def execute_paper(payload: PaperExecutionPayload):
    try:
        return paper_execute(
            account_id=payload.account_id,
            symbol=payload.symbol,
            trade=payload.trade,
            confirmed=payload.confirmed,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
