"""Public website compatibility routes.

ATLAS ULTIMATE is the single human-facing entry point. Legacy public root
traffic is redirected there while private API and MT5 services remain isolated.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
CANONICAL_ATLAS_PATH = "/atlas-ultimate"
router = APIRouter(tags=["website"])


@router.get("/", include_in_schema=False)
def website() -> RedirectResponse:
    return RedirectResponse(url=CANONICAL_ATLAS_PATH, status_code=308)


@router.get("/assets/{name}", include_in_schema=False)
def website_asset(name: str):
    # Explicit public allowlist; never expose a source directory or .env.
    if name not in {"site.css", "site.js", "demo-model.js", "favicon.svg", "google-auth.js"}:
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(WEB_ROOT / "assets" / name)
