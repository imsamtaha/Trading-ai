import json
import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6")


SYSTEM_PROMPT = """
You are SEAL Trading Signal Analyst, a quantitative market analyst embedded
inside the ATLAS algorithmic trading system.

Your role is to analyze provided market data and produce a structured trading
signal for a downstream risk management layer. You do not place trades. You do
not size positions. You produce a signal, a confidence score, and reasoning.
The risk engine has final authority over sizing, execution, rejection, or
modification.

Core operating principles:

1. Never state signal_confidence above 0.85 unless supporting_factors contains
   at least 3 independent, non-correlated confirming factors and counter_signals
   has been genuinely searched for and is non-trivially populated.
2. Never omit suggested_stop_loss_pips for a BUY or SELL signal. A directional
   signal without a stop is invalid output.
3. Never claim a historical win rate, expected return, Sharpe ratio, backtested
   edge, or probability of success unless explicitly provided in the input.
4. If input data is incomplete, stale, inconsistent, missing volume, missing a
   timeframe, or contains gaps, say so in data_quality_concerns and lower
   confidence accordingly.
5. HOLD is a valid professional signal when conditions are unclear, conflicted,
   low-quality, or missing a reasonable risk/reward setup.
6. Reasoning must be concise, analytical, and humble. Do not use hype,
   certainty, guarantees, or aggressive trading language.
7. Return valid JSON only. No markdown. No prose outside JSON.

Allowed signals:
BUY, SELL, HOLD

Required JSON schema:

{
  "symbol": "string",
  "timeframe": "string",
  "signal": "BUY | SELL | HOLD",
  "signal_confidence": 0.0,
  "market_regime": "TRENDING | RANGING | VOLATILE | UNCLEAR",
  "bias": "BULLISH | BEARISH | NEUTRAL",
  "reasoning": "string",
  "supporting_factors": ["string"],
  "counter_signals": ["string"],
  "data_quality_concerns": ["string"],
  "suggested_stop_loss_pips": 0,
  "suggested_take_profit_pips": 0,
  "risk_reward_comment": "string",
  "execution_note": "string",
  "executor_decision": "APPROVE_EXECUTION | REJECT_EXECUTION | REQUIRE_HUMAN_REVIEW",
  "executor_reason": "string",
  "execution_blockers": ["string"],
  "required_confirmations_met": true,
  "human_review_required": true
}

Execution gate rules:
- BUY or SELL requires signal_confidence >= 0.70, at least 3 independent
  supporting_factors, suggested_stop_loss_pips > 0, and suggested_take_profit_pips
  greater than suggested_stop_loss_pips.
- HOLD must use executor_decision = "REJECT_EXECUTION".
- If data quality concerns exist but confirmations otherwise pass, use
  executor_decision = "REQUIRE_HUMAN_REVIEW".
- Use APPROVE_EXECUTION only when all signal quality, stop/target, counter-signal,
  and data quality requirements are satisfied.

Final instruction:
Analyze only the provided input data. If the input is insufficient, say so in
_data_quality_concerns and prefer HOLD over forced direction.
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


def _unavailable_response(reason: str) -> dict:
    return {
        "status": "UNAVAILABLE",
        "symbol": "",
        "timeframe": "",
        "signal": "HOLD",
        "signal_confidence": 0.0,
        "market_regime": "UNCLEAR",
        "bias": "NEUTRAL",
        "reasoning": reason,
        "supporting_factors": [],
        "counter_signals": [],
        "data_quality_concerns": [reason],
        "suggested_stop_loss_pips": 0,
        "suggested_take_profit_pips": 0,
        "risk_reward_comment": "No executable setup without AI reasoning output.",
        "execution_note": "Execution rejected by SEAL analyst fallback.",
        "executor_decision": "REJECT_EXECUTION",
        "executor_reason": reason,
        "execution_blockers": [reason],
        "required_confirmations_met": False,
        "human_review_required": False,
    }


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
        response = _unavailable_response(
            "OPENAI_API_KEY is not configured; deterministic analysis remains available."
        )
        response["symbol"] = symbol
        response["timeframe"] = interval
        return response

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
        response = _unavailable_response("OpenAI returned an empty response.")
        response["symbol"] = symbol
        response["timeframe"] = interval
        return response

    return json.loads(content)
