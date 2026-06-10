import logging

from agentic import get_display, get_model, get_name
from fastapi import APIRouter

from chatapi.config import AppConfig

router = APIRouter(prefix="/api/settings")
logger = logging.getLogger("fastapi.config")


@router.get("/", tags=["Settings"])
async def get_file() -> dict:
    _config = AppConfig()
    model = get_model().split("/")[-1]
    return {
        "name": get_name(),
        "display": get_display(),
        "version": _config.project_version,
        "model": model,
    }
