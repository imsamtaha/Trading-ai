"""Descriptive entry evidence and frozen paired Paper research; no execution authority."""
from __future__ import annotations
import hashlib
import inspect
import json
import math
import os
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

def stamp(value):
    d = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if d.tzinfo is None:
        raise ValueError('Timezone required')
    return d.astimezone(timezone.utc)

def finite(value):
    try:
        n=float(value)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None

def quality_card(*, candidate, quote, entry, stop, timestamp, technical=None, structure=None, quote_offset=0):
    technical=technical or {}; structure=structure or {}
    now=stamp(timestamp); distance=abs(float(entry)-float(stop))
    bid,ask=finite(quote.get('bid')),finite(quote.get('ask'))
    spread=ask-bid if bid is not None and ask is not None and 0<bid<=ask else None
    fraction=spread/distance if spread is not None and distance>0 else None
    tick=(finite(quote.get('time_msc')) or 0)/1000 or finite(quote.get('time'))
    age=now.timestamp()-(tick-quote_offset) if tick else None
    atr=finite(technical.get('indicators',{}).get('atr_14'))
    atr=atr if atr is not None and atr>0 else None
    reasons=candidate.get('reasons',[])
    target='bullish' if candidate.get('direction')=='LONG' else 'bearish'
    trend=technical.get('trend'); momentum=technical.get('momentum')
    ratio=distance/atr if atr else None
    components={
        'trend':25 if trend==target else 0 if trend in ('bullish','bearish','neutral') else None,
        'structure':25 if 'Structure aligned' in reasons else 0 if 'Structure misaligned' in reasons else None,
        'momentum':20 if momentum==target else 0 if momentum in ('bullish','bearish','overbought','oversold') else None,
        'volatility':15 if ratio is not None and .5<=ratio<=3 else 0 if ratio is not None else None,
        'liquidity':15 if fraction is not None and fraction<=.25 else 0 if fraction is not None else None,
    }
    flags=[]
    if any(v is None for v in components.values()):flags.append('INCOMPLETE_EVIDENCE')
    if fraction is not None and fraction>.25:flags.append('SPREAD_TOO_WIDE')
    if age is None:flags.append('QUOTE_TIME_UNAVAILABLE')
    elif not -5<=age<=30:flags.append('STALE_OR_FUTURE_QUOTE')
    if spread is None:flags.append('INVALID_QUOTE')
    return dict(version=1, recorded_at=now.isoformat(),source='MT5',timeframe_scope='ENTRY_TIMEFRAME_ONLY',
        higher_timeframe_confirmed=False,broker_execution_allowed=False,changes_trade_decision=False,
        score=sum(components.values()) if all(v is not None for v in components.values()) else None,
        score_type='DESCRIPTIVE_UNVALIDATED_NOT_WIN_PROBABILITY',components=components,flags=flags,
        quote={k:finite(quote.get(k)) for k in ('bid','ask','time','time_msc')},quote_offset_seconds=quote_offset,
        quote_age_seconds=round(age,3) if age is not None else None,spread_to_stop=fraction,
        atr_14=atr,stop_to_atr=ratio,technical={k:technical.get(k) for k in ('trend','momentum','macd_signal','volume_state')},
        structure=structure,entry_reasons=list(reasons),utc_hour=now.hour,
        snapshot_id=f"{candidate.get('symbol','UNKNOWN')}:{timestamp}",
        costs={'spread_in_simulated_bid_ask':True,'commission':None,'swap':None,'slippage_model':'NEXT_OBSERVED_EXECUTABLE_QUOTE'})

