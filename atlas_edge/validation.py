"""Chronological, paired, cost-adjusted validation; no promotion side effects."""
from math import fsum
import random
from statistics import mean
from .core import number
from .data import timestamp


def purged_walk_forward(events, folds=3, embargo=1):
    if type(folds) is not int or folds<2 or type(embargo) is not int or embargo<1:
        raise ValueError('Invalid folds/embargo')
    if len(events)<(folds+1)*10: raise ValueError('Insufficient events')
    if any(a['decision_index']>=b['decision_index'] for a,b in zip(events,events[1:])):
        raise ValueError('Events must be strictly chronological')
    width=len(events)//(folds+1)
    result=[]
    for fold in range(folds):
        start=(fold+1)*width
        end=(fold+2)*width if fold<folds-1 else len(events)
        first=events[start]['decision_index']
        train=[i for i in range(start) if events[i]['end_index']<first-embargo
               and timestamp(events[i]['label_available_at']) < timestamp(events[start]['time'])]
        if not train: raise ValueError('No training data after purging')
        result.append((train,list(range(start,end))))
    return result


def calibration(probabilities, labels, bins=10):
    if len(probabilities)!=len(labels) or not labels: raise ValueError('Missing calibration data')
    p=[number(v,'probability',0,1) for v in probabilities]
    if any(type(y) is not int or y not in (0,1) for y in labels): raise ValueError('Invalid labels')
    groups={}
    for q,y in zip(p,labels): groups.setdefault(min(bins-1,int(q*bins)),[]).append((q,y))
    return {'brier':mean((q-y)**2 for q,y in zip(p,labels)),
            'ece':fsum(len(g)/len(p)*abs(mean(q for q,_ in g)-mean(y for _,y in g)) for g in groups.values()),
            'bins':[{'count':len(g),'probability':mean(q for q,_ in g),'frequency':mean(y for _,y in g)} for g in groups.values()]}


def block_lower(values, *, block=10, trials=1, seed=7, resamples=2000):
    if not values: raise ValueError('Empty return stream')
    v=[number(x,'return',-1e6,1e6) for x in values]
    if type(trials) is not int or not 1<=trials<=100 or type(block) is not int or block<1 or block>len(v):
        raise ValueError('Invalid block/trial count')
    # At least 20 draws in the Bonferroni-adjusted lower tail.
    resamples=max(resamples,400*trials)
    rng=random.Random(seed);boot=[]
    for _ in range(resamples):
        sample=[]
        while len(sample)<len(v):
            start=rng.randrange(len(v));sample.extend(v[(start+j)%len(v)] for j in range(block))
        boot.append(mean(sample[:len(v)]))
    boot.sort()
    return boot[int(.05/trials*len(boot))]


def scorecard(candidate, baselines, *, probabilities, labels, trials=1, block=10, minimum=200):
    if type(minimum) is not int or minimum<200: raise ValueError('OOS minimum cannot be below 200')
    required={'cash','trend','random','v2_1'}
    if set(baselines)!=required: raise ValueError('All four aligned baselines are required')
    n=len(candidate)
    if n<block or len(probabilities)!=n or len(labels)!=n or any(len(v)!=n for v in baselines.values()):
        raise ValueError('Unaligned evidence')
    c=[number(v,'candidate',-1e6,1e6) for v in candidate]
    metrics=calibration(probabilities,labels)
    adjusted_trials=trials*5  # Familywise correction includes expectancy and four baseline comparisons.
    lower=block_lower(c,block=block,trials=adjusted_trials)
    comparisons={name:block_lower([x-number(y,'baseline',-1e6,1e6) for x,y in zip(c,values)],block=block,trials=adjusted_trials)
                 for name,values in baselines.items()}
    reasons=[]
    if n<minimum: reasons.append('INSUFFICIENT_OOS_DECISIONS')
    if lower<=0: reasons.append('NONPOSITIVE_EXPECTANCY_LOWER_BOUND')
    if any(v<=0 for v in comparisons.values()): reasons.append('BASELINE_NOT_BEATEN_WITH_SUPPORT')
    if metrics['ece']>.10: reasons.append('CALIBRATION_ERROR')
    peak=equity=drawdown=0.0
    for value in c:
        equity+=value;peak=max(peak,equity);drawdown=max(drawdown,peak-equity)
    losses=-fsum(min(0,x) for x in c)
    risk_metrics={'profit_factor':fsum(max(0,x) for x in c)/losses if losses else None,
                  'max_drawdown_r':drawdown,'worst_decision_r':min(c),
                  'tail_mean_r':mean(sorted(c)[:max(1,len(c)//20)]),
                  'annualized_metrics':'UNAVAILABLE_WITHOUT_EQUITY_TIME_SERIES'}
    # A scorecard is research evidence, never a live trading switch.
    return {'status':'SHADOW_REVIEW' if not reasons else 'REJECTED','observations':n,
            'mean_net_r':mean(c),'risk_metrics':risk_metrics,'expectancy_lower_r':lower,'baseline_difference_lower_r':comparisons,
            'calibration':metrics,'gate_reasons':reasons,'trials_declared':trials,'block_size':block,
            'reviewers':[{'seat':'STC-04','status':'PENDING'},{'seat':'STC-09','status':'PENDING'}],
            'broker_execution_allowed':False,'live_activation_allowed':False}
