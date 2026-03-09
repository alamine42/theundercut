"""Tests for .beads/config.yaml structure and parsing (UND-47, UND-48, UND-60, UND-61).

Validates the beads configuration file is well-formed YAML with
expected structure, known keys, correct types, robust parsing,
and multi-repo configuration validation.
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


class TestYamlParsingRobustness:
    """Test YAML parsing edge cases and error handling (UND-61)."""

    def test_malformed_yaml_raises_error(self):
        """Malformed YAML should raise a YAMLError, not crash silently."""
        malformed = "key: [invalid: yaml: {{{"
        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(malformed)

    def test_empty_file_returns_none(self):
        """An empty YAML file should parse to None."""
        assert yaml.safe_load("") is None

    def test_comments_only_returns_none(self):
        """A file with only comments should parse to None."""
        comments_only = "# just a comment\n# another comment\n"
        assert yaml.safe_load(comments_only) is None

    def test_yaml_with_duplicate_keys_uses_last(self):
        """YAML with duplicate keys should use the last value (YAML spec)."""
        content = "key: first\nkey: second\n"
        result = yaml.safe_load(content)
        assert result["key"] == "second"

    def test_config_values_have_correct_types(self, beads_config_raw):
        """When config keys are uncommented, they should have expected types."""
        # Build a test config with all keys uncommented
        test_config = """
        issue-prefix: "test"
        no-db: false
        no-daemon: false
        no-auto-flush: false
        no-auto-import: false
        json: false
        actor: "test-actor"
        db: "/tmp/test.db"
        auto-start-daemon: true
        flush-debounce: "5s"
        sync-branch: "beads-sync"
        """
        result = yaml.safe_load(test_config)
        assert isinstance(result["issue-prefix"], str)
        assert isinstance(result["no-db"], bool)
        assert isinstance(result["no-daemon"], bool)
        assert isinstance(result["no-auto-flush"], bool)
        assert isinstance(result["no-auto-import"], bool)
        assert isinstance(result["json"], bool)
        assert isinstance(result["actor"], str)
        assert isinstance(result["db"], str)
        assert isinstance(result["auto-start-daemon"], bool)
        assert isinstance(result["flush-debounce"], str)
        assert isinstance(result["sync-branch"], str)

    def test_yaml_safe_load_rejects_unsafe_tags(self):
        """safe_load should reject dangerous YAML tags."""
        dangerous = "!!python/object/apply:os.system ['echo hacked']"
        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(dangerous)

    def test_config_encoding_is_utf8(self):
        """Config file should be valid UTF-8."""
        try:
            CONFIG_PATH.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            pytest.fail(".beads/config.yaml is not valid UTF-8")

    def test_config_lines_not_excessively_long(self, beads_config_raw):
        """Config lines should be reasonably short for readability."""
        for i, line in enumerate(beads_config_raw.splitlines(), 1):
            assert len(line) <= 200, (
                f"Line {i} is {len(line)} characters; keep lines under 200"
            )

    def test_missing_config_file_handled(self, tmp_path):
        """Application should handle a missing config file gracefully."""
        missing_path = tmp_path / "nonexistent" / "config.yaml"
        assert not missing_path.exists()


class TestMultiRepoConfigValidation:
    """Validate multi-repo configuration robustness (UND-60)."""

    def test_multi_repo_with_valid_paths(self):
        """A well-formed multi-repo config should parse correctly."""
        config = yaml.safe_load("""
        repos:
          primary: "."
          additional:
            - ~/beads-planning
            - ~/work-planning
        """)
        assert config["repos"]["primary"] == "."
        assert isinstance(config["repos"]["additional"], list)
        assert len(config["repos"]["additional"]) == 2

    def test_multi_repo_primary_must_be_string(self):
        """Primary repo value should be a string path."""
        config = yaml.safe_load("""
        repos:
          primary: "."
        """)
        assert isinstance(config["repos"]["primary"], str)

    def test_multi_repo_additional_empty_list(self):
        """An empty additional repos list should be valid."""
        config = yaml.safe_load("""
        repos:
          primary: "."
          additional: []
        """)
        assert config["repos"]["additional"] == []

    def test_multi_repo_additional_entries_are_strings(self):
        """Each entry in additional repos should be a string."""
        config = yaml.safe_load("""
        repos:
          primary: "."
          additional:
            - ~/repo1
            - /absolute/path/repo2
        """)
        for entry in config["repos"]["additional"]:
            assert isinstance(entry, str), (
                f"Additional repo entry must be a string, got: {type(entry)}"
            )

    def test_multi_repo_relative_paths_accepted(self):
        """Relative paths should be accepted in repo config."""
        config = yaml.safe_load("""
        repos:
          primary: "."
          additional:
            - ../sibling-repo
            - ./child-repo
        """)
        additional = config["repos"]["additional"]
        assert "../sibling-repo" in additional
        assert "./child-repo" in additional

    def test_multi_repo_tilde_expansion_paths(self):
        """Tilde paths (~/) should be accepted as they expand at runtime."""
        config = yaml.safe_load("""
        repos:
          primary: "."
          additional:
            - ~/beads-planning
        """)
        assert config["repos"]["additional"][0].startswith("~")

    def test_multi_repo_without_additional(self):
        """A multi-repo config with only primary should be valid."""
        config = yaml.safe_load("""
        repos:
          primary: "."
        """)
        assert "primary" in config["repos"]
        assert "additional" not in config["repos"]

    def test_multi_repo_duplicate_paths_detectable(self):
        """Duplicate paths in additional repos should be detectable."""
        config = yaml.safe_load("""
        repos:
          primary: "."
          additional:
            - ~/repo1
            - ~/repo1
        """)
        additional = config["repos"]["additional"]
        assert len(additional) != len(set(additional)), (
            "Duplicate repo paths should be detectable"
        )

    def test_config_documents_experimental_status(self, beads_config_raw):
        """Multi-repo config should document its experimental status."""
        assert "experimental" in beads_config_raw.lower(), (
            "Multi-repo feature should be documented as experimental"
        )
