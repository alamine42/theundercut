from dataclasses import dataclass
from typing import List

from f1_drive_grade.data_sources.base import RaceDataProvider, RaceDescriptor
from f1_drive_grade.data_sources.multi_source import MultiSourceFetcher


@dataclass
class DummyProvider(RaceDataProvider):
    name: str
    available: bool
    should_fail: bool = False
    schedule_rounds: int = 2

    def is_available(self) -> bool:
        return self.available

    def fetch_schedule(self, season: int) -> List[RaceDescriptor]:
        if not self.available:
            return []
        if self.should_fail:
            raise RuntimeError("schedule error")
        return [
            RaceDescriptor(season=season, round=i + 1, race_name=f"Race {i+1}", circuit="", slug=f"race_{i+1}")
            for i in range(self.schedule_rounds)
        ]

    def fetch_weekend(self, season: int, round_number: int) -> dict:
        if self.should_fail:
            raise RuntimeError("race error")
        return {"season": season, "round": round_number, "race_name": f"Race {round_number}", "circuit": "", "drivers": []}


def test_fetcher_uses_first_available_provider() -> None:
    provider = DummyProvider(name="primary", available=True)
    fetcher = MultiSourceFetcher([provider])
    schedule = fetcher.fetch_schedule(2024)
    assert len(schedule) == 2
    race = fetcher.fetch_race(2024, 1)
    assert race["round"] == 1


def test_fetcher_falls_back_to_next_provider() -> None:
    failing = DummyProvider(name="fail", available=True, should_fail=True)
    backup = DummyProvider(name="ok", available=True)
    fetcher = MultiSourceFetcher([failing, backup])
    schedule = fetcher.fetch_schedule(2024)
    assert len(schedule) == 2
    race = fetcher.fetch_race(2024, 1)
    assert race["race_name"] == "Race 1"
