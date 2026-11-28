"""Research-only v3 endpoints: no execution authority or account access."""
import os
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from atlas_edge.core import EdgeEvidence, evaluate_edge, policy
from atlas_edge.status import status

router=APIRouter(prefix='/agent/v3',tags=['edge-v3-research'])


class Evidence(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False,protected_namespaces=('model_dump',))
    probability: float = Field(ge=0,le=1,strict=True)
    probability_lower: float = Field(ge=0,le=1,strict=True)
    average_win_gross_r: float = Field(ge=0,le=1000,strict=True)
    average_loss_gross_r: float = Field(gt=0,le=1000,strict=True)
    spread_r: float = Field(ge=0,le=1000,strict=True)
    slippage_r: float = Field(ge=0,le=1000,strict=True)
    fees_r: float = Field(ge=0,le=1000,strict=True)
    ev_lower_r: float = Field(ge=-1000,le=1000,strict=True)
    target_volatility: float = Field(gt=0,le=1000,strict=True)
    instrument_volatility: float = Field(gt=0,le=1000,strict=True)
    drawdown: float = Field(ge=0,le=1,strict=True)
    risk_ceiling: float = Field(ge=0,le=.02,strict=True)
    risk_approval: str = Field(max_length=32)
    resolved_oos: int = Field(ge=0,le=100000000,strict=True)
    model_version: str = Field(min_length=1,max_length=120)
    feature_hash: str = Field(pattern='^[0-9a-f]{64}$')
    data_fresh: StrictBool
    model_validated: StrictBool
    source: str = Field(default='QUANT',max_length=20)


@router.get('/policy')
def edge_policy(): return policy()


@router.get('/status')
def edge_status(): return status(os.getenv('ATLAS_EDGE_V3_REPORT'))


@router.post('/evaluate')
def edge_evaluate(evidence:Evidence):
    result=evaluate_edge(EdgeEvidence(**evidence.model_dump()))
    result['evidence_provenance']='CALLER_SUPPLIED_NOT_INDEPENDENTLY_ATTESTED'
    return result
