import pytest
import os
import json
from typing import Dict, Any
from pathlib import Path
from mcp_test_harness.config import load_server_config, create_server_parameters
from mcp import StdioServerParameters

@pytest.fixture
def sample_config() -> Dict[str, Any]:
    return {
        "mcpServers": {
            "test-server": {
                "command": "echo",
                "args": ["test"],
                "env": {
                    "TEST_KEY": "test_value"
                }
            }
        }
    }

@pytest.fixture
def config_file(tmp_path: Path, sample_config: Dict[str, Any]) -> str:
    config_path = tmp_path / "test_config.json"
    with open(config_path, "w") as f:
        json.dump(sample_config, f)
    return str(config_path)

def test_load_server_config(config_file: str) -> None:
    config = load_server_config(config_file)
    assert "mcpServers" in config
    assert "test-server" in config["mcpServers"]
    assert config["mcpServers"]["test-server"]["command"] == "echo"

def test_create_server_parameters(sample_config: Dict[str, Any]) -> None:
    params = create_server_parameters(sample_config)
    assert "test-server" in params
    assert isinstance(params["test-server"], StdioServerParameters)
    assert params["test-server"].command == "echo"
    assert params["test-server"].args == ["test"]
    assert "TEST_KEY" in params["test-server"].env
    assert "PATH" in params["test-server"].env

def test_load_config_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        load_server_config("nonexistent_file.json") 