import json
import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6")


SYSTEM_PROMPT = """
You are the AI reasoning layer of a professional market-analysis
and paper-trading system.

You analyze structured market data provided by deterministic
software components.

You must:

1. Never invent market data.
2. Never invent news.
3. Never claim certainty.
4. Never guarantee profit.
5. Never describe a confidence score as a guaranteed probability.
6. Consider both bullish and bearish scenarios.
7. Respect the existing risk-engine decision.
8. Prefer WAIT when evidence is insufficient.
9. Explain the most important evidence concisely.
10. Treat the output as paper-trading analysis.

Return valid JSON only with:

{
  "market_bias": "BULLISH | BEARISH | NEUTRAL",
  "decision": "LONG | SHORT | WAIT",
  "confidence": 0,
  "bull_case": "...",
  "bear_case": "...",
  "key_evidence": [],
  "key_risks": [],
  "reasoning": "...",
  "recommendation": "..."
}
"""


def _openai_client() -> OpenAI | None:
    """Create the OpenAI client lazily.

    The API must still start when OPENAI_API_KEY is absent so health,
    dashboard, MT5 read-only state, and deterministic analysis remain usable.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        return None
    return OpenAI(api_key=api_key)


def analyze_market(
    symbol: str,
    interval: str,
    technical: dict,
    structure: dict,
    signal: dict,
    trade: dict,
) -> dict:
    client = _openai_client()
    if client is None:
        return {
            "status": "UNAVAILABLE",
            "market_bias": "NEUTRAL",
            "decision": "WAIT",
            "confidence": 0,
            "bull_case": "",
            "bear_case": "",
            "key_evidence": [],
            "key_risks": ["OPENAI_API_KEY is not configured."],
            "reasoning": "AI reasoning is disabled; deterministic analysis remains available.",
            "recommendation": "WAIT",
        }

    market_context = {
        "symbol": symbol,
        "interval": interval,
        "technical": technical,
        "structure": structure,
        "signal": signal,
        "risk_assessment": trade,
    }

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": json.dumps(
                    market_context,
                    separators=(",", ":"),
                ),
            },
        ],
    )

    content = response.choices[0].message.content
    if not content:
        return {
            "status": "UNAVAILABLE",
            "market_bias": "NEUTRAL",
            "decision": "WAIT",
            "confidence": 0,
            "bull_case": "",
            "bear_case": "",
            "key_evidence": [],
            "key_risks": ["OpenAI returned an empty response."],
            "reasoning": "No AI analysis was produced.",
            "recommendation": "WAIT",
        }

    return json.loads(content)
