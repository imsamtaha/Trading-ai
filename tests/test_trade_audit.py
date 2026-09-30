from app.mt5_demo.audit import TradeAudit

def test_audit_reservation_survives_new_store_instance(tmp_path):
    path = tmp_path / "orders.sqlite3"
    first = TradeAudit(path)
    assert first.reserve("alice", "unique-request", "***1234", "DEMO", "EURUSD", "BUY", 0.01) is True
    second = TradeAudit(path)
    assert second.reserve("alice", "unique-request", "***1234", "DEMO", "EURUSD", "BUY", 0.01) is False
    second.finish("alice", "unique-request", "FILLED", 42)
    assert second.status("alice", "unique-request") == "FILLED"
