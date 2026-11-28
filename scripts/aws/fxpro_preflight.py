#!/usr/bin/env python3
"""Fail-closed AWS/Linux preflight; never reads or prints credential values."""
from __future__ import annotations

import argparse
import os
import sys

SAFE = {
    "ATLAS_LIVE_TRADING": "false",
    "ATLAS_ENVIRONMENT": "paper",
    "ATLAS_DASHBOARD_ONLY": "true",
    "ATLAS_AGENT_PAPER_EXECUTION_ENABLED": "false",
    "ATLAS_AUTO_EXECUTION_ENABLED": "false",
    "ATLAS_REAL_MONEY_EXECUTION": "false",
    "ATLAS_DEMO_ORDER_EXECUTION": "false",
    "ATLAS_USER_REAL_ORDERS": "false",
    "ATLAS_USER_DEMO_ORDERS": "false",
    "ATLAS_MT5_CONNECTIONS_PAUSED": "true",
}

PROFILES = {
    "demo": (
        "ATLAS_CTRADER_DEMO_LOGIN",
        "ATLAS_CTRADER_CLIENT_ID",
        "ATLAS_CTRADER_CLIENT_SECRET",
        "ATLAS_CTRADER_ACCESS_TOKEN",
        "ATLAS_PROVIDER_STATUS_TOKEN",
    ),
    "live": (
        "ATLAS_CTRADER_LIVE_LOGIN",
        "ATLAS_CTRADER_LIVE_CLIENT_ID",
        "ATLAS_CTRADER_LIVE_CLIENT_SECRET",
        "ATLAS_CTRADER_LIVE_ACCESS_TOKEN",
        "ATLAS_PROVIDER_LIVE_STATUS_TOKEN",
    ),
}


def validate(require: str = "none") -> bool:
    ok = True
    unsafe = [
        name for name, expected in SAFE.items()
        if os.getenv(name, expected).strip().lower() != expected
    ]
    if unsafe:
        print("FAIL: unsafe ATLAS settings: " + ", ".join(sorted(unsafe)))
        ok = False
    else:
        print("Safety flags: PAPER ONLY / no broker orders")

    port = os.getenv("ATLAS_FXPRO_STATUS_PORT", "8766")
    if not (port.isascii() and port.isdecimal() and len(port) < 6 and 1 <= int(port) <= 65535):
        print("FAIL: invalid ATLAS_FXPRO_STATUS_PORT")
        ok = False

    for mode, keys in PROFILES.items():
        supplied = [bool(os.getenv(key, "").strip()) for key in keys]
        login = os.getenv(keys[0], "").strip()
        if login and not (login.isascii() and login.isdecimal()):
            print(f"FAIL: {mode.upper()} login must be digits")
            ok = False

        if all(supplied):
            token = os.getenv(keys[-1], "").strip()
            if len(token) < 24:
                print(f"FAIL: {mode.upper()} status token must be at least 24 characters")
                ok = False
            print(f"{mode.upper()} view-only profile: PRESENT (authorization not verified)")
        elif any(supplied):
            print(f"FAIL: {mode.upper()} view-only profile is PARTIAL")
            ok = False
        else:
            print(f"{mode.upper()} view-only profile: NOT CONFIGURED")
            if require in (mode, "both"):
                ok = False

    demo_token = os.getenv(PROFILES["demo"][-1], "").strip()
    live_token = os.getenv(PROFILES["live"][-1], "").strip()
    if demo_token and live_token and demo_token == live_token:
        print("FAIL: DEMO and LIVE status tokens must be different")
        ok = False

    if ok:
        print("Preflight: PASS (credentials, if present, still require provider verification)")
    else:
        print("Preflight: BLOCKED; service must not start")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require", choices=("none", "demo", "live", "both"), default="none")
    args = ap.parse_args()
    return 0 if validate(args.require) else 1


if __name__ == "__main__":
    sys.exit(main())
