# This file makes the config directory a proper Python package

import logging
import sys
from typing import Literal

import toml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from chatapi.config.logger import ExcludeRouter, UvicornJSONAccessFormatter, UvicornJSONDefaultFormatter

DEFAULT_MODEL_CONFIG = SettingsConfigDict(env_prefix="AGENTIC_")


class AppRouter(BaseSettings):
    API_KEY: str = Field(default="")
    JWT_ISSUER: str = Field(default="")
    JWT_AUDIENCE: str = Field(default="")
    JWT_JWKS_URL: str = Field(default="")
    JWT_ALGORITHMS: str = Field(default="RS256")

    model_config = DEFAULT_MODEL_CONFIG


class AppConfig(BaseSettings):
    project_name: str = Field(default="")
    project_version: str = Field(default="")
    project_desc: str = Field(default="")

    port: int = Field(default=3000)
    host: str = Field(default="0.0.0.0")  # noqa: S104

    log_name: str = Field(default="agent")
    log_level: Literal["debug", "info", "warning", "error"] = Field(default="info")
    log_format: Literal["json", "text"] = Field(default="json")

    format_text: str = Field(default="%(asctime)s [%(levelname)s] [%(name)s] %(message)s")

    def __init__(self) -> None:
        super().__init__()
        pyp = toml.load("./pyproject.toml")
        self.project_name = pyp["project"]["name"]
        self.project_version = pyp["project"]["version"]
        self.project_desc = pyp["project"]["description"]

    def init_logger(self) -> logging.Logger:
        # Create and configure a handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(self.format_text))

        # Remove any existing handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        logger = self.get_logger()
        logger.setLevel(self.log_level.upper())
        logger.addHandler(handler)
        return logger

    def get_logger(self) -> logging.Logger:
        return logging.getLogger(self.log_name)

    def create_logger_config(self) -> dict:
        formatter_json = (
            UvicornJSONDefaultFormatter if self.log_format == "json" else lambda: logging.Formatter(self.format_text)
        )
        formatter_http_access = (
            UvicornJSONAccessFormatter if self.log_format == "json" else lambda: logging.Formatter(self.format_text)
        )
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": formatter_json,
                },
                "access": {
                    "()": formatter_http_access,
                },
            },
            "filters": {
                "exclude_router": {
                    "()": ExcludeRouter,
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                    "filters": ["exclude_router"],
                },
                "access": {
                    "formatter": "access",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "filters": ["exclude_router"],
                },
            },
            "loggers": {
                "uvicorn": {"handlers": ["default"], "level": self.log_level.upper(), "propagate": False},
                "uvicorn.error": {"level": self.log_level.upper()},
                "uvicorn.access": {"handlers": ["access"], "level": self.log_level.upper(), "propagate": False},
            },
            "root": {"handlers": ["default"], "level": self.log_level.upper()},
        }
