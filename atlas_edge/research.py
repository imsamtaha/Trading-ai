"""Measuring-stick first: reproducible single-sleeve challengers, never live models."""
from collections import defaultdict
from dataclasses import asdict
from hashlib import sha256
import json
from math import sqrt
from statistics import mean
import random

from .core import VERSION, policy
from .data import feature_snapshot, triple_barrier, timestamp, round_trip_cost_r
from .validation import purged_walk_forward, scorecard, calibration, block_lower


def evaluate_research(bars, *, sleeve='trend', horizon=10, folds=3, trials=1, old_council=None, input_kind='UNVERIFIED_INPUT', source_label=''):
    if input_kind not in {'UNVERIFIED_INPUT','SYNTHETIC','HISTORICAL_USER_SUPPLIED'}: raise ValueError('Invalid input provenance')
    if input_kind=='HISTORICAL_USER_SUPPLIED' and (not isinstance(source_label,str) or not source_label.strip()): raise ValueError('Historical source label required')
    if sleeve not in {'trend','mean_reversion','breakout'}: raise ValueError('Unknown sleeve')
    if type(horizon) is not int or not 1<=horizon<=100: raise ValueError('Invalid horizon')
    if type(trials) is not int or not 1<=trials<=10: raise ValueError('Declare 1–10 total tried configurations per run family')
    if old_council is not None:
        normalized={}
        for key,value in old_council.items():
            instant=timestamp(key)
            if type(value) is not int or value not in (-1,0,1):
                raise ValueError('v2.1 sides must be -1, 0, 1')
            if instant in normalized and normalized[instant]!=value:
                raise ValueError('Conflicting v2.1 decisions for the same timestamp')
            normalized[instant]=value
        old_council=normalized
    cutoff=int(len(bars)*.8)
    development=bars[:cutoff]
    events=[];rng=random.Random(7)
    # Fixed, non-overlapping decision cadence; no overlapping wagers inflate samples.
    for i in range(20,len(development)-horizon,horizon):
        snapshot=feature_snapshot(development,i)
        side=snapshot['sleeves'][sleeve]
        distance=snapshot['features']['atr14']*1.5
        hypotheses={d:triple_barrier(development,i,d,distance,horizon=horizon) for d in (-1,1)}
        candidate=hypotheses[side or 1]
        trend=snapshot['sleeves']['trend'];random_side=rng.choice([-1,1])
        key=snapshot['time']
        old_side=old_council.get(timestamp(key)) if old_council is not None else None
        if old_side is not None and (type(old_side) is not int or old_side not in (-1,0,1)):
            raise ValueError('v2.1 sides must be -1, 0, 1')
        events.append({**candidate,'time':key,'side':side,'bucket':min(4,int(abs(snapshot['features']['normalized_deviation']))),
            'feature_hash':snapshot['feature_hash'],'predicted_cost_r':round_trip_cost_r(development[i],development[i].close,distance),
            'baselines':{'cash':None,'trend':hypotheses[trend] if trend else None,
                         'random':hypotheses[random_side],'v2_1':hypotheses[old_side] if old_side else None},
            'old_baseline_known':old_side is not None})
    splits=purged_walk_forward(events,folds=folds,embargo=1)
    streams={scale:[] for scale in (1.0,1.5,2.0)}
    baseline_streams={scale:{name:[] for name in ('cash','trend','random','v2_1')} for scale in streams}
    probabilities=[];labels=[];oos=[];split_log=[];majority_predictions=[];train_correct=[]
    for train,test in splits:
        bins=defaultdict(list)
        for j in train:
            row=events[j]
            if row['side']: bins[row['bucket']].append(row)
        fitted={}
        for bucket,history in bins.items():
            p=(sum(x['label'] for x in history)+1)/(len(history)+2)
            mean_gross=mean(x['gross_r'] for x in history)
            lower=block_lower([x['gross_r'] for x in history],block=min(10,len(history)),trials=trials*5) if len(history)>=30 else None
            uncertainty=1/(len(history)+2)**.5
            fitted[bucket]={'p':p,'mean_gross':mean_gross,'lower':lower,'hurdle':.05+uncertainty}
        majority=mean(events[j]['label'] for j in train)>=.5
        for j in train:
            row=events[j];pred=fitted.get(row['bucket'],{'p':.5})['p']>=.5
            train_correct.append(int(pred==bool(row['label'])))
        split_log.append({'train_decisions':len(train),'test_decisions':len(test),
                          'train_label_max':max(events[j]['label_available_at'] for j in train),
                          'test_start':events[test[0]]['time']})
        for j in test:
            row=events[j];history=bins[row['bucket']]
            # Transparent frequency meta-labeler prototype; no fitted signal weights.
            estimate=fitted.get(row['bucket'])
            p=estimate['p'] if estimate else .5
            expected=estimate['mean_gross']-row['predicted_cost_r'] if estimate else None
            ev_lower=estimate['lower']-row['predicted_cost_r'] if estimate and estimate['lower'] is not None else None
            # No historical support, no action; this is not Senior Risk approval.
            selected=bool(row['side'] and len(history)>=30 and p>.5 and expected is not None and expected>estimate['hurdle'] and ev_lower is not None and ev_lower>0)
            probabilities.append(p);labels.append(row['label']);majority_predictions.append(int(majority))
            for scale in streams:
                streams[scale].append(row['gross_r']-scale*row['cost_r'] if selected else 0.0)
                for name,trade in row['baselines'].items():
                    baseline_streams[scale][name].append(trade['gross_r']-scale*trade['cost_r'] if trade else 0.0)
            oos.append({'time':row['time'],'end_index':row['end_index'],'feature_hash':row['feature_hash'],
                        'selected':selected,'probability':p,'label':row['label'],
                        'gross_r':row['gross_r'],'cost_r':row['cost_r'],
                        'cost_prediction_error_r':row['cost_r']-row['predicted_cost_r'],
                        'old_baseline_known':row['old_baseline_known']})
    accuracy=mean(int((p>=.5)==bool(y)) for p,y in zip(probabilities,labels))
    majority_accuracy=mean(int(p==y) for p,y in zip(majority_predictions,labels))
    train_accuracy=mean(train_correct)
    stability=accuracy/train_accuracy if train_accuracy else 0.0
    meta_metrics={'oos_accuracy':accuracy,'training_accuracy':train_accuracy,
                  'training_fold_majority_oos_accuracy':majority_accuracy,'stability':stability}
    cards={}
    for scale in streams:
        cards[str(scale)]=scorecard(streams[scale],baseline_streams[scale],probabilities=probabilities,
                                   labels=labels,trials=trials,block=min(10,len(oos)))
        card=cards[str(scale)]
        if not all(r['old_baseline_known'] for r in oos):
            card['gate_reasons'].append('V2_1_BASELINE_UNAVAILABLE')
            card['baseline_difference_lower_r']['v2_1']=None
            card['status']='REJECTED'
        if accuracy<=max(.525,majority_accuracy+.005) or stability<.8:
            card['gate_reasons'].append('META_LABELER_BASELINE_OR_STABILITY_GATE')
            card['status']='REJECTED'
        if input_kind!='HISTORICAL_USER_SUPPLIED':
            card['gate_reasons'].append('SYNTHETIC_OR_UNVERIFIED_INPUT')
            card['status']='REJECTED'
    rejected=any(c['status']=='REJECTED' for c in cards.values())
    serial=[{**asdict(b),'time':b.time.isoformat(),'available_at':b.available_at.isoformat()} for b in bars]
    data_hash=sha256(json.dumps(serial,sort_keys=True,allow_nan=False).encode()).hexdigest()
    config={'sleeve':sleeve,'horizon':horizon,'folds':folds,'trials':trials,'data_hash':data_hash,'input_kind':input_kind,'source_label':source_label}
    model_id=sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    return {'schema_version':1,'engine_version':VERSION,'model_id':model_id,'config':config,
            'stage':'RESEARCH_ONLY','status':'REJECTED' if rejected else 'SHADOW_REVIEW_REQUIRED',
            'data_origin':'OHLC_COUNTERFACTUAL_BACKTEST','input_kind':input_kind,'source_label':source_label,'sample_count':len(oos),
            'metrics_unit':'R_PER_FIXED_NONOVERLAPPING_DECISION_NOT_EQUITY_RETURN',
            'label_method':'next_bar_entry_stop_first_triple_barrier',
            'meta_labeler':'TRAIN_FOLD_STRENGTH_BUCKET_FREQUENCY_PROTOTYPE','meta_labeler_metrics':meta_metrics,
            'cost_convention':'round_trip_bps_spread_plus_slippage_plus_fees',
            'holdout':{'start':bars[cutoff].time.isoformat(),'bars':len(bars)-cutoff,'status':'NOT_EVALUATED_BY_THIS_RUN'},
            'walk_forward':split_log,'cost_stress':cards,'resolved_decisions':oos,
            'reviewers':[{'seat':'STC-04','status':'PENDING'},{'seat':'STC-09','status':'PENDING'}],
            'unimplemented_promotion_gates':['matched_portfolio_risk_adjusted_returns','sleeve_ablation',
                'regime_validation','live_fill_cost_calibration','rescue_exit_validation','independent_reviews'],
            'champion_unchanged':True,'broker_execution_allowed':False,'live_activation_allowed':False,
            'policy':policy()}