def settled(rows, cutoff):
    from app.intelligence.shadow_selector import ShadowSelector
    cutoff=stamp(cutoff);valid={};conflicts=set();invalid=duplicates=0
    for row in rows:
        try:
            identity=str(row['id']);opened=stamp(row['opened_at']);closed=stamp(row['closed_at'])
            if not identity or row.get('status')!='CLOSED' or not opened<=closed<=cutoff or finite(row['r_multiple']) is None:
                raise ValueError('Unsettled or future outcome')
            intent=(row.get('training_context') or {}).get('trade_intent') or {}
            if row.get('broker_execution_allowed') or intent.get('broker_execution_allowed') or str(row.get('execution_environment','PAPER')).upper()!='PAPER':
                raise ValueError('Paper only')
            row={**row,'r_multiple':float(row['r_multiple'])}
            ShadowSelector.features(row)
            if identity in valid:
                duplicates+=1
                if valid[identity]!=row:conflicts.add(identity)
            else:valid[identity]=dict(row)
        except (KeyError,ValueError,TypeError,OverflowError):invalid+=1
    for identity in conflicts:valid.pop(identity,None)
    return sorted(valid.values(),key=lambda r:(stamp(r['opened_at']),r['id'])),dict(invalid_records=invalid,duplicate_records=duplicates,conflicting_ids=len(conflicts))

def feature_fingerprint():
    from app.intelligence.shadow_selector import ShadowSelector
    from app.strategy import universe
    source=inspect.getsource(ShadowSelector.features)+Path(universe.__file__).read_text(encoding='utf-8-sig')
    return hashlib.sha256(source.encode()).hexdigest()

def model_predict(model,row):
    from app.intelligence.shadow_selector import ShadowSelector,sigmoid
    pair=list(ShadowSelector._support(row))
    if pair not in model['supported_pairs']:return None
    raw=sum(w*x for w,x in zip(model['weights'],ShadowSelector.features(row)))
    return sigmoid(model['calibrator'][0]+model['calibrator'][1]*raw)

def stats(scored):
    selected=[r for r,p in scored if p>=.8]
    gains=sum(max(0,float(r['r_multiple'])) for r in selected)
    losses=-sum(min(0,float(r['r_multiple'])) for r in selected)
    return dict(samples=len(scored),selected=len(selected),coverage=len(selected)/len(scored) if scored else None,
        brier=sum((p-float(r['r_multiple']>0))**2 for r,p in scored)/len(scored) if scored else None,
        selected_sum_r=sum(float(r['r_multiple']) for r in selected),profit_factor_r=gains/losses if losses else None,
        mean_selected_r=sum(float(r['r_multiple']) for r in selected)/len(selected) if selected else None)

