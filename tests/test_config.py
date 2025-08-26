"""Tests for Codexa configuration."""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from codexa.config import Config


def test_config_initialization():
    """Test that Config initializes properly."""
    config = Config()
    assert config.default_provider == "openai"
    assert "openai" in config.default_models
    assert "anthropic" in config.default_models


def test_config_with_env_vars():
    """Test configuration with environment variables."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        config = Config()
        assert config.get_api_key("openai") == "test-key"
        assert config.has_valid_config() is True


def test_config_without_api_keys():
    """Test configuration without API keys."""
    with patch.dict(os.environ, {}, clear=True):
        config = Config()
        assert config.get_api_key("openai") is None
        assert config.has_valid_config() is False


def test_create_default_config():
    """Test creating default configuration file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / ".codexarc"
        
        with patch("pathlib.Path.home", return_value=Path(temp_dir)):
            config = Config()
            config.create_default_config()
            
            assert config_path.exists()
            
            # Verify content
            import yaml
            with open(config_path, 'r') as f:
                content = yaml.safe_load(f)
            
            assert content["provider"] == "openai"
            assert "models" in content
            assert "guidelines" in content