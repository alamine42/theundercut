from theundercut.services import cache


def test_analytics_cache_key_sorts_drivers():
    key = cache.analytics_cache_key(2024, 1, ["VER", "HAM", "VER"])
    assert key == "analytics:v1:2024:1:HAM,VER"


def test_invalidate_analytics_cache_deletes_matching(monkeypatch):
    class DummyRedis:
        def __init__(self):
            self.deleted = []
            self.keys = {
                "analytics:v1:2024:1:all": "payload",
                "analytics:v1:2024:1:HAM": "filtered",
                "analytics:v1:2024:2:all": "other",
            }

        def scan_iter(self, match):
            # simplistic glob match for the test
            prefix = match.rstrip("*")
            for key in list(self.keys):
                if key.startswith(prefix):
                    yield key

        def delete(self, *keys):
            self.deleted.extend(keys)
            for key in keys:
                self.keys.pop(key, None)

    dummy = DummyRedis()
    monkeypatch.setattr(cache, "redis_client", dummy)

    cache.invalidate_analytics_cache(2024, 1)
    assert set(dummy.deleted) == {"analytics:v1:2024:1:all", "analytics:v1:2024:1:HAM"}
    assert "analytics:v1:2024:2:all" in dummy.keys  # untouched
