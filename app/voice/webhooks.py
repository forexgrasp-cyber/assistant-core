"""Voice webhooks setup."""

from fastapi import FastAPI
from .router import router


def setup_voice_webhooks(app: FastAPI):
    """Mount voice webhook routes."""
    app.include_router(router)