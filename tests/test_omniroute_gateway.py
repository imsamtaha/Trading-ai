"""Tests: OmniRoute never bypasses ATLAS PAPER/owner boundary."""
import io
from types import SimpleNamespace

import pytest

from app.intelligence.omniroute_gateway import OmniRouteResearchGateway


class FakeCatalog:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, limit):
        assert limit <= 128 * 1024 + 1
        return b'{"data":[{"id":"mock-model"}]}'


def _env(**kwargs):
    return {
        "ATLAS_OMNIROUTE_ENABLED": "true",
        "ATLAS_DASHBOARD_ONLY": "true",
        "ATLAS_LIVE_TRADING": "false",
        "ATLAS_REAL_MONEY_EXECUTION": "false",
        "ATLAS_OMNIROUTE_BASE_URL": "http://127.0.0.1:20128/v1",
        "ATLAS_OMNIROUTE_API_KEY": "local-test-key-never-commit",
        **kwargs,
    }


def test_off_by_default_and_never_call_network():
    gateway = OmniRouteResearchGateway(env={}, urlopen=lambda *_a, **_k: pytest.fail("network"))
    assert gateway.status()["status"] == "OMNIROUTE_DISABLED"
    assert gateway.status()["broker_execution_allowed"] is False
    assert gateway.research(symbol="XAUUSD", timeframe="15m", observations=["synthetic"])["status"] == "OMNIROUTE_DISABLED"


@pytest.mark.parametrize(
    "settings",
    [
        {"ATLAS_DASHBOARD_ONLY": "false"},
        {"ATLAS_LIVE_TRADING": "true"},
        {"ATLAS_REAL_MONEY_EXECUTION": "true"},
    ],
)
def test_not_available_in_trading_execution_mode(settings):
    state = _env(**settings)
    gateway = OmniRouteResearchGateway(env=state, urlopen=lambda *_a, **_k: pytest.fail("network"))
    assert gateway.status()["status"] == "PAPER_READ_ONLY_MODE_REQUIRED"
    assert gateway.research(symbol="XAUUSD", timeframe="15m", observations=["mock"])["broker_execution_allowed"] is False


@pytest.mark.parametrize("url", [
    "http://evil.test:20128/v1",
    "https://example.test/v1",
    "http://127.0.0.1:5000/v1",
    "http://user:pass@127.0.0.1:20128/v1",
    "http://127.0.0.1:20128/v1?key=secret",
    "http://127.0.0.1:20128/v1/chat/completions",
])
def test_rejects_non_loopback_or_unexpected_endpoint(url):
    gateway = OmniRouteResearchGateway(
        env=_env(ATLAS_OMNIROUTE_BASE_URL=url),
        urlopen=lambda *_a, **_k: pytest.fail("SSRF risk"),
    )
    assert gateway.status()["status"].startswith("OmniRoute must use")
    assert gateway.status()["broker_execution_allowed"] is False


def test_secret_key_file_used_locally_and_never_emitted(tmp_path):
    secret = "internal-key-not-for-github"
    key_file = tmp_path / "omni-secret.txt"
    key_file.write_text(secret, encoding="utf-8")
    events = []

    def fake_get(request, *, timeout):
        events.append((request.full_url, request.get_header("Authorization"), timeout))
        return FakeCatalog()

    gateway = OmniRouteResearchGateway(
        env=_env(ATLAS_OMNIROUTE_API_KEY="", ATLAS_OMNIROUTE_API_KEY_FILE=str(key_file)),
        urlopen=fake_get,
    )
    result = gateway.status()
    assert result["status"] == "READY"
    assert result["model_catalog_entries"] == 1
    assert result["transport"] == "LOCAL_ONLY"
    assert events == [("http://127.0.0.1:20128/v1/models", "Bearer " + secret, 2.5)]
    assert secret not in str(result)
    assert result["council_weights_modified"] is False


def test_missing_credentials_fail_closed_before_network(tmp_path):
    gateway = OmniRouteResearchGateway(
        env=_env(ATLAS_OMNIROUTE_API_KEY="", ATLAS_OMNIROUTE_API_KEY_FILE=str(tmp_path / "missing")),
        urlopen=lambda *_a, **_k: pytest.fail("no credentials should mean no HTTP"),
    )
    assert gateway.status()["status"] == "LOCAL_OMNIROUTE_KEY_UNAVAILABLE"


def test_research_never_calls_broker_and_closes_client():
    state = _env(ATLAS_OMNIROUTE_MODEL="auto")
    holder = {}

    class FakeClient:
        def __init__(self, **kwargs):
            holder["credentials_received"] = kwargs["api_key"]
            holder["url"] = kwargs["base_url"]
            holder["timeout"] = kwargs["timeout"]
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        @staticmethod
        def create(**kwargs):
            holder["request"] = kwargs
            return SimpleNamespace(choices=[
                SimpleNamespace(message=SimpleNamespace(content="Observed volatility with unknown data freshness."))
            ])

        def close(self):
            holder["closed"] = True

    gateway = OmniRouteResearchGateway(env=state, client_factory=FakeClient)
    result = gateway.research(
        symbol="EURUSD",
        timeframe="15m",
        observations=["Synthetic price range expanded; no live data."],
    )
    assert result["status"] == "RESEARCH_READY"
    assert result["source"] == "OMNIROUTE_LOCAL_LLM_UNVERIFIED"
    assert result["verified_market_data"] is False
    assert result["broker_execution_allowed"] is False
    assert result["council_weights_modified"] is False
    assert holder["url"] == "http://127.0.0.1:20128/v1"
    assert holder["timeout"] == 8.0
    assert holder["request"]["model"] == "auto"
    assert all(m["role"] in {"system", "user"} for m in holder["request"]["messages"])
    assert "Do not issue orders" in holder["request"]["messages"][0]["content"]
    assert holder["closed"]
    assert holder["credentials_received"] not in str(result)


def test_invalid_observations_or_symbols_rejected():
    gateway = OmniRouteResearchGateway(env=_env(), client_factory=lambda **_kw: pytest.fail("invalid input"))
    with pytest.raises(ValueError, match="symbol"):
        gateway.research(symbol="EUR/USD?token=1", timeframe="15m", observations=["mock"])
    with pytest.raises(ValueError, match="observation"):
        gateway.research(symbol="EURUSD", timeframe="15m", observations=[" "])


def test_invalid_catalog_degrades_without_exposing_response():
    class BadCatalog:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def read(self, _limit):
            return b"NOT_JSON"

    gateway = OmniRouteResearchGateway(env=_env(), urlopen=lambda *_a, **_k: BadCatalog())
    assert gateway.status()["status"] == "GATEWAY_UNREACHABLE"
