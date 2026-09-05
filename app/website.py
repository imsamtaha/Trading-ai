"""Public website served by the existing private ATLAS application.

Only web/ is included in static deployments. No private API is deployed there.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
router = APIRouter(tags=["website"])


@router.get("/", include_in_schema=False)
def website():
    return FileResponse(WEB_ROOT / "index.html")


@router.get("/assets/{name}", include_in_schema=False)
def website_asset(name: str):
    # Explicit public allowlist; never expose a source directory or .env.
    if name not in {"site.css", "site.js", "demo-model.js", "favicon.svg"}:
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(WEB_ROOT / "assets" / name)
