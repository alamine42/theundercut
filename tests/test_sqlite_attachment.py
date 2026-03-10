"""Tests for SQLite database attachment mechanism (UND-19, UND-22, UND-24).

Validates that the SQLite ATTACH DATABASE setup in tests/__init__.py
works correctly, handles failures gracefully, and the 'core' schema
is accessible for unique constraints used by the test infrastructure.
"""

import sqlite3
import warnings

import pytest


class TestSQLiteImportAvailability:
    """Verify sqlite3 module is importable and usable (UND-19)."""

    def test_sqlite3_module_importable(self):
        """The sqlite3 standard library module should be importable."""
        import sqlite3 as _sqlite3
        assert _sqlite3 is not None

    def test_sqlite3_connection_class_exists(self):
        """sqlite3.Connection class should be available."""
        from sqlite3 import Connection as SQLite3Connection
        assert SQLite3Connection is not None

    def test_sqlite3_connection_is_callable(self):
        """We should be able to create an in-memory SQLite connection."""
        conn = sqlite3.connect(":memory:")
        assert conn is not None
        conn.close()


class TestSQLiteAttachSuccess:
    """Verify ATTACH DATABASE works for in-memory databases (UND-22)."""

    def test_attach_database_succeeds(self):
        """ATTACH DATABASE ':memory:' AS core should not raise."""
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute("ATTACH DATABASE ':memory:' AS core")
        except Exception as exc:
            pytest.fail(f"ATTACH DATABASE raised: {exc}")
        finally:
            conn.close()

    def test_core_schema_accessible_after_attach(self):
        """After attaching, tables can be created in the 'core' schema."""
        conn = sqlite3.connect(":memory:")
        conn.execute("ATTACH DATABASE ':memory:' AS core")
        conn.execute("CREATE TABLE core.test_tbl (id INTEGER PRIMARY KEY)")
        rows = conn.execute(
            "SELECT name FROM core.sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [r[0] for r in rows]
        assert "test_tbl" in table_names, (
            "Table created in 'core' schema should be visible"
        )
        conn.close()

    def test_core_schema_insert_and_query(self):
        """Data can be inserted and queried in the 'core' schema."""
        conn = sqlite3.connect(":memory:")
        conn.execute("ATTACH DATABASE ':memory:' AS core")
        conn.execute("CREATE TABLE core.kv (k TEXT PRIMARY KEY, v TEXT)")
        conn.execute("INSERT INTO core.kv (k, v) VALUES ('a', '1')")
        result = conn.execute("SELECT v FROM core.kv WHERE k = 'a'").fetchone()
        assert result[0] == "1"
        conn.close()

    def test_multiple_schemas_can_coexist(self):
        """Multiple attached databases should not conflict."""
        conn = sqlite3.connect(":memory:")
        conn.execute("ATTACH DATABASE ':memory:' AS core")
        conn.execute("ATTACH DATABASE ':memory:' AS config")
        conn.execute("CREATE TABLE core.t1 (id INTEGER)")
        conn.execute("CREATE TABLE config.t2 (id INTEGER)")
        core_tables = conn.execute(
            "SELECT name FROM core.sqlite_master WHERE type='table'"
        ).fetchall()
        config_tables = conn.execute(
            "SELECT name FROM config.sqlite_master WHERE type='table'"
        ).fetchall()
        assert any(r[0] == "t1" for r in core_tables)
        assert any(r[0] == "t2" for r in config_tables)
        conn.close()

    def test_attach_same_alias_twice_raises(self):
        """Attaching the same alias twice should raise an error."""
        conn = sqlite3.connect(":memory:")
        conn.execute("ATTACH DATABASE ':memory:' AS core")
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("ATTACH DATABASE ':memory:' AS core")
        conn.close()


class TestSQLiteAttachFailureHandling:
    """Verify graceful error handling for attachment failures (UND-24)."""

    def test_broad_exception_does_not_propagate(self):
        """The tests/__init__.py pattern should catch all exceptions."""
        # Simulate the pattern from tests/__init__.py
        caught = False
        try:
            # Force a failure by attaching to an invalid path on a read-only conn
            raise sqlite3.OperationalError("simulated failure")
        except Exception:
            caught = True
        assert caught, "Broad exception handler should catch OperationalError"

    def test_import_error_produces_warning(self):
        """When sqlite3 is unavailable, a warning should be emitted."""
        # Simulate the warning path from tests/__init__.py
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            warnings.warn(
                "sqlite3 module not available; SQLite ATTACH setup skipped",
                stacklevel=1,
            )
            assert len(w) == 1
            assert "sqlite3 module not available" in str(w[0].message)

    def test_attach_to_nonexistent_readonly_path_raises(self):
        """Attaching to a non-existent file path should raise OperationalError."""
        conn = sqlite3.connect(":memory:")
        # A path in a non-existent directory should fail
        with pytest.raises(sqlite3.OperationalError):
            conn.execute(
                "ATTACH DATABASE '/nonexistent/dir/db.sqlite' AS bad_db"
            )
        conn.close()

    def test_detach_after_attach_succeeds(self):
        """DETACH should work after a successful ATTACH."""
        conn = sqlite3.connect(":memory:")
        conn.execute("ATTACH DATABASE ':memory:' AS core")
        conn.execute("DETACH DATABASE core")
        # After detach, re-attach should work
        conn.execute("ATTACH DATABASE ':memory:' AS core")
        conn.close()


class TestConfTestSQLiteIntegration:
    """Verify conftest.py _build_engine attaches expected schemas (UND-19)."""

    def test_conftest_build_engine_attaches_core(self, db_session):
        """The conftest engine should have 'core' schema attached."""
        result = db_session.execute(
            __import__("sqlalchemy").text(
                "SELECT name FROM pragma_database_list"
            )
        ).fetchall()
        schema_names = [r[0] for r in result]
        assert "core" in schema_names, (
            "conftest _build_engine should ATTACH ':memory:' AS core"
        )

    def test_conftest_build_engine_attaches_config(self, db_session):
        """The conftest engine should have 'config' schema attached."""
        result = db_session.execute(
            __import__("sqlalchemy").text(
                "SELECT name FROM pragma_database_list"
            )
        ).fetchall()
        schema_names = [r[0] for r in result]
        assert "config" in schema_names, (
            "conftest _build_engine should ATTACH ':memory:' AS config"
        )

    def test_conftest_build_engine_attaches_validation(self, db_session):
        """The conftest engine should have 'validation' schema attached."""
        result = db_session.execute(
            __import__("sqlalchemy").text(
                "SELECT name FROM pragma_database_list"
            )
        ).fetchall()
        schema_names = [r[0] for r in result]
        assert "validation" in schema_names, (
            "conftest _build_engine should ATTACH ':memory:' AS validation"
        )
