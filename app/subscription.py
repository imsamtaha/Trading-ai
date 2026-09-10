from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["subscription"])
CANONICAL_ATLAS_PATH = "/atlas-ultimate"


@router.get("/subscribe", include_in_schema=False)
def subscribe() -> RedirectResponse:
    """Legacy public entry point; all subscriber UI now lives in ATLAS ULTIMATE."""
    return RedirectResponse(url=f"{CANONICAL_ATLAS_PATH}#plans", status_code=308)
