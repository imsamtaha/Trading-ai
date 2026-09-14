from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib.parse import quote
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
CHART_URL="https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
HEADLINES_URL="https://finance.yahoo.com/rss/topstories"

def _enabled(): return os.getenv("ATLAS_MARKET_DATA_ENABLED","true").lower()=="true"
def _number(v):
    try: return float(v)
    except (TypeError,ValueError): return None
def _direction(p):
    if p is None: return "NEUTRAL"
    return "BULLISH" if p>0.15 else "BEARISH" if p<-0.15 else "NEUTRAL"
def _freshness(timestamp):
    """Classify provider quote age without treating stale data as live."""
    if not timestamp: return None,"UNKNOWN",False
    try:
        ts=datetime.fromtimestamp(float(timestamp),tz=timezone.utc)
        age=max(0,(datetime.now(timezone.utc)-ts).total_seconds())
    except (TypeError,ValueError,OverflowError): return None,"UNKNOWN",False
    fresh_limit=max(60,int(os.getenv("ATLAS_MARKET_FRESH_SECONDS","900")))
    stale_limit=max(fresh_limit,int(os.getenv("ATLAS_MARKET_STALE_SECONDS","86400")))
    state="FRESH" if age<=fresh_limit else "DELAYED" if age<=stale_limit else "STALE"
    return ts.isoformat(),state,state!="STALE"

def _arabic_headlines(stories):
    key=os.getenv("OPENAI_API_KEY","").strip()
    if not key or key=="YOUR_API_KEY_HERE" or not stories: return stories
    try:
        from openai import OpenAI
        titles=[s["title"] for s in stories]
        prompt=("You are the Arabic financial-news editor for ATLAS. Rewrite ONLY the supplied English headlines as concise, natural, professional Modern Standard Arabic suitable for a premium financial intelligence dashboard. Avoid literal or sensational phrasing. Preserve exact factual meaning, tone, numbers, percentages, currencies, company/person names, tickers and market/asset symbols; keep tickers and symbols in English. Never add facts, forecasts, trading advice, sentiment or interpretation. Return valid JSON only exactly as {\"titles\":[\"...\"]}, preserving input order and count.\nINPUT:\n"+json.dumps({"titles":titles},ensure_ascii=False))
        r=OpenAI(api_key=key).responses.create(model=os.getenv("OPENAI_MODEL","gpt-5.6"),input=prompt)
        raw=(r.output_text or "").strip()
        if raw.startswith("```"): raw=raw.strip("`").removeprefix("json").strip()
        ar=json.loads(raw).get("titles",[])
        if len(ar)!=len(stories) or not all(str(a).strip() for a in ar): return stories
        return [{**s,"title_en":s["title"],"title_ar":str(a).strip()} for s,a in zip(stories,ar)]
    except Exception: return stories

class MarketBriefingService:
    """Public market/news context isolated from all execution paths."""
    def __init__(self,session=requests,timeout=None): self.session=session; self.timeout=timeout or float(os.getenv("ATLAS_MARKET_DATA_TIMEOUT","8"))
    def _get(self,url,**kwargs):
        try:
            r=self.session.get(url,timeout=self.timeout,headers={"User-Agent":"Mozilla/5.0 ATLAS-MarketBoard/1.4","Accept":"application/json,text/xml,*/*"},**kwargs); r.raise_for_status(); return r
        except requests.RequestException as exc: raise MarketBriefingError(str(exc)) from exc
    def _chart_quote(self,symbol):
        url=CHART_URL.format(symbol=quote(symbol,safe=""))
        payload=self._get(url,params={"range":"5d","interval":"1d","includePrePost":"false","events":"div,splits"}).json()
        result=(payload.get("chart",{}).get("result") or [])
        if not result: raise MarketBriefingError(f"No chart data for {symbol}")
        item=result[0]; meta=item.get("meta",{}); price=_number(meta.get("regularMarketPrice")); previous=_number(meta.get("chartPreviousClose") or meta.get("previousClose"))
        if price is None:
            closes=((item.get("indicators",{}).get("quote") or [{}])[0].get("close") or []); valid=[_number(v) for v in closes if _number(v) is not None]; price=valid[-1] if valid else None
            if previous is None and len(valid)>1: previous=valid[-2]
        change=(price-previous) if price is not None and previous not in (None,0) else None; pct=(change/previous*100) if change is not None and previous else None
        quote_time,freshness,fresh=_freshness(meta.get("regularMarketTime"))
        return price,change,(round(pct,3) if pct is not None else None),quote_time,freshness,fresh
    def market_board(self):
        board=[]; failures=[]
        for symbol,label,category in WALL_STREET_WATCHLIST:
            try: price,change,pct,quote_time,freshness,fresh=self._chart_quote(symbol)
            except MarketBriefingError as exc: price=change=pct=quote_time=None; freshness="UNAVAILABLE"; fresh=False; failures.append(str(exc))
            available=price is not None
            board.append({"symbol":symbol,"label":label,"category":category,"price":price,"change":change,"change_percent":pct,"direction":_direction(pct) if fresh else "UNAVAILABLE","analysis":("UP" if pct>0 else "DOWN" if pct<0 else "FLAT") if pct is not None and fresh else "UNAVAILABLE","quote_time":quote_time,"freshness":freshness,"fresh":fresh,"market_state":freshness,"available":available})
        if not any(x["available"] for x in board): raise MarketBriefingError("; ".join(failures[:3]) or "Market chart data unavailable")
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
        available=[x for x in board if x["available"]]; usable=[x for x in available if x["fresh"]]; stale=len(available)-len(usable); rising=sum((x.get("change_percent") or 0)>0 for x in usable); falling=sum((x.get("change_percent") or 0)<0 for x in usable); breadth="BULLISH" if rising>falling else "BEARISH" if falling>rising else "NEUTRAL"
        status="ONLINE" if usable else "DEGRADED"
        return {"status":status,"as_of":now,"market_board":board,"market_analysis":{"breadth":breadth if usable else "UNAVAILABLE","rising":rising,"falling":falling,"tracked":len(available),"usable":len(usable),"stale":stale,"execution":"DISABLED"},"headlines":headlines,"errors":errors,"source":"Yahoo Finance public chart data and RSS","disclaimer":"Context only. Quote freshness is checked before market direction/breadth is calculated. Stale public prices are not treated as current ATLAS market context and are never used by the execution gate."}

_service=MarketBriefingService()
def get_market_briefing(): return _service.briefing()
