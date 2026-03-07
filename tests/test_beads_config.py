"""Tests for .beads/config.yaml structure and parsing (UND-47, UND-48).

Validates the beads configuration file is well-formed YAML with
expected structure, known keys, and correct types.
"""

import pytest
import yaml
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / ".beads" / "config.yaml"


@pytest.fixture(scope="module")
def beads_config_raw():
    """Return raw YAML content."""
    if not CONFIG_PATH.exists():
        pytest.skip(".beads/config.yaml not found")
    return CONFIG_PATH.read_text()


@pytest.fixture(scope="module")
def beads_config(beads_config_raw):
    """Return parsed YAML (may be None if all keys are commented out)."""
    return yaml.safe_load(beads_config_raw)


class TestBeadsConfigParsing:
    """Verify the config file is valid YAML (UND-48)."""

    def test_file_exists(self):
        assert CONFIG_PATH.exists(), ".beads/config.yaml not found"

    def test_valid_yaml(self, beads_config_raw):
        """Config must be parseable YAML without errors."""
        try:
            yaml.safe_load(beads_config_raw)
        except yaml.YAMLError as exc:
            pytest.fail(f".beads/config.yaml is not valid YAML: {exc}")

    def test_no_tab_characters(self, beads_config_raw):
        """YAML should use spaces, not tabs."""
        for i, line in enumerate(beads_config_raw.splitlines(), 1):
            assert "\t" not in line, f"Tab character found on line {i}"

    def test_parseable_without_crash(self, beads_config_raw):
        """Loading the config should not raise any exception."""
        result = yaml.safe_load(beads_config_raw)
        # Result can be None if entirely commented out, which is valid
        assert result is None or isinstance(result, dict)


class TestBeadsConfigKnownKeys:
    """Validate that only known keys appear in the config (UND-48)."""

    KNOWN_KEYS = {
        "issue-prefix",
        "no-db",
        "no-daemon",
        "no-auto-flush",
        "no-auto-import",
        "json",
        "actor",
        "db",
        "auto-start-daemon",
        "flush-debounce",
        "sync-branch",
        "repos",
    }

    def test_only_known_keys(self, beads_config):
        if beads_config is None:
            pytest.skip("All config keys are commented out")
        for key in beads_config:
            assert key in self.KNOWN_KEYS, (
                f"Unknown key '{key}' in .beads/config.yaml"
            )


class TestBeadsMultiRepoConfig:
    """Validate multi-repo configuration structure (UND-47)."""

    def test_repos_key_is_dict_if_present(self, beads_config):
        if beads_config is None or "repos" not in beads_config:
            pytest.skip("repos key not present or config is commented out")
        repos = beads_config["repos"]
        assert isinstance(repos, dict), "repos must be a mapping"

    def test_repos_has_primary_if_present(self, beads_config):
        if beads_config is None or "repos" not in beads_config:
            pytest.skip("repos key not present or config is commented out")
        assert "primary" in beads_config["repos"], (
            "Multi-repo config must have a 'primary' key"
        )

    def test_repos_additional_is_list_if_present(self, beads_config):
        if beads_config is None or "repos" not in beads_config:
            pytest.skip("repos key not present or config is commented out")
        repos = beads_config["repos"]
        if "additional" in repos:
            assert isinstance(repos["additional"], list), (
                "repos.additional must be a list of paths"
            )

    def test_config_documents_multi_repo(self, beads_config_raw):
        """The config file should document the multi-repo feature."""
        assert "multi-repo" in beads_config_raw.lower() or "repos:" in beads_config_raw, (
            "Config file should document multi-repo configuration"
        )