def freeze_experiment(rows,now):
    from app.intelligence.shadow_selector import ShadowSelector,train
    now=stamp(now);valid,counts=settled(rows,now)
    report=dict(version=1,created_at=now.isoformat(),status='INSUFFICIENT_DATA',broker_execution_allowed=False,
        changes_trade_decision=False,threshold=.8,samples=len(valid),validation=counts,
        design='Frozen matched features, regularization, epochs, calibration and historical holdout; baseline thins unique training rows 1:2, dense retains all. Forward predictions saved at entry.',
        minimum_forward_outcomes=100,minimum_forward_days=5,commission_assumption=None)
    report.update(feature_schema_version=1,feature_fingerprint=feature_fingerprint(),training_configuration={'epochs':200,'regularization':.05,'learning_rate':.2,'seed':'deterministic-no-randomness'})
    report['experiment_id']=hashlib.sha256(json.dumps([now.isoformat(),[r['id'] for r in valid]]).encode()).hexdigest()[:20]
    if len(valid)<100 or len({stamp(r['opened_at']).date() for r in valid})<3:return report
    a,b=int(len(valid)*.6),int(len(valid)*.8);calibration=valid[a:b];holdout=valid[b:]
    training=[r for r in valid[:a] if stamp(r['closed_at'])<stamp(calibration[0]['opened_at'])]
    calibration=[r for r in calibration if stamp(r['closed_at'])<stamp(holdout[0]['opened_at'])]
    baseline=training[::2]
    if len(baseline)<30 or len(calibration)<10 or len(holdout)<10:return report
    models={}
    for name,subset in [('baseline',baseline),('dense',training)]:
        labels=[float(r['r_multiple']>0) for r in subset];cy=[float(r['r_multiple']>0) for r in calibration]
        if len(set(labels))<2 or len(set(cy))<2:
            report['status']='INSUFFICIENT_LABEL_VARIATION';return report
        weights=train([ShadowSelector.features(r) for r in subset],labels,epochs=200)
        cx=[[1.,sum(w*x for w,x in zip(weights,ShadowSelector.features(r)))] for r in calibration]
        models[name]=dict(weights=weights,calibrator=train(cx,cy,epochs=200),training_samples=len(subset),
            training_ids=[r['id'] for r in subset],calibration_ids=[r['id'] for r in calibration],
            supported_pairs=sorted([list(p) for p in {ShadowSelector._support(r) for r in subset}]))
    replay={};predictions={}
    for name,model in models.items():
        predictions[name]=[(r,model_predict(model,r)) for r in holdout]
    paired_ids={r['id'] for r,p in predictions['baseline'] if p is not None}&{r['id'] for r,p in predictions['dense'] if p is not None}
    for name,pairs in predictions.items():
        replay[name]=stats([(r,p) for r,p in pairs if r['id'] in paired_ids])
        replay[name]['unpaired_supported_count']=sum(p is not None for _,p in pairs)
    report.update(status='FROZEN_SHADOW',models=models,trained_through=max(r['closed_at'] for r in training+calibration),
        historical_test_ids=[r['id'] for r in holdout],historical_replay=replay,
        replay_label='EXPLORATORY_HISTORICAL_NOT_FORWARD_EVIDENCE')
    return report

def forecast(experiment,row):
    result=dict(status=experiment.get('status','INSUFFICIENT_DATA'),experiment_id=experiment['experiment_id'],
        broker_execution_allowed=False,changes_trade_decision=False,probabilities=None)
    if experiment.get('status')!='FROZEN_SHADOW':return result
    if experiment.get('feature_fingerprint')!=feature_fingerprint():
        result['status']='FEATURE_SCHEMA_CHANGED';return result
    timestamp=stamp(row.get('timestamp') or row['opened_at'])
    if timestamp<stamp(experiment['created_at']) or timestamp<=stamp(experiment['trained_through']):
        result['status']='PRE_EXPERIMENT';return result
    probabilities={name:model_predict(model,row) for name,model in experiment['models'].items()}
    if any(p is None for p in probabilities.values()):result['status']='UNSUPPORTED_PAIR';return result
    return dict(result,status='PAIRED_SHADOW',recorded_at=timestamp.isoformat(),probabilities=probabilities)

def comparison_report(experiment,rows,now):
    now=stamp(now);valid,counts=settled(rows,now);paired=[]
    for row in valid:
        evidence=(row.get('quality_card') or {}).get('density_experiment') or {}
        try:
            probabilities=evidence.get('probabilities')
            if evidence.get('experiment_id')!=experiment['experiment_id'] or evidence.get('status')!='PAIRED_SHADOW' or not probabilities:continue
            saved=stamp(evidence['recorded_at']);opened=stamp(row['opened_at'])
            if not stamp(experiment['created_at'])<=saved<=opened<=stamp(row['closed_at']):continue
            if set(probabilities)!={'baseline','dense'} or any(finite(p) is None or not 0<=p<=1 for p in probabilities.values()):continue
            paired.append((row,probabilities))
        except (ValueError,TypeError,KeyError):continue
    days=len({stamp(r['opened_at']).date() for r,_ in paired})
    report=dict(version=1,generated_at=now.isoformat(),experiment_id=experiment['experiment_id'],
        broker_execution_allowed=False,changes_trade_decision=False,validation=counts,
        decision='COLLECT_FORWARD_EVIDENCE',historical_replay=experiment.get('historical_replay'),
        evidence_status='MINIMUM_REVIEW_WINDOW_REACHED' if len(paired)>=100 and days>=5 else 'INSUFFICIENT_FORWARD_DATA',
        forward=dict(paired_outcomes=len(paired),observed_days=days,net_profit_after_fees=None,
            baseline=stats([(r,p['baseline']) for r,p in paired]),dense=stats([(r,p['dense']) for r,p in paired])))
    # Reaching a minimum window requests review; it never activates a model or implies causality.
    return report

