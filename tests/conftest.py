"""Keep the legacy broker tests on their explicitly selected test provider."""

import os

import pytest


@pytest.fixture(autouse=True)
def legacy_test_provider(monkeypatch):
    # Existing tests exercise the MT5 compatibility path with mocked brokers.
    if "ATLAS_BROKER_PROVIDER" not in os.environ:
        monkeypatch.setenv("ATLAS_BROKER_PROVIDER", "mt5")
    if "ATLAS_MT5_CONNECTIONS_PAUSED" not in os.environ:
        monkeypatch.setenv("ATLAS_MT5_CONNECTIONS_PAUSED", "false")
