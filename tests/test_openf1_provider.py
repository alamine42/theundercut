from __future__ import annotations

from f1_drive_grade.data_sources.openf1_provider import OpenF1Config, OpenF1Provider


class DummyOpenF1Provider(OpenF1Provider):
    def __init__(self) -> None:
        super().__init__(config=OpenF1Config())
        self._fixtures = {
            "sessions": [
                {
                    "session_key": 9001,
                    "round": 1,
                    "meeting_name": "Test Grand Prix",
                    "location": "Test Circuit",
                    "laps": 50,
                }
            ],
            "results": [
                {
                    "driver_code": "AAA",
                    "driver_number": 1,
                    "team_name": "Alpha GP",
                    "grid_position": 2,
                    "position": 1,
                    "laps": 50,
                    "status": "Finished",
                },
                {
                    "driver_code": "BBB",
                    "driver_number": 2,
                    "team_name": "Beta GP",
                    "grid_position": 1,
                    "position": 2,
                    "laps": 50,
                    "status": "Finished",
                },
            ],
            "laps": [
                {"driver_number": 1, "lap_number": 1, "lap_time": "90.0"},
                {"driver_number": 1, "lap_number": 2, "lap_time": "91.0"},
                {"driver_number": 2, "lap_number": 1, "lap_time": "92.0"},
                {"driver_number": 2, "lap_number": 2, "lap_time": "93.0"},
            ],
            "pit_stops": [
                {"driver_number": 1, "lap_number": 20},
                {"driver_number": 2, "lap_number": 22},
            ],
            "overtakes": [
                {
                    "overtaking_driver_number": 1,
                    "overtaken_driver_number": 2,
                    "lap_number": 30,
                    "location": "Test Circuit",
                    "duration": 3.5,
                }
            ],
        }

    def _get(self, endpoint: str, params: dict) -> list[dict]:  # type: ignore[override]
        return self._fixtures.get(endpoint, [])


def test_fetch_schedule_caches_session() -> None:
    provider = DummyOpenF1Provider()
    schedule = provider.fetch_schedule(2025)
    assert len(schedule) == 1
    assert schedule[0].race_name == "Test Grand Prix"
    meta = provider._session_cache_entry(2025, 1)
    assert meta["session_key"] == 9001


def test_fetch_weekend_shapes_driver_entries() -> None:
    provider = DummyOpenF1Provider()
    provider.fetch_schedule(2025)
    descriptor = provider.fetch_weekend(2025, 1)
    assert descriptor["race_name"] == "Test Grand Prix"
    drivers = {entry["driver"]: entry for entry in descriptor["drivers"]}
    assert set(drivers.keys()) == {"AAA", "BBB"}

    aaa_entry = drivers["AAA"]
    assert aaa_entry["strategy"]["actual_pit_laps"] == [20]
    assert aaa_entry["strategy"]["optimal_pit_laps"]
    assert aaa_entry["overtakes"], "OpenF1 overtakes should be injected"
    assert aaa_entry["overtakes"][0]["event_source"] == "openf1"
