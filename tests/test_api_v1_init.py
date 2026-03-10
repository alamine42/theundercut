"""Tests for API v1 module initialization (UND-34).

Validates that the API v1 package structure is correct: the __init__.py
exists, all expected sub-module files are present, and each sub-module
defines a FastAPI APIRouter with a proper /api/v1/ prefix.

Uses AST parsing rather than runtime imports to avoid requiring the full
dependency chain (psycopg2, httpx, etc.) in the test environment.
"""

import ast
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
V1_DIR = ROOT / "src" / "theundercut" / "api" / "v1"

EXPECTED_MODULES = [
    "analytics",
    "circuits",
    "race",
    "standings",
    "strategy",
    "testing",
]


class TestApiV1PackageStructure:
    """Verify the api.v1 package directory structure (UND-34)."""

    def test_v1_directory_exists(self):
        """The v1/ directory should exist."""
        assert V1_DIR.is_dir(), f"Expected directory: {V1_DIR}"

    def test_v1_init_file_exists(self):
        """The v1/__init__.py file should exist (making it a package)."""
        init = V1_DIR / "__init__.py"
        assert init.exists(), "v1/ must have an __init__.py"

    def test_api_init_file_exists(self):
        """The api/__init__.py file should exist."""
        api_init = V1_DIR.parent / "__init__.py"
        assert api_init.exists(), "api/ must have an __init__.py"


class TestApiV1SubModuleFiles:
    """Verify all expected sub-module files exist (UND-34)."""

    @pytest.mark.parametrize("module_name", EXPECTED_MODULES)
    def test_submodule_file_exists(self, module_name):
        """Each expected sub-module .py file should exist."""
        path = V1_DIR / f"{module_name}.py"
        assert path.exists(), f"Missing sub-module file: {path}"

    @pytest.mark.parametrize("module_name", EXPECTED_MODULES)
    def test_submodule_is_valid_python(self, module_name):
        """Each sub-module should be parseable as valid Python."""
        path = V1_DIR / f"{module_name}.py"
        source = path.read_text()
        try:
            ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            pytest.fail(f"{module_name}.py has a syntax error: {exc}")


class TestApiV1RouterDefinitions:
    """Verify each sub-module defines a router via AST inspection (UND-34)."""

    @pytest.mark.parametrize("module_name", EXPECTED_MODULES)
    def test_submodule_defines_router_variable(self, module_name):
        """Each sub-module should assign a top-level 'router' variable."""
        path = V1_DIR / f"{module_name}.py"
        tree = ast.parse(path.read_text(), filename=str(path))
        router_assignments = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "router"
                for t in node.targets
            )
        ]
        assert len(router_assignments) > 0, (
            f"{module_name}.py should define a 'router' variable"
        )

    @pytest.mark.parametrize("module_name", EXPECTED_MODULES)
    def test_submodule_imports_api_router(self, module_name):
        """Each sub-module should import APIRouter from fastapi."""
        path = V1_DIR / f"{module_name}.py"
        tree = ast.parse(path.read_text(), filename=str(path))
        imports_api_router = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "fastapi":
                    for alias in node.names:
                        if alias.name == "APIRouter":
                            imports_api_router = True
        assert imports_api_router, (
            f"{module_name}.py should import APIRouter from fastapi"
        )

    @pytest.mark.parametrize("module_name", EXPECTED_MODULES)
    def test_router_has_api_v1_prefix(self, module_name):
        """Each router should be created with a /api/v1/ prefix (string literal check)."""
        path = V1_DIR / f"{module_name}.py"
        source = path.read_text()
        assert "/api/v1/" in source, (
            f"{module_name}.py router should include '/api/v1/' prefix"
        )


class TestApiV1MainAppImports:
    """Verify main.py imports all v1 sub-modules (UND-34)."""

    @pytest.fixture(scope="class")
    def main_source(self):
        path = ROOT / "src" / "theundercut" / "api" / "main.py"
        assert path.exists(), "api/main.py not found"
        return path.read_text()

    @pytest.fixture(scope="class")
    def main_tree(self, main_source):
        return ast.parse(main_source)

    def test_main_imports_analytics(self, main_source):
        """main.py should import the analytics sub-module."""
        assert "from theundercut.api.v1 import analytics" in main_source

    def test_main_imports_circuits(self, main_source):
        """main.py should import the circuits sub-module."""
        assert "from theundercut.api.v1 import circuits" in main_source

    def test_main_imports_race(self, main_source):
        """main.py should import the race sub-module."""
        assert "from theundercut.api.v1 import race" in main_source

    def test_main_imports_standings(self, main_source):
        """main.py should import the standings sub-module."""
        assert "from theundercut.api.v1 import standings" in main_source

    def test_main_imports_strategy(self, main_source):
        """main.py should import the strategy sub-module."""
        assert "from theundercut.api.v1 import strategy" in main_source

    def test_main_imports_testing(self, main_source):
        """main.py should import the testing sub-module."""
        assert "from theundercut.api.v1 import testing" in main_source

    def test_main_creates_fastapi_app(self, main_tree):
        """main.py should create a FastAPI app instance."""
        source = ast.dump(main_tree)
        assert "FastAPI" in source, "main.py should instantiate FastAPI()"

    def test_main_includes_routers(self, main_source):
        """main.py should include routers via app.include_router."""
        assert "include_router" in main_source, (
            "main.py should call app.include_router to mount v1 routers"
        )
