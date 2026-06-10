import logging
import sys
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request, responses
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from scalar_doc import ScalarDoc
from starlette import status

from chatapi.config import AppConfig, AppRouter
from chatapi.config.logger import UvicornJSONDefaultFormatter
from chatapi.models import ErrorResponse
from chatapi.router.chat import router as router_prediction
from chatapi.router.files import router as router_files
from chatapi.router.history import router as router_chathistory
from chatapi.router.middleware import TraceIDMiddleware
from chatapi.router.prompts import router as router_prompts
from chatapi.router.setting import router as router_setting

load_dotenv()


_config = AppConfig()


def create_app_config() -> AppConfig:
    return _config  # type: ignore


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(
    UvicornJSONDefaultFormatter() if _config.log_format == "json" else logging.Formatter(_config.format_text),
)

# Remove any existing handlers
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logger = logging.getLogger()
logger.setLevel(_config.log_level.upper())
logger.addHandler(handler)

logger.info("init config")


tags_metadata = [
    {
        "name": "Chat",
        "description": "AI model for generating predictions.",
    },
    {
        "name": "Files",
        "description": "Operations for managing file uploads and retrievals.",
    },
    {
        "name": "History",
        "description": "Operations for managing chat history.",
    },
    {
        "name": "Config",
        "description": "Configuration settings and parameters for the application.",
    },
]


load_dotenv()


def _register_routes(app: FastAPI) -> None:
    app.add_middleware(TraceIDMiddleware)
    app.include_router(router_prediction)
    app.include_router(router_chathistory)
    app.include_router(router_files)
    app.include_router(router_prompts)
    app.include_router(router_setting)


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(status.HTTP_404_NOT_FOUND)
    async def not_found_exception_handler(req: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(error="Not Found", code=404).model_dump(),
        )

    @app.exception_handler(status.HTTP_401_UNAUTHORIZED)
    async def unauthorized_exception_handler(req: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(error="Not authenticated", code=401).model_dump(),
        )

    @app.exception_handler(status.HTTP_403_FORBIDDEN)
    async def forbidden_exception_handler(req: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=ErrorResponse(error="Forbidden", code=403).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(req: Request, exc: RequestValidationError) -> JSONResponse:
        error_details = [{"msg": f"{err['msg']}", "loc": ".".join(map(str, err["loc"]))} for err in exc.errors()]
        error_message = "; ".join([f"{detail['msg']} at {detail['loc']}" for detail in error_details])
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(error=error_message, code=status.HTTP_400_BAD_REQUEST).model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def default_exception_handler(req: Request, exc: HTTPException) -> JSONResponse:
        split_detail = exc.detail.split(":")
        if len(split_detail) != 2:
            code, detail = 500, exc.detail
        else:
            try:
                code, detail = split_detail
                code = int(code)
            except (ValueError, TypeError):
                code, detail = 500, exc.detail

        return JSONResponse(
            status_code=code,
            content=ErrorResponse(error=detail.strip(), code=code).model_dump(),
        )


def create_app_fastapi(setup_workflow: Callable, title: str, desc: str) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logger = logging.getLogger("fastapi")
        await setup_workflow()
        logger.info("checkpoint connection...")
        try:
            yield
            logger.info("Connection is closed")
        except Exception as e:
            logger.error("Elastic connection can't close with error: " + str(e))

    app = FastAPI(
        title=title if title else "Agentic AI",
        description=desc if desc else "🤖 AI API Specification",
        lifespan=lifespan,
        summary=_config.project_desc,
        openapi_tags=tags_metadata,
        docs_url=None,
        redoc_url=None,
    )

    docs = ScalarDoc.from_spec(spec=app.openapi_url, mode="url")

    @app.get("/healthz")
    async def health_check() -> str:
        return "☕"

    @app.get("/docs", include_in_schema=False)
    async def get_docs() -> responses.HTMLResponse:
        docs_html = docs.to_html()
        return responses.HTMLResponse(docs_html)

    if _config.host == "localhost" and not AppRouter().API_KEY:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    _register_routes(app)
    _register_exception_handlers(app)

    return app
