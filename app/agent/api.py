from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.conversation import converse
from app.agent.core import AtlasAgent
from app.agent.models import AgentRequest, MULTI_TIMEFRAMES
from app.agent.right_hand import build_right_hand_plan, capabilities as right_hand_capabilities
from app.agent.tool_bridge import ConnectorBridgeError, bridge_status, execute_tool
from app.agent.tools import TOOLS, paper_execute
from app.intelligence.titan_council import POLICY as TITAN_POLICY, TitanEvidence, evaluate_titan
from app.intelligence.titan_review import TitanReview, review_titan


router = APIRouter(prefix="/agent", tags=["atlas-agent"])


class DecisionPayload(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    interval: str = Field(default="1h", min_length=1, max_length=10)
    limit: int = Field(default=100, ge=50, le=500)
    account_balance: float = Field(default=10000.0, gt=0)
    risk_percent: float = Field(default=1.0, gt=0, le=2.0)
    multi_timeframe: bool = False


class RightHandPayload(BaseModel):
    request: str = Field(min_length=1, max_length=4000)


class RightHandChatPayload(RightHandPayload):
    interval: str = Field(default="15m", min_length=1, max_length=10)
    multi_timeframe: bool = True
    account_balance: float = Field(default=10000.0, gt=0)
    risk_percent: float = Field(default=1.0, gt=0, le=2.0)


class RightHandToolPayload(BaseModel):
    tool: str = Field(min_length=1, max_length=80)
    arguments: dict = Field(default_factory=dict)
    approved: bool = False


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
        "titan_policy": "/agent/titan/policy",
        "titan_analysis": "/agent/titan/analyze",
        "titan_review": "/agent/titan/review",
        "multi_timeframes": list(MULTI_TIMEFRAMES),
        "multi_timeframe_policy": "unanimous_signals_and_all_risk_approved",
        "right_hand": "/agent/right-hand/capabilities",
        "right_hand_chat": "/agent/right-hand/chat",
        "right_hand_tools": "/agent/right-hand/tools",
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "risk": tool.risk,
            }
            for tool in TOOLS.values()
        ],
    }


@router.get("/titan/policy")
def titan_policy():
    return TITAN_POLICY


@router.post("/titan/analyze")
def titan_analyze(payload: TitanEvidence):
    return evaluate_titan(payload)


@router.post("/titan/review")
def titan_review(payload: TitanReview):
    return review_titan(payload)


@router.get("/right-hand/capabilities")
def right_hand_info():
    payload = right_hand_capabilities()
    payload["connector_bridge"] = bridge_status()
    return payload


@router.get("/right-hand/tools")
def right_hand_tools():
    return bridge_status()


@router.post("/right-hand/tools/execute")
def right_hand_tool_execute(payload: RightHandToolPayload):
    try:
        return execute_tool(payload.tool, payload.arguments, approved=payload.approved)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ConnectorBridgeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/right-hand/plan")
def right_hand_plan(payload: RightHandPayload):
    try:
        return build_right_hand_plan(payload.request).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/right-hand/chat")
def right_hand_chat(payload: RightHandChatPayload):
    try:
        return converse(
            payload.request,
            interval=payload.interval,
            multi_timeframe=payload.multi_timeframe,
            account_balance=payload.account_balance,
            risk_percent=payload.risk_percent,
        ).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


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
