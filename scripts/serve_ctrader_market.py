"""Standalone ASGI entry point for the read-only cTrader quote bridge."""

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

from app.integrations.ctrader_bridge import router

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(router)
