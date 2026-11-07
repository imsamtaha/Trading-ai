"""Read-only public trader workspace, separate from /sam owner data."""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["traders"])
_UI = Path(__file__).resolve().parent / "trader_ui" / "index.html"

@router.get("/traders", include_in_schema=False)
@router.get("/traders/", include_in_schema=False)
def traders_page():
    return FileResponse(_UI, media_type="text/html; charset=utf-8",
                        headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"})
