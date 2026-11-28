"""Safe research status projection; no journal/account data is exposed."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
from .core import VERSION, number, policy
from .data import timestamp


def status(report_path=None, now=None):
    now=now or datetime.now(timezone.utc)
    result={'version':VERSION,'stage':'RESEARCH_ONLY','decision':'ABSTAIN','report_state':'UNAVAILABLE',
            'worker_verified':False,'live_activation_allowed':False,'broker_execution_allowed':False,
            'reason_codes':['NO_VALIDATED_RESEARCH_REPORT'],
            'reviewers':[{'seat':'STC-04','status':'PENDING'},{'seat':'STC-09','status':'PENDING'}]}
    if report_path is None: return result
    try:
        path=Path(report_path)
        if path.stat().st_size>16*1024*1024: raise ValueError('Report too large')
        raw=json.loads(path.read_text(),parse_constant=lambda v: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
        if raw.get('schema_version')!=1 or raw.get('engine_version')!=VERSION or raw.get('stage')!='RESEARCH_ONLY' or raw.get('broker_execution_allowed') is not False or raw.get('live_activation_allowed') is not False:
            raise ValueError('Invalid report provenance')
        if raw.get('data_origin')!='OHLC_COUNTERFACTUAL_BACKTEST' or raw.get('champion_unchanged') is not True:
            raise ValueError('Invalid report origin')
        generated=timestamp(raw['generated_at'])
        if generated>now+timedelta(minutes=1): raise ValueError('Future report')
        count=raw['sample_count']
        if type(count) is not int or count<1: raise ValueError('Invalid sample count')
        if raw['status'] not in {'REJECTED','SHADOW_REVIEW_REQUIRED'}: raise ValueError('Invalid report status')
        model=raw['model_id']
        if not isinstance(model,str) or len(model)!=64 or any(c not in '0123456789abcdef' for c in model):
            raise ValueError('Invalid model ID')
        summaries={}
        for scale in ('1.0','1.5','2.0'):
            card=raw['cost_stress'][scale]
            if type(card['observations']) is not int or not 0<card['observations']<=count: raise ValueError('Invalid observations')
            summaries[scale]={'observations':card['observations'],
                'mean_net_r':number(card['mean_net_r'],'mean',-1e6,1e6),
                'expectancy_lower_r':number(card['expectancy_lower_r'],'lower',-1e6,1e6),
                'status':card['status'] if card['status'] in {'REJECTED','SHADOW_REVIEW'} else 'UNVERIFIED'}
        stale=now-generated>timedelta(hours=24)
        result.update(report_state='STALE' if stale else 'LOCAL_RESEARCH_REPORT',
                      generated_at=generated.isoformat(),model_id=model,sample_count=count,
                      input_kind=raw.get('input_kind') if raw.get('input_kind') in {'SYNTHETIC','HISTORICAL_USER_SUPPLIED','UNVERIFIED_INPUT'} else 'UNVERIFIED_INPUT',
                      research_status=raw['status'],cost_stress=summaries,
                      report_authority='LOCAL_OPERATOR_SUPPLIED_NOT_INDEPENDENTLY_ATTESTED',
                      reason_codes=['RESEARCH_ONLY','INDEPENDENT_REVIEWS_PENDING','RUNTIME_NOT_VERIFIED']+(['REPORT_OLDER_THAN_24_HOURS'] if stale else []))
    except (OSError,ValueError,KeyError,TypeError,AttributeError):
        result['reason_codes']=['MISSING_OR_INVALID_RESEARCH_REPORT']
    return result
