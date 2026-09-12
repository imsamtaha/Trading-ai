from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree

import requests


class MarketBriefingError(RuntimeError):
    pass


WALL_STREET_WATCHLIST = (
    ("^DJI", "Dow Jones", "US Equities"), ("^GSPC", "S&P 500", "US Equities"),
    ("^IXIC", "Nasdaq Composite", "US Equities"), ("^VIX", "CBOE VIX", "Volatility"),
    ("GC=F", "Gold Futures", "Commodities"), ("SI=F", "Silver Futures", "Commodities"),
    ("CL=F", "WTI Crude", "Commodities"), ("NG=F", "Natural Gas", "Commodities"),
    ("EURUSD=X", "EUR/USD", "FX"), ("BTC-USD", "Bitcoin", "Digital Assets"),
)
QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
HEADLINES_URL = "https://finance.yahoo.com/rss/topstories"


def _enabled() -> bool:
    return os.getenv("ATLAS_MARKET_DATA_ENABLED", "true").lower() == "true"


def _number(value: Any) -> float | None:
    try: return float(value)
    except (TypeError, ValueError): return None


def _direction(change_pct: float | None) -> str:
    if change_pct is None: return "NEUTRAL"
    if change_pct > 0.15: return "BULLISH"
    if change_pct < -0.15: return "BEARISH"
    return "NEUTRAL"


def _arabic_headlines(stories: list[dict[str, str]]) -> list[dict[str, str]]:
    """Translate/summarize fetched headlines into formal Arabic when OpenAI is configured.

    Original title/url/source are always preserved. Failure never blocks the news board.
    """
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key or key == "YOUR_API_KEY_HERE" or not stories:
        return stories
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        titles = [s["title"] for s in stories]
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5.6"), temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role":"system","content":"Translate only the supplied financial-news headlines into concise Modern Standard Arabic. Do not add facts, predictions, advice, or numbers. Preserve company names, market symbols and asset symbols in English. Return JSON exactly as {\"titles\":[...]} in the same order."},
                {"role":"user","content":json.dumps({"titles":titles}, ensure_ascii=False)},
            ],
        )
        payload = json.loads(response.choices[0].message.content or "{}")
        translated = payload.get("titles", [])
        if len(translated) != len(stories): return stories
        return [{**s, "title_ar": str(ar), "original_title": s["title"]} for s, ar in zip(stories, translated)]
    except Exception:
        return stories


class MarketBriefingService:
    """Public market context and deterministic direction analysis; no execution path."""
    def __init__(self, session: Any = requests, timeout: float | None = None):
        self.session=session; self.timeout=timeout or float(os.getenv("ATLAS_MARKET_DATA_TIMEOUT", "8"))

    def _get(self, url: str, **kwargs: Any) -> Any:
        try:
            response=self.session.get(url, timeout=self.timeout, headers={"User-Agent":"ATLAS-MarketBoard/1.1"}, **kwargs)
            response.raise_for_status(); return response
        except requests.RequestException as exc: raise MarketBriefingError(str(exc)) from exc

    def market_board(self) -> list[dict[str, Any]]:
        symbols=",".join(s for s,_,_ in WALL_STREET_WATCHLIST)
        payload=self._get(QUOTE_URL, params={"symbols":symbols}).json()
        quotes=payload.get("quoteResponse",{}).get("result",[]); by_symbol={str(x.get("symbol","")):x for x in quotes}
        board=[]
        for symbol,label,category in WALL_STREET_WATCHLIST:
            q=by_symbol.get(symbol,{}); price=_number(q.get("regularMarketPrice")); change=_number(q.get("regularMarketChange")); pct=_number(q.get("regularMarketChangePercent")); pct=round(pct,3) if pct is not None else None
            board.append({"symbol":symbol,"label":label,"category":category,"price":price,"change":change,"change_percent":pct,"direction":_direction(pct),"analysis":"UP" if pct is not None and pct>0 else "DOWN" if pct is not None and pct<0 else "FLAT","market_state":q.get("marketState","UNKNOWN"),"available":price is not None})
        return board

    def headlines(self, limit: int = 6) -> list[dict[str,str]]:
        response=self._get(HEADLINES_URL)
        try: root=ElementTree.fromstring(response.content)
        except ElementTree.ParseError as exc: raise MarketBriefingError("Market headline feed returned invalid XML.") from exc
        stories=[]
        for item in root.iter():
            if item.tag.rsplit("}",1)[-1] != "item": continue
            values={c.tag.rsplit("}",1)[-1]:(c.text or "").strip() for c in item}
            if values.get("title"): stories.append({"title":values["title"],"url":values.get("link",""),"published_at":values.get("pubDate",""),"source":"Yahoo Finance"})
            if len(stories)>=max(1,min(20,limit)): break
        return _arabic_headlines(stories)

    def briefing(self) -> dict[str,Any]:
        now=datetime.now(timezone.utc).isoformat()
        if not _enabled(): return {"status":"DISABLED","as_of":now,"market_board":[],"headlines":[],"errors":[],"disclaimer":"Public market context is disabled."}
        errors=[]
        try: board=self.market_board()
        except MarketBriefingError as exc: board=[]; errors.append("market_board: "+str(exc))
        try: headlines=self.headlines()
        except MarketBriefingError as exc: headlines=[]; errors.append("headlines: "+str(exc))
        available=[x for x in board if x["available"]]; rising=sum((x.get("change_percent") or 0)>0 for x in available); falling=sum((x.get("change_percent") or 0)<0 for x in available)
        breadth="BULLISH" if rising>falling else "BEARISH" if falling>rising else "NEUTRAL"
        return {"status":"ONLINE" if board else "DEGRADED","as_of":now,"market_board":board,"market_analysis":{"breadth":breadth,"rising":rising,"falling":falling,"tracked":len(available),"execution":"DISABLED"},"headlines":headlines,"errors":errors,"source":"Yahoo Finance public market data and RSS","disclaimer":"Context only. Public prices, deterministic direction labels and headlines are not ATLAS execution signals."}

_service=MarketBriefingService()
def get_market_briefing() -> dict[str,Any]: return _service.briefing()
