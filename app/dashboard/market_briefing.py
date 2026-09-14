from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree

import requests

class MarketBriefingError(RuntimeError): pass

WALL_STREET_WATCHLIST = (
    ("^DJI", "Dow Jones", "US Equities"), ("^GSPC", "S&P 500", "US Equities"),
    ("^IXIC", "Nasdaq Composite", "US Equities"), ("^VIX", "CBOE VIX", "Volatility"),
    ("GC=F", "Gold Futures", "Commodities"), ("SI=F", "Silver Futures", "Commodities"),
    ("CL=F", "WTI Crude", "Commodities"), ("NG=F", "Natural Gas", "Commodities"),
    ("EURUSD=X", "EUR/USD", "FX"), ("BTC-USD", "Bitcoin", "Digital Assets"),
)
QUOTE_URL="https://query1.finance.yahoo.com/v7/finance/quote"
HEADLINES_URL="https://finance.yahoo.com/rss/topstories"

def _enabled(): return os.getenv("ATLAS_MARKET_DATA_ENABLED","true").lower()=="true"
def _number(v):
    try: return float(v)
    except (TypeError,ValueError): return None
def _direction(p):
    if p is None: return "NEUTRAL"
    return "BULLISH" if p>0.15 else "BEARISH" if p<-0.15 else "NEUTRAL"

def _arabic_headlines(stories):
    """Localize financial headlines into natural professional MSA without changing facts."""
    key=os.getenv("OPENAI_API_KEY","").strip()
    if not key or key=="YOUR_API_KEY_HERE" or not stories: return stories
    try:
        from openai import OpenAI
        titles=[s["title"] for s in stories]
        prompt=(
            "You are the Arabic financial-news editor for ATLAS. Rewrite ONLY the supplied English "
            "headlines as concise, natural, professional Modern Standard Arabic suitable for a premium "
            "financial intelligence dashboard. Do not translate literally. Preserve the exact factual "
            "meaning, tone, numbers, percentages, currencies, company/person names, tickers and market/asset "
            "symbols; keep tickers and symbols such as NVDA, EURUSD, XAUUSD and BTCUSD in English. Never add "
            "facts, forecasts, trading advice, sentiment or interpretation. Prefer standard financial Arabic "
            "such as يرتفع/يتراجع, وسط ترقب, آفاق التضخم, تقييمات السوق, and نمو الذكاء الاصطناعي when those "
            "meanings are actually present. Avoid awkward word-for-word phrasing. Return valid JSON only, "
            "exactly as {\"titles\":[\"...\"]}, preserving input order and count.\n\nINPUT:\n" +
            json.dumps({"titles":titles},ensure_ascii=False)
        )
        r=OpenAI(api_key=key).responses.create(
            model=os.getenv("OPENAI_MODEL","gpt-5.6"),
            input=prompt,
        )
        raw=(r.output_text or "").strip()
        if raw.startswith("```"):
            raw=raw.strip("`").removeprefix("json").strip()
        ar=json.loads(raw).get("titles",[])
        if len(ar)!=len(stories) or not all(str(a).strip() for a in ar): return stories
        return [{**s,"title_en":s["title"],"title_ar":str(a).strip()} for s,a in zip(stories,ar)]
    except Exception:
        return stories

class MarketBriefingService:
    """Public market/news analysis that remains isolated from execution."""
    def __init__(self,session=requests,timeout=None): self.session=session; self.timeout=timeout or float(os.getenv("ATLAS_MARKET_DATA_TIMEOUT","8"))
    def _get(self,url,**kwargs):
        try:
            r=self.session.get(url,timeout=self.timeout,headers={"User-Agent":"ATLAS-MarketBoard/1.2"},**kwargs); r.raise_for_status(); return r
        except requests.RequestException as exc: raise MarketBriefingError(str(exc)) from exc
    def market_board(self):
        payload=self._get(QUOTE_URL,params={"symbols":",".join(s for s,_,_ in WALL_STREET_WATCHLIST)}).json()
        by={str(x.get("symbol","")):x for x in payload.get("quoteResponse",{}).get("result",[])}; board=[]
        for symbol,label,category in WALL_STREET_WATCHLIST:
            q=by.get(symbol,{}); price=_number(q.get("regularMarketPrice")); change=_number(q.get("regularMarketChange")); pct=_number(q.get("regularMarketChangePercent")); pct=round(pct,3) if pct is not None else None
            board.append({"symbol":symbol,"label":label,"category":category,"price":price,"change":change,"change_percent":pct,"direction":_direction(pct),"analysis":"UP" if pct is not None and pct>0 else "DOWN" if pct is not None and pct<0 else "FLAT","market_state":q.get("marketState","UNKNOWN"),"available":price is not None})
        return board
    def headlines(self,limit=6):
        response=self._get(HEADLINES_URL)
        try: root=ElementTree.fromstring(response.content)
        except ElementTree.ParseError as exc: raise MarketBriefingError("Market headline feed returned invalid XML.") from exc
        stories=[]
        for item in root.iter():
            if item.tag.rsplit("}",1)[-1]!="item": continue
            v={c.tag.rsplit("}",1)[-1]:(c.text or "").strip() for c in item}
            if v.get("title"): stories.append({"title":v["title"],"url":v.get("link",""),"published_at":v.get("pubDate",""),"source":"Yahoo Finance"})
            if len(stories)>=max(1,min(20,limit)): break
        return _arabic_headlines(stories)
    def briefing(self):
        now=datetime.now(timezone.utc).isoformat()
        if not _enabled(): return {"status":"DISABLED","as_of":now,"market_board":[],"headlines":[],"errors":[],"disclaimer":"Public market context is disabled."}
        errors=[]
        try: board=self.market_board()
        except MarketBriefingError as exc: board=[]; errors.append("market_board: "+str(exc))
        try: headlines=self.headlines()
        except MarketBriefingError as exc: headlines=[]; errors.append("headlines: "+str(exc))
        available=[x for x in board if x["available"]]; rising=sum((x.get("change_percent") or 0)>0 for x in available); falling=sum((x.get("change_percent") or 0)<0 for x in available); breadth="BULLISH" if rising>falling else "BEARISH" if falling>rising else "NEUTRAL"
        return {"status":"ONLINE" if board else "DEGRADED","as_of":now,"market_board":board,"market_analysis":{"breadth":breadth,"rising":rising,"falling":falling,"tracked":len(available),"execution":"DISABLED"},"headlines":headlines,"errors":errors,"source":"Yahoo Finance public market data and RSS","disclaimer":"Context only. Public prices, deterministic direction labels and headlines are not ATLAS execution signals and are never used by the execution gate."}

_service=MarketBriefingService()
def get_market_briefing(): return _service.briefing()
