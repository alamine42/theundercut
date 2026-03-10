"""Tests for Playwright configuration security (UND-36).

Validates that the Playwright test configuration uses environment
variables for URLs instead of hardcoded values, making it safe to
run in different environments.
"""

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def playwright_config_raw():
    path = ROOT / "web" / "playwright.config.ts"
    if not path.exists():
        pytest.skip("web/playwright.config.ts not found")
    return path.read_text()


class TestPlaywrightUrlConfiguration:
    """Validate URLs are configurable via environment variables (UND-36)."""

    def test_base_url_uses_env_var(self, playwright_config_raw):
        """baseURL should be configurable via TEST_BASE_URL env var."""
        assert "process.env.TEST_BASE_URL" in playwright_config_raw, (
            "baseURL should use process.env.TEST_BASE_URL for configurability"
        )

    def test_base_url_has_fallback(self, playwright_config_raw):
        """baseURL should fall back to localhost:4000 when env var is not set."""
        assert "http://localhost:4000" in playwright_config_raw, (
            "baseURL should keep localhost:4000 as a sensible default"
        )

    def test_web_server_url_uses_env_var(self, playwright_config_raw):
        """webServer url should also be configurable via env var."""
        # Find the webServer section and check its url
        lines = playwright_config_raw.splitlines()
        in_web_server = False
        web_server_url_line = None
        for line in lines:
            if "webServer" in line:
                in_web_server = True
            if in_web_server and "url:" in line:
                web_server_url_line = line
                break
        assert web_server_url_line is not None, "webServer should have a url property"
        assert "process.env.TEST_BASE_URL" in web_server_url_line, (
            "webServer url should use process.env.TEST_BASE_URL"
        )

    def test_no_hardcoded_urls_without_env_fallback(self, playwright_config_raw):
        """All localhost URLs should have env var alternatives."""
        lines = playwright_config_raw.splitlines()
        for line in lines:
            # Skip comment lines
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if "localhost:4000" in line:
                assert "process.env" in line, (
                    f"Line with localhost URL should have env var fallback: {line.strip()}"
                )

    def test_config_uses_ci_env_for_retries(self, playwright_config_raw):
        """Config should use CI env var for retry behavior."""
        assert "process.env.CI" in playwright_config_raw

    def test_config_uses_ci_env_for_workers(self, playwright_config_raw):
        """Config should use CI env var for worker count."""
        assert "workers:" in playwright_config_raw
        assert "process.env.CI" in playwright_config_raw

    def test_config_has_web_server_command(self, playwright_config_raw):
        """webServer should have a command to start the dev server."""
        assert "npm run dev" in playwright_config_raw

    def test_config_has_test_dir(self, playwright_config_raw):
        """Config should specify a test directory."""
        assert "testDir" in playwright_config_raw
