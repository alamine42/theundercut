

# Ensure SQLite attachment for inline unique constraints
try:
    from sqlite3 import Connection as SQLite3Connection
    SQLite3Connection.execute("ATTACH DATABASE ':memory:' AS core")
except Exception:
    pass
