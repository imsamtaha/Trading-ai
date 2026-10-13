from datetime import datetime,timezone
from test_atlas_mt5_council_training import _monitor,_candidate,_decision,_fresh_quote


def test_malformed_optional_quality_context_preserves_existing_paper_gates(tmp_path,monkeypatch):
    monkeypatch.setenv('ATLAS_PAPER_QUALITY_DIR',str(tmp_path/'quality'))
    monitor=_monitor(tmp_path,monkeypatch)
    monkeypatch.setattr(monitor.broker,'quote',lambda symbol:_fresh_quote())
    try:
        result=monitor._open_paper_trade(timestamp=datetime.now(timezone.utc).isoformat(),symbol='EURUSD',candidate=_candidate(),decision=_decision(),quality_context={'technical':'malformed'})
    except (ValueError,TypeError,AttributeError) as exc:
        assert False,f'Optional research stopped approved paper entry: {exc}'
    assert result['status']=='PAPER_TRADE_OPENED'
    assert result['trade']['quality_card']['status']=='QUALITY_EVIDENCE_UNAVAILABLE'
    assert result['trade_intent']['broker_execution_allowed'] is False


def test_corrupt_optional_research_manifest_preserves_monitor_startup(tmp_path,monkeypatch):
    directory=tmp_path/'quality';directory.mkdir();(directory/'density-experiment.json').write_text('{broken')
    monkeypatch.setenv('ATLAS_PAPER_QUALITY_DIR',str(directory))
    try:monitor=_monitor(tmp_path,monkeypatch)
    except (ValueError,OSError) as exc:assert False,f'Optional research stopped monitor startup: {exc}'
    assert monitor.quality_lab.experiment is None

