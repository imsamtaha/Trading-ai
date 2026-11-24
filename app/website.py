"""Public website routes for the canonical ATLAS ULTIMATE address."""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.dashboard import _atlas_ultimate_html

WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
router = APIRouter(tags=["website"])


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def website() -> HTMLResponse:
    """Serve ATLAS ULTIMATE directly at the domain root."""
    return HTMLResponse(_atlas_ultimate_html())


@router.get("/centers", include_in_schema=False)
@router.get("/centers/", include_in_schema=False)
def centers_hub():
    """Standalone read-only navigation hub; destination access stays independently protected."""
    return FileResponse(WEB_ROOT / "centers" / "index.html")


@router.get("/traders", include_in_schema=False)
@router.get("/traders/", include_in_schema=False)
def traders_market_redirect():
    return RedirectResponse("/#market-analysis", status_code=308)


@router.get("/council/btc-2026-08-31.html", include_in_schema=False)
def historical_council_exercise():
    return FileResponse(WEB_ROOT / "council" / "btc-2026-08-31.html")


@router.get("/assets/{name}", include_in_schema=False)
def website_asset(name: str):
    # Explicit public allowlist; never expose a source directory or .env.
    if name not in {
        "site.css", "centers.css", "site.js", "demo-model.js", "favicon.svg", "google-auth.js",
        "atlas-brand.css", "atlas-main-logo.svg", "atlas-news.js",
        "atlas-market.css", "atlas-market.js", "atlas-tiger.webp", "atlas-tiger-small.webp",
        "just-ai-brand.css", "just-ai-icon.webp", "just-ai-reference.webp",
        "just-ai-intelligence.webp", "just-ai-intelligence-mark.webp",
    }:
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(WEB_ROOT / "assets" / name)

