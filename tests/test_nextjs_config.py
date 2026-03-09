"""Tests for Next.js configuration and build setup (UND-15, UND-25, UND-27).

Validates the Next.js configuration files, build/start commands, and
rewrite rules are properly defined.
"""

import json
import pytest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"


@pytest.fixture(scope="module")
def package_json():
    path = WEB_DIR / "package.json"
    if not path.exists():
        pytest.skip("web/package.json not found")
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def next_config_source():
    path = WEB_DIR / "next.config.ts"
    if not path.exists():
        pytest.skip("web/next.config.ts not found")
    return path.read_text()


class TestPackageJsonScripts:
    """Validate build and start commands exist (UND-25)."""

    def test_has_build_script(self, package_json):
        assert "build" in package_json.get("scripts", {}), (
            "package.json missing 'build' script"
        )

    def test_has_start_script(self, package_json):
        assert "start" in package_json.get("scripts", {}), (
            "package.json missing 'start' script"
        )

    def test_has_dev_script(self, package_json):
        assert "dev" in package_json.get("scripts", {}), (
            "package.json missing 'dev' script"
        )

    def test_has_lint_script(self, package_json):
        assert "lint" in package_json.get("scripts", {}), (
            "package.json missing 'lint' script"
        )

    def test_has_test_script(self, package_json):
        assert "test" in package_json.get("scripts", {}), (
            "package.json missing 'test' script"
        )

    def test_build_uses_next(self, package_json):
        build = package_json["scripts"]["build"]
        assert "next" in build, "build script should use 'next build'"

    def test_start_uses_next(self, package_json):
        start = package_json["scripts"]["start"]
        assert "next" in start, "start script should use 'next start'"


class TestNextJsDependencies:
    """Validate Next.js dependencies are present."""

    def test_has_next_dependency(self, package_json):
        deps = package_json.get("dependencies", {})
        assert "next" in deps, "Missing 'next' in dependencies"

    def test_has_react_dependency(self, package_json):
        deps = package_json.get("dependencies", {})
        assert "react" in deps, "Missing 'react' in dependencies"

    def test_has_react_dom_dependency(self, package_json):
        deps = package_json.get("dependencies", {})
        assert "react-dom" in deps, "Missing 'react-dom' in dependencies"


class TestNextConfigRewrites:
    """Validate next.config.ts rewrite rules (UND-27)."""

    def test_config_file_exists(self):
        assert (WEB_DIR / "next.config.ts").exists(), "next.config.ts not found"

    def test_has_rewrites(self, next_config_source):
        assert "rewrites" in next_config_source, (
            "next.config.ts should define rewrites"
        )

    def test_rewrites_api_v1_path(self, next_config_source):
        assert "/api/v1/" in next_config_source, (
            "next.config.ts should rewrite /api/v1/ paths"
        )

    def test_uses_fastapi_url(self, next_config_source):
        assert "FASTAPI_URL" in next_config_source or "fastapiUrl" in next_config_source, (
            "next.config.ts should reference FASTAPI_URL"
        )

    def test_validates_fastapi_url(self, next_config_source):
        """The config should validate the FASTAPI_URL value."""
        assert "getValidatedFastapiUrl" in next_config_source or "new URL" in next_config_source, (
            "next.config.ts should validate the FASTAPI_URL"
        )

    def test_blocks_ssrf_hosts(self):
        """The config should block known SSRF targets (via imported module)."""
        validate_module = WEB_DIR / "src" / "lib" / "validate-fastapi-url.ts"
        assert validate_module.exists(), "validate-fastapi-url.ts not found"
        source = validate_module.read_text()
        assert "169.254.169.254" in source, (
            "URL validation module should block cloud metadata SSRF endpoint"
        )


class TestRedirectPages:
    """Validate redirect pages exist and work (UND-15)."""

    def test_circuits_season_redirect_exists(self):
        page = WEB_DIR / "src" / "app" / "(main)" / "circuits" / "[season]" / "page.tsx"
        assert page.exists(), "circuits/[season]/page.tsx redirect page not found"

    def test_circuits_season_redirect_content(self):
        page = WEB_DIR / "src" / "app" / "(main)" / "circuits" / "[season]" / "page.tsx"
        if not page.exists():
            pytest.skip("redirect page not found")
        content = page.read_text()
        assert "redirect" in content, "Page should use redirect function"
        assert "/circuits" in content, "Page should redirect to /circuits"

    def test_redirect_imports_from_next(self):
        page = WEB_DIR / "src" / "app" / "(main)" / "circuits" / "[season]" / "page.tsx"
        if not page.exists():
            pytest.skip("redirect page not found")
        content = page.read_text()
        assert "next/navigation" in content, (
            "redirect should be imported from next/navigation"
        )
