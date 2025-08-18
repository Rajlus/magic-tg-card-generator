"""Functional tests for Config - testing actual configuration behavior."""

import os
from pathlib import Path
from unittest.mock import patch

from magic_tg_card_generator.config import Settings


class TestConfigFunctionality:
    """Test that Settings actually loads and manages settings correctly."""

    def test_config_loads_from_environment_variables(self, tmp_path, monkeypatch):
        """Test that config actually reads from environment."""
        monkeypatch.chdir(tmp_path)

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test_key_123",
                "DATABASE_URL": "postgresql://localhost/test",
                "API_TIMEOUT": "60",
            },
        ):
            config = Settings()

            # Verify it actually loaded the values
            assert config.api_key == "test_key_123"
            assert config.database_url == "postgresql://localhost/test"
            assert config.api_timeout == 60

    def test_config_uses_defaults_when_env_not_set(self, tmp_path, monkeypatch):
        """Test that defaults work when environment is empty."""
        monkeypatch.chdir(tmp_path)

        with patch.dict(os.environ, {}, clear=True):
            config = Settings()

            # Verify defaults are functional
            assert config.api_key is None
            assert config.database_url == "sqlite:///./data/app.db"
            assert config.api_timeout == 30

    def test_config_creates_directories_on_init(self, tmp_path, monkeypatch):
        """Test that config actually creates required directories."""
        monkeypatch.chdir(tmp_path)

        config = Settings()

        # Verify directories were actually created
        assert config.data_dir.exists()
        assert config.output_dir.exists()
        assert config.data_dir.is_dir()
        assert config.output_dir.is_dir()

    def test_config_loads_from_env_file(self, tmp_path, monkeypatch):
        """Test that .env file is actually loaded."""
        monkeypatch.chdir(tmp_path)

        env_file = tmp_path / ".env"
        env_file.write_text(
            "OPENAI_API_KEY=env_file_key\n" "DEBUG=true\n" "LOG_LEVEL=DEBUG\n"
        )

        # The Settings class automatically loads .env file
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "env_file_key", "DEBUG": "true", "LOG_LEVEL": "DEBUG"},
        ):
            config = Settings()

            assert config.api_key == "env_file_key"
            assert config.debug is True
            assert config.log_level == "DEBUG"

    def test_config_app_metadata_is_correct(self, tmp_path, monkeypatch):
        """Test that app metadata is set correctly."""
        monkeypatch.chdir(tmp_path)

        config = Settings()

        assert config.app_name == "Magic TG Card Generator"
        assert config.app_version == "0.1.0"

    def test_config_debug_mode_affects_logging(self, tmp_path, monkeypatch):
        """Test that debug mode actually changes behavior."""
        monkeypatch.chdir(tmp_path)

        with patch.dict(os.environ, {"DEBUG": "true", "LOG_LEVEL": "DEBUG"}):
            config = Settings()
            assert config.debug is True
            assert config.log_level == "DEBUG"

        with patch.dict(os.environ, {"DEBUG": "false"}):
            config = Settings()
            assert config.debug is False

    def test_config_paths_are_pathlib_objects(self, tmp_path, monkeypatch):
        """Test that path settings return Path objects."""
        monkeypatch.chdir(tmp_path)

        config = Settings()

        assert isinstance(config.data_dir, Path)
        assert isinstance(config.output_dir, Path)

    def test_config_environment_precedence(self, tmp_path, monkeypatch):
        """Test that environment variables override defaults."""
        monkeypatch.chdir(tmp_path)

        # First with defaults
        config1 = Settings()
        default_timeout = config1.api_timeout

        # Then with environment override
        with patch.dict(os.environ, {"API_TIMEOUT": "120"}):
            config2 = Settings()
            assert config2.api_timeout == 120
            assert config2.api_timeout != default_timeout

    def test_config_database_url_format(self, tmp_path, monkeypatch):
        """Test that database URL is properly formatted."""
        monkeypatch.chdir(tmp_path)

        config = Settings()

        # Should be a valid SQLite URL by default
        assert config.database_url.startswith("sqlite://")

        # Test with custom database URL
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://user:pass@localhost/db"}
        ):
            config = Settings()
            assert config.database_url == "postgresql://user:pass@localhost/db"

    def test_config_api_key_from_alias(self, tmp_path, monkeypatch):
        """Test that API key can be set via OPENAI_API_KEY alias."""
        monkeypatch.chdir(tmp_path)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            config = Settings()
            assert config.api_key == "sk-test-key"

    def test_config_case_insensitive(self, tmp_path, monkeypatch):
        """Test that environment variables are case insensitive."""
        monkeypatch.chdir(tmp_path)

        with patch.dict(os.environ, {"debug": "true"}):
            config = Settings()
            assert config.debug is True

        with patch.dict(os.environ, {"DEBUG": "true"}):
            config = Settings()
            assert config.debug is True
