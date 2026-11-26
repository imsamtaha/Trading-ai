"""Service entry and the public Council reference."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
router = APIRouter(tags=["website"])


@router.get("/", include_in_schema=False)
def service_entry():
    return {"service": "ATLAS Intelligence", "api": "/api", "health": "/health"}


@router.api_route("/centers", methods=["GET", "HEAD"], include_in_schema=False)
@router.api_route("/centers/", methods=["GET", "HEAD"], include_in_schema=False)
@router.api_route("/traders", methods=["GET", "HEAD"], include_in_schema=False)
@router.api_route("/traders/", methods=["GET", "HEAD"], include_in_schema=False)
@router.api_route("/dashboard", methods=["GET", "HEAD"], include_in_schema=False)
@router.api_route("/dashboard/", methods=["GET", "HEAD"], include_in_schema=False)
@router.api_route("/atlas-ultimate", methods=["GET", "HEAD"], include_in_schema=False)
def retired_dashboard():
    return Response(status_code=410, headers={"Cache-Control": "no-store"})


@router.get("/council/btc-2026-08-31.html", include_in_schema=False)
def historical_council_exercise():
    return FileResponse(WEB_ROOT / "council" / "btc-2026-08-31.html")


@router.get("/assets/{name}", include_in_schema=False)
def website_asset(name: str):
    if name not in {"google-auth.js", "atlas-market.css", "just-ai-intelligence-mark.webp"}:
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(WEB_ROOT / "assets" / name)
