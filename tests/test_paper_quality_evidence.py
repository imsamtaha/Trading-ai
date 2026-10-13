import tempfile
import unittest
import inspect
from pathlib import Path
from app.paper_trading.mt5_ledger import MT5PaperLedger

class EvidenceTests(unittest.TestCase):
    def test_entry_and_exit_quotes_and_card_remain_in_settled_ledger(self):
        self.assertIn('entry_quote',inspect.signature(MT5PaperLedger.open_trade).parameters,'Entry execution evidence is missing')
        with tempfile.TemporaryDirectory() as d:
            ledger=MT5PaperLedger(Path(d)/'ledger.json')
            trade=ledger.open_trade(symbol='TEST',direction='LONG',entry=100,stop_loss=99,take_profit=102,position_size=1,risk={'actual_risk_amount':1,'risk_reward':2},strategy='TEST',confidence=80,timeframe='5m',decision={'decision':'BUY'},entry_quote={'bid':99.9,'ask':100,'time':1000},quality_card={'score':None})
            self.assertEqual(trade['quality_card']['trade_id'],trade['id'])
            closed=ledger.close_due_positions('TEST',bid=98.5,ask=98.6,quote_evidence={'bid':98.5,'ask':98.6,'time':1001})[0]
            self.assertEqual(closed['entry_quote']['ask'],100)
            self.assertEqual(closed['exit_quote']['time'],1001)
            self.assertEqual(closed['r_multiple'],-1.5)
            reloaded=MT5PaperLedger(Path(d)/'ledger.json').closed_trades()[0]
            self.assertEqual(reloaded['quality_card']['trade_id'],trade['id'])

if __name__=='__main__':unittest.main()
