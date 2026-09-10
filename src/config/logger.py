import logging
import os

from pydantic import BaseModel, field_validator

_CONFIGURED = False


class Settings(BaseModel):
    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def _valid_log_level(cls, value: str) -> str:
        level = value.strip().upper()
        if not isinstance(logging.getLevelName(level), int):
            raise ValueError(f"unknown log level: {level}")
        return level


def _configure() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    settings = Settings(log_level=os.environ.get("RAG_LOG_LEVEL", "INFO"))
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(settings.log_level)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    _configure()
    return logging.getLogger(name)
