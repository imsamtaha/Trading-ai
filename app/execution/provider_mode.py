"""Broker connection selection shared by the web service and worker."""

import os


def _selected_provider() -> str:
    return os.getenv("ATLAS_BROKER_PROVIDER", "mt5").strip().lower()


def ctrader_selected() -> bool:
    return _selected_provider() == "ctrader"


def mt5_connections_paused() -> bool:
    return _selected_provider() != "mt5" or os.getenv("ATLAS_MT5_CONNECTIONS_PAUSED", "").strip().lower() == "true"
