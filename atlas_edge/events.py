"""LLM/provider event evidence is feature/risk data, never a directional vote."""
import re
from .data import timestamp
from .core import number


def validate_event(raw, as_of):
    required={'event_type','symbols','surprise','novelty','risk_flag','published_at','available_at','source'}
    if not isinstance(raw,dict) or set(raw)!=required: raise ValueError('Structured event fields only; direction/order fields are forbidden')
    if raw['event_type'] not in {'earnings','macro','legal','geopolitical','corporate','other'}:
        raise ValueError('Unknown event type')
    if not isinstance(raw['symbols'],list) or not 1<=len(raw['symbols'])<=50 or any(not isinstance(x,str) or not re.fullmatch(r'[A-Z0-9.^=-]{1,24}',x) for x in raw['symbols']):
        raise ValueError('Invalid affected symbols')
    for key in ('surprise','novelty'): number(raw[key],key,0,1)
    if type(raw['risk_flag']) is not bool: raise ValueError('Explicit risk flag required')
    if not isinstance(raw['source'],str) or not 1<=len(raw['source'])<=200: raise ValueError('Missing source')
    published,available=timestamp(raw['published_at']),timestamp(raw['available_at'])
    if not published<=available<=as_of: raise ValueError('Future/unavailable event evidence')
    return {**raw,'role':'FEATURE_OR_RISK_ONLY','direction_allowed':False,'source_independently_verified':False}
