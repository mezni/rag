import yaml
from pathlib import Path
from pydantic import ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict
from config.settings import ApplicationSettings
from config.logger import setup_logger

logger = setup_logger("config_manager")


class ConfigManager(BaseSettings):
    """Manages application configuration, loading from YAML and environment variables.

    Settings are loaded in the following order (later overrides earlier):
    1. Default values (defined in ApplicationSettings)
    2. YAML file (e.g., pipeline.yaml)
    3. Environment variables
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    settings: ApplicationSettings

    @classmethod
    def load_from_yaml(cls, yaml_path: Path) -> "ConfigManager":
        if not yaml_path.exists():
            logger.warning(f"YAML config file not found: {yaml_path}")
            return cls(settings=ApplicationSettings(pipeline=None, runtime=None)) # Provide default or handle error appropriately

        logger.info(f"Loading configuration from {yaml_path}")
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)

        # Assuming the YAML directly maps to ApplicationSettings structure
        app_settings = ApplicationSettings(**yaml_config)
        return cls(settings=app_settings)


def get_application_settings(config_path: Path) -> ApplicationSettings:
    config_manager = ConfigManager.load_from_yaml(config_path)
    return config_manager.settings
