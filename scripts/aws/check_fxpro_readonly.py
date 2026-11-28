#!/usr/bin/env python3
"""Verify localhost FxPro statuses without logging balances or credentials."""
from __future__ import annotations
import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

PROFILES = {
    "demo": ("ATLAS_PROVIDER_STATUS_TOKEN", "DEMO", "/status/ctrader/demo"),
    "live": ("ATLAS_PROVIDER_LIVE_STATUS_TOKEN", "LIVE", "/status/ctrader/live"),
}

def check(mode: str) -> bool:
    token_key, environment, path = PROFILES[mode]
    token = os.getenv(token_key, "").strip()
    if not token:
        print(f"{environment}: NOT CONFIGURED (missing private status token)")
        return False
    port = os.getenv("ATLAS_FXPRO_STATUS_PORT", "8766")
    if not (port.isascii() and port.isdecimal() and len(port) < 6 and 1 <= int(port) <= 65535):
        print(f"{environment}: invalid local status port")
        return False
    request = Request(
        f"http://127.0.0.1:{port}{path}",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with build_opener(ProxyHandler({})).open(request, timeout=12) as response:
            data = json.load(response)
    except HTTPError as exc:
        print(f"{environment}: UNAVAILABLE (HTTP {exc.code})")
        return False
    except (URLError, OSError, ValueError, TimeoutError):
        print(f"{environment}: UNAVAILABLE (status service not reachable)")
        return False
    if (
        isinstance(data, dict)
        and data.get("status") == "CONNECTED"
        and data.get("environment") == environment
        and data.get("access") == "READ_ONLY"
        and data.get("brokerOrders") is False
    ):
        print(f"{environment}: CONNECTED / READ_ONLY / NO BROKER ORDERS")
        return True
    print(f"{environment}: BLOCKED (status response failed safety checks)")
    return False

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("demo", "live", "both"), default="both")
    mode = parser.parse_args().mode
    modes = ("demo", "live") if mode == "both" else (mode,)
    results = [check(item) for item in modes]
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
