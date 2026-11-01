"""Tests for ShopGuard AI Configuration & Environment."""

from pathlib import Path
from src.shopguard.config import settings


def test_settings_paths_and_defaults():
    """Verify default paths and basic configuration values."""
    assert settings.BASE_DIR.exists()
    assert isinstance(settings.SHOPGUARD_PORT, int)
    assert settings.SHOPGUARD_PORT == 8010
    assert isinstance(settings.SIMULATOR_PORT, int)
    assert settings.SIMULATOR_PORT == 8002
    assert settings.LLM_PROVIDER == "groq"
    assert settings.GROQ_MODEL != ""


def test_runtime_directories_created():
    """Verify required directories are instantiated."""
    assert settings.DATA_DIR.exists()
    assert settings.LOGS_DIR.exists()
    assert settings.KNOWLEDGE_BASE_DIR.exists()
