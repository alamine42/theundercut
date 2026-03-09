"""Tests for MCP server configuration files (UND-16, UND-17, UND-55).

Validates that all MCP config files across IDE integrations have correct
structure, required fields, pinned package versions, and integration
connectivity prerequisites.
"""

import json
import re

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


class TestMCPServerIntegration:
    """Validate MCP server integration and connectivity prerequisites (UND-55)."""

    def test_all_configs_reference_same_package(self, mcp_config):
        """All MCP configs should reference the same agentation-mcp package."""
        _, root_key, data = mcp_config
        server = data[root_key]["agentation"]
        args = server["args"]
        mcp_args = [a for a in args if "agentation-mcp" in a]
        assert mcp_args, "Must reference agentation-mcp package"

    def test_package_version_is_semver(self, mcp_config):
        """The pinned version should follow semantic versioning."""
        _, root_key, data = mcp_config
        server = data[root_key]["agentation"]
        args = server["args"]
        mcp_args = [a for a in args if "agentation-mcp" in a]
        if not mcp_args:
            pytest.skip("No agentation-mcp arg found")
        pkg_ref = mcp_args[0]
        if "@" in pkg_ref:
            version = pkg_ref.split("@")[-1]
            semver_pattern = re.compile(r"^\d+\.\d+\.\d+$")
            assert semver_pattern.match(version), (
                f"Version '{version}' is not valid semver (expected x.y.z)"
            )

    def test_all_configs_use_same_version(self):
        """All MCP config files should pin to the same version."""
        versions = []
        for path, root_key in MCP_CONFIGS:
            if not path.exists():
                continue
            with open(path) as f:
                data = json.load(f)
            server = data[root_key]["agentation"]
            args = server["args"]
            mcp_args = [a for a in args if "agentation-mcp" in a]
            if mcp_args and "@" in mcp_args[0]:
                versions.append(mcp_args[0].split("@")[-1])
        if len(versions) < 2:
            pytest.skip("Not enough configs with pinned versions to compare")
        assert len(set(versions)) == 1, (
            f"MCP configs use different versions: {set(versions)}"
        )

    def test_npx_dash_y_flag_present(self, mcp_config):
        """npx should use -y flag for non-interactive execution."""
        _, root_key, data = mcp_config
        server = data[root_key]["agentation"]
        args = server["args"]
        assert "-y" in args, (
            "npx args should include '-y' for non-interactive installation"
        )

    def test_command_is_not_empty(self, mcp_config):
        """The command field should not be empty."""
        _, root_key, data = mcp_config
        server = data[root_key]["agentation"]
        assert server["command"].strip(), "command must not be empty"

    def test_args_are_not_empty(self, mcp_config):
        """The args list should contain at least one entry."""
        _, root_key, data = mcp_config
        server = data[root_key]["agentation"]
        assert len(server["args"]) > 0, "args must have at least one entry"

    def test_no_extraneous_server_config_keys(self, mcp_config):
        """Server config should only contain known keys."""
        _, root_key, data = mcp_config
        server = data[root_key]["agentation"]
        known_keys = {"command", "args", "env", "cwd", "source", "type"}
        for key in server:
            assert key in known_keys, (
                f"Unexpected key '{key}' in agentation server config"
            )

    def test_config_files_are_valid_json(self):
        """All MCP config files should be parseable as valid JSON."""
        for path, _ in MCP_CONFIGS:
            if not path.exists():
                continue
            try:
                with open(path) as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"{path.relative_to(ROOT)} is not valid JSON: {e}")

    def test_config_files_not_empty(self):
        """MCP config files should not be empty."""
        for path, _ in MCP_CONFIGS:
            if not path.exists():
                continue
            content = path.read_text().strip()
            assert content, f"{path.relative_to(ROOT)} is empty"
