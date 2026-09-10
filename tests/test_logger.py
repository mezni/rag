import pytest
from pydantic import ValidationError

from src.config.logger import Settings


def test_settings_default_log_level() -> None:
    assert Settings().log_level == "INFO"


def test_settings_normalizes_and_validates_level() -> None:
    assert Settings(log_level=" debug ").log_level == "DEBUG"


def test_settings_rejects_unknown_level() -> None:
    with pytest.raises(ValidationError, match="unknown log level"):
        Settings(log_level="LOUD")