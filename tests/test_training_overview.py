import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone

SOURCE=Path(__file__).resolve().parents[1]/"runtime/private-api/app/runtime_control/training.py"
spec=importlib.util.spec_from_file_location("atlas_training_overview", SOURCE)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class TrainingOverviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.paper=self.root/".runtime/paper"
        self.paper.mkdir(parents=True)
    def tearDown(self): self.tmp.cleanup()
    def write(self,name,data):
        (self.paper/name).write_text(json.dumps(data),encoding="utf-8")
    def test_daily_and_mixed_qualification_reasons(self):
        self.assertEqual(module.rejection_category("Maximum daily paper entries reached (100)."),"DAILY_LIMIT")
        self.assertEqual(module.rejection_category("Candidate failed confidence or risk qualification."),"OTHER")
    def test_missing_is_unavailable_not_zero(self):
        result=module.training_overview(self.root)
        self.assertIsNone(result["portfolio"])
        self.assertIsNone(result["selector"])
        self.assertIn("ledger",result["unavailable"])
    def test_unique_closed_future_excluded_and_utc_entries(self):
        rows=[{"id":"one","status":"CLOSED","opened_at":"2026-10-08T22:00:00+00:00","closed_at":"2026-10-08T22:10:00+00:00","symbol":"BTCUSD","r_multiple":2}]
        self.write("atlas_demo_ledger.json",{"closed_trades":rows+rows+[dict(rows[0],id="future",closed_at="2026-10-09T22:10:00+00:00")],"open_positions":[]})
        r=module.training_overview(self.root,datetime(2026,10,8,23,tzinfo=timezone.utc))
        self.assertEqual(r["portfolio"]["closed"],1)
        self.assertEqual(r["portfolio"]["entries_today_utc"],1)
        self.assertEqual(r["asset_classes"][0]["sum_r"],2)
        self.assertEqual(r["portfolio"]["excluded_records"],2)
    def test_number_gate_does_not_claim_ready_before_third_day(self):
        self.write("atlas_shadow_report.json",{"mode":"SHADOW","generated_at":"2026-10-08T22:00:00+00:00","samples":106,"independent_days":2,"minimum_samples":100,"minimum_days":3,"status":"INSUFFICIENT_DATA","broker_execution_allowed":False})
        r=module.training_overview(self.root,datetime(2026,10,8,23,tzinfo=timezone.utc))
        self.assertFalse(r["selector"]["data_gates_met"])
        self.assertEqual(r["selector"]["days"],2)
    def test_only_safe_aggregates_leave_server(self):
        self.write("atlas_council_profile.json",{"generated_at":"2026-10-08T22:00:00+00:00","training_environment":"PAPER","broker_execution_allowed":False,"agents":{"technical":{"weight":0.9,"brier_score":0.4,"samples":10,"secret":"should-never-leave"}}})
        r=module.training_overview(self.root)
        self.assertNotIn("secret",json.dumps(r))
        self.assertIsNone(r["agents"][0]["weight_change"])
    def test_rejection_counts_are_recent_events_not_unique_trades(self):
        d=self.root/"data";d.mkdir()
        events=[{"timestamp":"2026-10-08T22:59:00+00:00","status":"NO_TRADE","reason":"CRYPTO concentration limit reached."},{"timestamp":"2026-10-08T22:59:01+00:00","status":"MT5_ERROR","reason":"Maximum open paper positions reached (5)."},{"timestamp":"2026-10-08T22:59:02+00:00","status":"OPENED","reason":"secret-account"}]
        (d/"atlas_signals.jsonl").write_text("\n".join(map(json.dumps,events))+"\n")
        r=module.training_overview(self.root,datetime(2026,10,8,23,tzinfo=timezone.utc))
        self.assertEqual(r["rejections"]["total"],2)
        self.assertNotIn("secret-account",json.dumps(r))
        self.assertEqual({x["category"] for x in r["rejections"]["counts"]},{"CONCENTRATION","OPEN_LIMIT"})

if __name__=="__main__": unittest.main()
