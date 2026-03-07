"""Tests for MCP server configuration files (UND-16, UND-17).

Validates that all MCP config files across IDE integrations have correct
structure, required fields, and pinned package versions.
"""

import json
import pytest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"

# All known MCP config files and their expected structure
MCP_CONFIGS = [
    (WEB_DIR / ".mcp.json", "mcpServers"),
    (WEB_DIR / ".cursor" / "mcp.json", "mcpServers"),
    (WEB_DIR / ".gemini" / "settings.json", "mcpServers"),
    (WEB_DIR / ".vscode" / "mcp.json", "servers"),
]


@pytest.fixture(params=MCP_CONFIGS, ids=lambda c: str(c[0].relative_to(ROOT)))
def mcp_config(request):
    path, root_key = request.param
    if not path.exists():
        pytest.skip(f"{path.relative_to(ROOT)} not found")
    with open(path) as f:
        data = json.load(f)
    return path, root_key, data


class TestMCPConfigStructure:
    """Validate MCP config files have correct JSON structure."""

    def test_valid_json(self, mcp_config):
        """Config must be valid JSON."""
        path, _, _ = mcp_config
        with open(path) as f:
            json.load(f)  # Should not raise

    def test_has_root_key(self, mcp_config):
        path, root_key, data = mcp_config
        assert root_key in data, (
            f"{path.name} missing root key '{root_key}'"
        )

    def test_has_agentation_server(self, mcp_config):
        _, root_key, data = mcp_config
        servers = data[root_key]
        assert "agentation" in servers, "Missing 'agentation' server definition"

    def test_agentation_has_command(self, mcp_config):
        _, root_key, data = mcp_config
        server = data[root_key]["agentation"]
        assert "command" in server, "agentation server missing 'command'"

    def test_agentation_has_args(self, mcp_config):
        _, root_key, data = mcp_config
        server = data[root_key]["agentation"]
        assert "args" in server, "agentation server missing 'args'"

    def test_agentation_uses_npx(self, mcp_config):
        _, root_key, data = mcp_config
        server = data[root_key]["agentation"]
        assert server["command"] == "npx", "agentation should use npx command"

    def test_agentation_args_is_list(self, mcp_config):
        _, root_key, data = mcp_config
        server = data[root_key]["agentation"]
        assert isinstance(server["args"], list), "args must be a list"


class TestMCPVersionPinning:
    """Verify agentation-mcp package version is pinned."""

    def test_package_version_pinned(self, mcp_config):
        """The agentation-mcp package should have a pinned version."""
        path, root_key, data = mcp_config
        server = data[root_key]["agentation"]
        args = server["args"]
        # Find the agentation-mcp arg
        mcp_args = [a for a in args if "agentation-mcp" in a]
        assert mcp_args, "No agentation-mcp argument found"
        pkg_ref = mcp_args[0]
        assert "@" in pkg_ref, (
            f"{path.relative_to(ROOT)}: agentation-mcp is not version-pinned "
            f"(found '{pkg_ref}', expected 'agentation-mcp@x.y.z')"
        )


class TestZedSettings:
    """Validate .zed/settings.json if present."""

    @pytest.fixture()
    def zed_config(self):
        path = WEB_DIR / ".zed" / "settings.json"
        if not path.exists():
            pytest.skip(".zed/settings.json not found")
        with open(path) as f:
            return json.load(f)

    def test_has_context_servers(self, zed_config):
        assert "context_servers" in zed_config

    def test_agentation_has_source(self, zed_config):
        server = zed_config["context_servers"]["agentation"]
        assert "source" in server
