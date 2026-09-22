"""Public website routes for the canonical ATLAS ULTIMATE address."""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from app.dashboard import _atlas_ultimate_html

WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
router = APIRouter(tags=["website"])


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def website() -> HTMLResponse:
    """Serve ATLAS ULTIMATE directly at the domain root."""
    return HTMLResponse(_atlas_ultimate_html())


@router.get("/assets/{name}", include_in_schema=False)
def website_asset(name: str):
    # Explicit public allowlist; never expose a source directory or .env.
    if name not in {
        "site.css", "site.js", "demo-model.js", "favicon.svg", "google-auth.js",
        "atlas-brand.css", "atlas-main-logo.svg",
    }:
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(WEB_ROOT / "assets" / name)
