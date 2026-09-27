"""Bounded, read-only educational assistant for authenticated users."""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque

from openai import OpenAI

_lock = threading.Lock()
_recent: dict[str, deque[float]] = defaultdict(deque)


class AssistantUnavailable(Exception):
    pass


class AssistantRateLimited(Exception):
    pass


def _client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise AssistantUnavailable("Assistant is not configured.")
    return OpenAI(api_key=key, timeout=15.0, max_retries=0)

def answer_assistant(user_id: str, message: str) -> str:
    now = time.monotonic()
    with _lock:
        recent = _recent[user_id]
        while recent and now - recent[0] >= 60:
            recent.popleft()
        if len(recent) >= 6:
            raise AssistantRateLimited()
        recent.append(now)
    try:
        result = _client().responses.create(
            model=os.getenv("ATLAS_ASSISTANT_MODEL", "gpt-4.1-mini"),
            instructions=(
                "You are ATLAS, an educational trading assistant. Answer concisely in the user's language. "
                "Never claim access to live prices, balances, positions, private account data, or execution. "
                "Do not place trades, promise returns, or give personalized buy/sell instructions. "
                "Explain uncertainty and risk when relevant."
            ),
            input=message,
            max_output_tokens=300,
            store=False,
        )
        answer = result.output_text.strip()
        if not answer:
            raise AssistantUnavailable("Assistant returned no answer.")
        return answer
    except AssistantUnavailable:
        raise
    except Exception as exc:
        raise AssistantUnavailable("Assistant is temporarily unavailable.") from exc
