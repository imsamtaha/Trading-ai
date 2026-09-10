from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["subscription"])


@router.get("/subscribe", include_in_schema=False)
def subscribe() -> RedirectResponse:
    """Legacy subscriber route; plans now live on the canonical ATLAS ULTIMATE root."""
    return RedirectResponse(url="/#plans", status_code=308)
