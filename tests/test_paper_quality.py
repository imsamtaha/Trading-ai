import unittest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
try:
    from app.intelligence import paper_quality as q
except ImportError:
    q = None

NOW = datetime(2026, 10, 13, 8, 0, tzinfo=timezone.utc)

def rows(n=160):
    result = []
    for i in range(n):
        opened = NOW - timedelta(days=10) + timedelta(hours=i)
        result.append(dict(id=str(i), status='CLOSED', symbol='EURUSD', strategy='CONTINUATION_5M', direction='LONG', confidence=75+(i%2)*20, opened_at=opened.isoformat(), closed_at=(opened+timedelta(minutes=5)).isoformat(), r_multiple=2 if i%3 else -1, risk_normalized_pnl=20 if i%3 else -10))
    return result

class QualityTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(q, 'Paper quality and paired density experiment are not implemented')

    def test_missing_evidence_is_unknown_not_zero_or_perfect_score(self):
        card=q.quality_card(candidate={},quote={},entry=100,stop=99,timestamp=NOW.isoformat())
        self.assertIsNone(card['score']);self.assertIsNone(card['components']['trend'])
        self.assertIn('INCOMPLETE_EVIDENCE',card['flags'])
        self.assertIsNone(card['costs']['commission']);self.assertFalse(card['changes_trade_decision'])

    def test_wide_spread_flags_even_when_technical_factors_align(self):
        c=dict(direction='LONG',reasons=['Trend aligned','Structure aligned','Momentum aligned'])
        card=q.quality_card(candidate=c,quote={'bid':99,'ask':100,'time':NOW.timestamp()},entry=100,stop=99.5,timestamp=NOW.isoformat(),technical={'trend':'bullish','momentum':'bullish','indicators':{'atr_14':1}})
        self.assertIn('SPREAD_TOO_WIDE',card['flags']);self.assertEqual(card['spread_to_stop'],2)
        self.assertFalse(card['higher_timeframe_confirmed'])

    def test_broker_clock_offset_is_preserved_and_corrected_for_age(self):
        card=q.quality_card(candidate={},quote={'bid':99.99,'ask':100,'time':NOW.timestamp()+10800},entry=100,stop=99,timestamp=NOW.isoformat(),quote_offset=10800)
        self.assertEqual(card['quote_age_seconds'],0);self.assertEqual(card['quote']['time'],NOW.timestamp()+10800)

    def test_absent_structure_does_not_become_a_known_zero_component(self):
        card=q.quality_card(candidate={'direction':'LONG','reasons':['Trend aligned']},quote={'bid':99.99,'ask':100,'time':NOW.timestamp()},entry=100,stop=99,timestamp=NOW.isoformat(),technical={'trend':'bullish','momentum':'bullish','indicators':{'atr_14':1}})
        self.assertIsNone(card['components']['structure']);self.assertIsNone(card['score'])

    def test_eligible_training_removes_future_live_open_and_conflicting_duplicate(self):
        a=rows(4);a.append(dict(a[0]));a.append(dict(a[1],r_multiple=9));a.append(dict(a[2],id='future',closed_at=(NOW+timedelta(days=1)).isoformat()));a.append(dict(a[2],id='live',broker_execution_allowed=True));a.append(dict(a[2],id='open',status='OPEN'))
        valid,counts=q.settled(a,NOW)
        self.assertEqual({r['id'] for r in valid},{'0','2','3'});self.assertEqual(counts['conflicting_ids'],1)

    def test_frozen_models_share_calibration_and_test_and_vary_unique_training_count(self):
        exp=q.freeze_experiment(rows(),NOW)
        self.assertEqual(exp['status'],'FROZEN_SHADOW')
        self.assertGreater(exp['models']['dense']['training_samples'],exp['models']['baseline']['training_samples'])
        self.assertEqual(exp['models']['dense']['calibration_ids'],exp['models']['baseline']['calibration_ids'])
        self.assertLess(exp['trained_through'],exp['created_at'])
        self.assertFalse(exp['broker_execution_allowed'])

    def test_prediction_before_experiment_or_unknown_pair_is_not_forward_evidence(self):
        exp=q.freeze_experiment(rows(),NOW);r=rows()[0]
        self.assertEqual(q.forecast(exp,r)['status'],'PRE_EXPERIMENT')
        self.assertEqual(q.forecast(exp,dict(r,timestamp=(NOW+timedelta(seconds=1)).isoformat(),opened_at=None,symbol='UNSEEN'))['status'],'UNSUPPORTED_PAIR')

    def test_report_does_not_call_historical_replay_forward_profit(self):
        exp=q.freeze_experiment(rows(),NOW);report=q.comparison_report(exp,rows(),NOW)
        self.assertEqual(report['forward']['paired_outcomes'],0)
        self.assertEqual(report['decision'],'COLLECT_FORWARD_EVIDENCE')
        self.assertIsNone(report['forward']['net_profit_after_fees'])

    def test_report_pairs_new_closed_rows_once_using_saved_entry_predictions(self):
        exp=q.freeze_experiment(rows(),NOW);r=rows()[0];r=dict(r,id='forward',opened_at=(NOW+timedelta(seconds=1)).isoformat(),closed_at=(NOW+timedelta(minutes=10)).isoformat())
        prediction=q.forecast(exp,r);self.assertEqual(prediction['status'],'PAIRED_SHADOW')
        r['quality_card']={'density_experiment':prediction}
        report=q.comparison_report(exp,[r,r],NOW+timedelta(hours=1))
        self.assertEqual(report['forward']['paired_outcomes'],1)
        self.assertEqual(report['forward']['baseline']['samples'],1)

    def test_small_or_one_class_dataset_stays_insufficient(self):
        self.assertEqual(q.freeze_experiment(rows(12),NOW)['status'],'INSUFFICIENT_DATA')
        self.assertEqual(q.freeze_experiment([dict(r,r_multiple=1) for r in rows()],NOW)['status'],'INSUFFICIENT_LABEL_VARIATION')

    def test_malformed_feature_is_counted_invalid_without_poisoning_training(self):
        data=rows();data.append(dict(data[0],id='bad',confidence='bad'))
        exp=q.freeze_experiment(data,NOW)
        self.assertEqual(exp['status'],'FROZEN_SHADOW');self.assertEqual(exp['validation']['invalid_records'],1)

    def test_changed_feature_schema_refuses_saved_model_predictions(self):
        exp=q.freeze_experiment(rows(),NOW);exp['feature_fingerprint']='obsolete'
        r=dict(rows()[0],opened_at=(NOW+timedelta(seconds=1)).isoformat())
        self.assertEqual(q.forecast(exp,r)['status'],'FEATURE_SCHEMA_CHANGED')

    def test_corrupt_optional_research_file_does_not_abort_monitor_startup(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'density-experiment.json').write_text('{broken')
            try:lab=q.PaperQualityLab(d)
            except (ValueError,OSError) as exc:self.fail(f'Optional research crashed startup: {exc}')
            self.assertIsNone(lab.experiment)

    def test_two_lab_instances_reuse_the_same_committed_frozen_model(self):
        with tempfile.TemporaryDirectory() as d:
            first=q.PaperQualityLab(d);second=q.PaperQualityLab(d)
            first.refresh(rows());second.refresh(rows())
            self.assertEqual(first.experiment['experiment_id'],second.experiment['experiment_id'])
            self.assertEqual(first.experiment['experiment_id'],json.loads(Path(d,'density-experiment.json').read_text())['experiment_id'])

if __name__=='__main__':unittest.main()