def atomic_save(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix=path.stem+'-',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as handle:
            json.dump(data,handle,ensure_ascii=False,indent=2,allow_nan=False);handle.flush();os.fsync(handle.fileno())
        try:os.replace(temp,path)
        except PermissionError:
            if os.name!='nt' or not path.exists():raise
            from app.paper_trading.mt5_ledger import _win_replace_existing
            _win_replace_existing(Path(temp),path)
    finally:
        if os.path.exists(temp):os.unlink(temp)

class PaperQualityLab:
    def __init__(self,directory):
        self.directory=Path(directory);self.path=self.directory/'density-experiment.json';self.experiment=None
        self.load_error=None
        self.experiment=self._read_experiment()

    def _read_experiment(self):
        try:
            if not self.path.exists():return None
            value=json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(value,dict) or not value.get('experiment_id') or value.get('broker_execution_allowed') is not False:
                raise ValueError('Invalid research manifest')
            if value.get('status')=='FROZEN_SHADOW':
                stamp(value['created_at']);stamp(value['trained_through'])
                if set(value['models'])!={'baseline','dense'}:raise ValueError('Paired models required')
            self.load_error=None
            return value
        except (OSError,ValueError,TypeError,KeyError) as exc:
            self.load_error=str(exc)
            return None

    @contextmanager
    def _freeze_lock(self):
        self.directory.mkdir(parents=True,exist_ok=True)
        with (self.directory/'freeze.lock').open('a+b') as handle:
            if os.fstat(handle.fileno()).st_size==0:handle.write(b'0');handle.flush()
            deadline=time.monotonic()+2
            while True:
                try:
                    handle.seek(0)
                    if os.name=='nt':
                        import msvcrt
                        msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic()>=deadline:raise OSError('Research freeze busy; retry next settlement')
                    time.sleep(.02)
            try:yield
            finally:
                handle.seek(0)
                if os.name=='nt':msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
                else:fcntl.flock(handle.fileno(),fcntl.LOCK_UN)

    def refresh(self,rows):
        now=datetime.now(timezone.utc)
        with self._freeze_lock():
            # Reload under the process lock: a second worker must use the committed model.
            existing=self._read_experiment()
            if existing and existing.get('status')=='FROZEN_SHADOW':self.experiment=existing
            else:
                if self.load_error and self.path.exists():
                    backup=self.directory/f'density-experiment.invalid-{time.time_ns()}.json'
                    backup.write_bytes(self.path.read_bytes())
                self.experiment=freeze_experiment(rows,now);atomic_save(self.path,self.experiment)
        report=comparison_report(self.experiment,rows,now)
        atomic_save(self.directory/'density-comparison.json',report)
        cards=[r for r in rows if r.get('quality_card')]
        atomic_save(self.directory/'quality-summary.json',dict(generated_at=now.isoformat(),closed=len(rows),
            with_entry_evidence=len(cards),legacy_without_entry_evidence=len(rows)-len(cards),
            overshot_stop_count=sum(r.get('exit_reason')=='STOP_LOSS' and r.get('r_multiple',0)<-1.5 for r in rows),
            score_type='DESCRIPTIVE_UNVALIDATED_NOT_WIN_PROBABILITY',commission_verified=False,broker_execution_allowed=False))
        return report

    def predict(self,row):
        if not self.experiment:return None
        return forecast(self.experiment,row)
