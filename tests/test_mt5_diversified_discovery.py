from unittest.mock import Mock
from app.monitor.atlas_mt5 import AtlasMT5Monitor

def test_diversified_discovery(monkeypatch):
    monkeypatch.delenv("ATLAS_PREFERRED_CANONICAL", raising=False)
    m = AtlasMT5Monitor(symbols=[], top_n=12)
    def s(name,bid,ask):
        return {"symbol":name,"bid":bid,"ask":ask,"point":0.01,"tradeable":True,"visible":True}
    m.broker.symbols = Mock(return_value=[
        s("XAUUSDm",3600,3600.2),
        s("NGASm",3,3.001),
        s("EURUSD.fx",1.1,1.10005),
        s("NAS100.cash",25000,25001),
        s("BTCUSDm",100000,100010),
        s("WHEAT.cash",600,600.1),
    ])
    found = set(m.discover_symbols())
    assert found == {"XAUUSDm","NGASm","EURUSD.fx","NAS100.cash","BTCUSDm","WHEAT.cash"}
    assert {x["asset_class"] for x in m.universe} == {"METALS","ENERGY","FOREX","INDICES","CRYPTO","COMMODITIES"}
