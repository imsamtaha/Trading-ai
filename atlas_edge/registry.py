"""Research registry. It cannot install an inference model or a champion."""
from datetime import datetime,timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile


def register_challenger(report,path):
    if report.get('stage')!='RESEARCH_ONLY' or report.get('broker_execution_allowed') is not False or report.get('champion_unchanged') is not True:
        raise ValueError('Research-only provenance required')
    config=report.get('config')
    fingerprint=sha256(json.dumps(config,sort_keys=True,allow_nan=False).encode()).hexdigest()
    if report.get('model_id')!=fingerprint: raise ValueError('Model fingerprint mismatch')
    target=Path(path)
    data=json.loads(target.read_text()) if target.exists() else {'schema_version':1,'champion':None,'challengers':{}}
    if data.get('schema_version')!=1 or data.get('champion') is not None:
        raise ValueError('This research registry cannot modify a champion')
    entry={'model_id':fingerprint,'config':config,'status':'REJECTED' if report['status']=='REJECTED' else 'AWAITING_INDEPENDENT_REVIEW',
           'registered_at':datetime.now(timezone.utc).isoformat(),'reviews':{'STC-04':'PENDING','STC-09':'PENDING'},
           'inference_installed':False,'live_activation_allowed':False}
    existing=data['challengers'].get(fingerprint)
    if existing and existing['config']!=config: raise ValueError('Immutable version mismatch')
    # Repeated registration is idempotent and never overwrites a review.
    data['challengers'].setdefault(fingerprint,entry)
    target.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(dir=target.parent,prefix='.edge-registry-')
    try:
        with os.fdopen(fd,'w') as handle: json.dump(data,handle,allow_nan=False,indent=2)
        os.replace(name,target)
    finally:
        if os.path.exists(name):os.unlink(name)
    return data['challengers'][fingerprint]
