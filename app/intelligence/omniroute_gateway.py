"""Private local OmniRoute bridge for ATLAS research, never broker execution.

This module is opt-in and uses only an OpenAI-compatible gateway bound on the
Windows loopback interface. Credentials are read at request time from local
Windows storage or a process environment variable. No secrets enter Git.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable


DEFAULT_BASE_URL = "http://127.0.0.1:20128/v1"
MAX_GATEWAY_BODY = 128 * 1024


def _enabled(env: dict[str, str]) -> bool:
    return env.get("ATLAS_OMNIROUTE_ENABLED", "").strip().lower() == "true"


def _safe_mode(env: dict[str, str]) -> bool:
    return (
        env.get("ATLAS_DASHBOARD_ONLY", "false").strip().lower() == "true"
        and env.get("ATLAS_LIVE_TRADING", "true").strip().lower() == "false"
        and env.get("ATLAS_REAL_MONEY_EXECUTION", "false").strip().lower() != "true"
    )


def _base_url(env: dict[str, str]) -> str:
    value = env.get("ATLAS_OMNIROUTE_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
    parsed = urllib.parse.urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"localhost", "127.0.0.1"}
        or parsed.port != 20128
        or parsed.path != "/v1"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("OmniRoute must use a local HTTP endpoint at port 20128 /v1")
    return value


def _api_key(env: dict[str, str]) -> str | None:
    direct = env.get("ATLAS_OMNIROUTE_API_KEY", "").strip()
    if direct:
        return direct

    path_value = env.get("ATLAS_OMNIROUTE_API_KEY_FILE", "").strip()
    if not path_value:
        root = env.get("LOCALAPPDATA", "")
        if not root:
            return None
        path = Path(root) / "OmniRoute" / "data" / "api-key.txt"
    else:
        path = Path(path_value).expanduser()
    try:
        if not path.is_file() or path.stat().st_size > 4096:
            return None
        return path.read_text(encoding="utf-8").strip() or None
    except (OSError, UnicodeError):
        return None


class OmniRouteResearchGateway:
    """Read-only research adapter, intentionally separate from Council and MT5."""

    def __init__(
        self,
        *,
        env: dict[str, str] | None = None,
        urlopen: Callable[..., Any] | None = None,
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.env = dict(os.environ if env is None else env)
        self.urlopen = urlopen or urllib.request.urlopen
        self.client_factory = client_factory

    def _setup(self) -> tuple[str, str]:
        if not _enabled(self.env):
            raise ValueError("OMNIROUTE_DISABLED")
        if not _safe_mode(self.env):
            raise ValueError("PAPER_READ_ONLY_MODE_REQUIRED")
        url = _base_url(self.env)
        key = _api_key(self.env)
        if not key:
            raise ValueError("LOCAL_OMNIROUTE_KEY_UNAVAILABLE")
        return url, key

    def status(self) -> dict[str, Any]:
        """Get local model-catalog availability without leaking key or models."""
        try:
            url, key = self._setup()
        except ValueError as exc:
            return self._status(str(exc))

        request = urllib.request.Request(
            url + "/models",
            method="GET",
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
        )
        try:
            with self.urlopen(request, timeout=2.5) as response:
                if response.status != 200:
                    return self._status("GATEWAY_NOT_READY")
                data = response.read(MAX_GATEWAY_BODY + 1)
            if len(data) > MAX_GATEWAY_BODY:
                return self._status("INVALID_CATALOG")
            parsed = json.loads(data)
            if not isinstance(parsed, dict) or not isinstance(parsed.get("data"), list):
                return self._status("INVALID_CATALOG")
            return self._status("READY", provider_count=len(parsed["data"]))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError):
            return self._status("GATEWAY_UNREACHABLE")

    @staticmethod
    def _status(status: str, *, provider_count: int | None = None) -> dict[str, Any]:
        result = {
            "gateway": "OmniRoute",
            "status": status,
            "transport": "LOCAL_ONLY",
            "purpose": "MARKET_RESEARCH_ONLY",
            "broker_execution_allowed": False,
            "live_trading_enabled": False,
            "council_weights_modified": False,
        }
        if provider_count is not None:
            result["model_catalog_entries"] = provider_count
        return result

    def research(
        self,
        *,
        symbol: str,
        timeframe: str,
        observations: list[str],
    ) -> dict[str, Any]:
        """Generate non-executable research commentary from supplied facts only."""
        try:
            url, key = self._setup()
        except ValueError as exc:
            return self._status(str(exc))

        if not re.fullmatch(r"[A-Z0-9._-]{1,24}", symbol.upper()):
            raise ValueError("Unsupported research symbol")
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,12}", timeframe):
            raise ValueError("Unsupported timeframe")
        if not observations or len(observations) > 10:
            raise ValueError("1-10 factual market observations required")
        observations = [x.strip() for x in observations]
        if any(not x or len(x) > 400 for x in observations):
            raise ValueError("Each market observation must contain 1-400 characters")

        # Models can be expensive; never silently route by provider auto-execution.
        model = self.env.get("ATLAS_OMNIROUTE_MODEL", "auto").strip()
        if not re.fullmatch(r"[a-zA-Z0-9._:/-]{1,100}", model):
            return self._status("MODEL_NOT_CONFIGURED")

        if self.client_factory is None:
            from openai import OpenAI
            factory = OpenAI
        else:
            factory = self.client_factory

        client = None
        try:
            client = factory(api_key=key, base_url=url, timeout=8.0, max_retries=0)
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                max_tokens=300,
                messages=[
                    {"role": "system", "content": (
                        "You are a non-executing ATLAS educational market research "
                        "summarizer. Only describe the provided observations, "
                        "uncertainties and missing evidence. Do not issue orders, "
                        "buy/sell recommendations, targets, financial promises, "
                        "account instructions or position sizes. Do not claim "
                        "to have live or verified market data. Keep it concise."
                    )},
                    {"role": "user", "content": json.dumps({
                        "symbol": symbol.upper(),
                        "timeframe": timeframe,
                        "supplied_observations": observations,
                    }, ensure_ascii=False)},
                ],
            )
            content = response.choices[0].message.content
            if not isinstance(content, str) or not content.strip():
                return self._status("EMPTY_RESEARCH_RESPONSE")
            return {
                **self._status("RESEARCH_READY"),
                "symbol": symbol.upper(),
                "timeframe": timeframe,
                "analysis": content[:2000],
                "source": "OMNIROUTE_LOCAL_LLM_UNVERIFIED",
                "verified_market_data": False,
            }
        except Exception:
            # Avoid propagating provider error strings which may include credentials.
            return self._status("GATEWAY_RESEARCH_FAILED")
        finally:
            if client is not None:
                client.close()
