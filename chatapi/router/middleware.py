import logging
import os
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Annotated, Any

import jwt
from dotenv import load_dotenv
from fastapi import Depends, Request, Response
from fastapi.exceptions import HTTPException
from fastapi.security import APIKeyHeader
from jwt import PyJWKClient
from pydantic import ValidationError
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware

from chatapi.config.app import AppRouter
from chatapi.config.logger import CTX_TRACE_ID, HEADER_KEY_NAME, HEADER_TRACE_NAME
from chatapi.models.orm import ChatType

load_dotenv()

logger = logging.getLogger("fastapi.middleware")

app = AppRouter()

is_local = os.getenv("HOST", "") == "localhost" and not app.API_KEY
api_key_header = APIKeyHeader(name=HEADER_KEY_NAME, auto_error=False)
_jwks_client: PyJWKClient | None = None


class OrderType(Enum):
    ASC = "ASC"
    DESC = "DESC"


async def param_get_file(session_id: str, check_sum: str) -> dict[str, str]:
    return {"session_id": session_id, "check_sum": check_sum}


async def param_upload_file(session_id: str) -> dict[str, str]:
    return {"session_id": session_id}


async def param_get_messages(session_id: str, res_format: str = "json") -> dict[str, str]:
    return {"session_id": session_id, "format": res_format}


async def param_history(session_id: str, skip: int = 0, limit: int = 100, order: str = "ASC") -> dict[str, str | int]:
    return {"session_id": session_id, "skip": skip, "limit": limit, "order": order}


def str_to_timestamp(value: str) -> datetime:
    """Convert string to datetime (accepts either format YYYY-MM-DD or YYYY-MM-DD HH:MM:00)."""
    if value is None or value.strip() == "":
        raise ValidationError("Date is required")

    # Try parsing with the format YYYY-MM-DD
    try:
        parsed_date = datetime.strptime(value, "%Y-%m-%d")
        return parsed_date
    except ValueError:
        pass

    # Try parsing with the format YYYY-MM-DD HH:MM:00
    try:
        parsed_date = datetime.strptime(value, "%Y-%m-%d %H:%M:00")
        return parsed_date
    except ValueError as e:
        raise ValueError(f"Invalid timestamp format: {value}. Expected YYYY-MM-DD or YYYY-MM-DD HH:MM:00") from e


async def param_records(
    beginDate: str,
    lastDate: str,
    content: str | None = None,
    chatType: ChatType | None = None,
    deleted: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    order: OrderType | None = OrderType.DESC,
) -> dict[str, Any]:
    return {
        "content": content,
        "chat_type": chatType,
        "deleted": deleted,
        "begin_date": str_to_timestamp(beginDate),
        "last_date": str_to_timestamp(lastDate),
        "skip": skip,
        "limit": limit,
        "order": order,
    }


def _jwt_algorithms() -> list[str]:
    return [algorithm.strip() for algorithm in app.JWT_ALGORITHMS.split(",") if algorithm.strip()]


def _jwt_enabled() -> bool:
    return bool(app.JWT_ISSUER and app.JWT_AUDIENCE and app.JWT_JWKS_URL)


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(app.JWT_JWKS_URL)

    return _jwks_client


def _decode_bearer_token(authorization: str | None) -> dict[str, Any] | None:
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None

    if not _jwt_enabled():
        logger.warning("JWT bearer token received but JWT auth is not configured")
        return None

    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=_jwt_algorithms(),
            audience=app.JWT_AUDIENCE,
            issuer=app.JWT_ISSUER,
        )
    except jwt.PyJWTError as exc:
        logger.warning("JWT authentication failed: %s", exc)
        return None


async def api_key_authentication(
    request: Request,
    api_key: Annotated[str | None, Depends(api_key_header)],
) -> str | dict[str, Any] | None:
    if is_local:
        return api_key

    if app.API_KEY and api_key == app.API_KEY:
        return api_key

    claims = _decode_bearer_token(request.headers.get("authorization"))
    if claims:
        request.state.auth_claims = claims
        return claims

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


# Middleware get trace-id
class TraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        trace_id = request.headers.get(HEADER_TRACE_NAME)

        if trace_id:
            CTX_TRACE_ID.set(trace_id)  # type: ignore

        response = await call_next(request)

        if trace_id:
            response.headers[HEADER_TRACE_NAME] = trace_id

        return response
