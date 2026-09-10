import logging
import os

_CONFIGURED = False


def _configure() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.addHandler(handler)
    level_name = os.environ.get("RAG_LOG_LEVEL", "INFO").upper()
    level = logging.getLevelName(level_name)
    root.setLevel(level if isinstance(level, int) else logging.INFO)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    _configure()
    return logging.getLogger(name)