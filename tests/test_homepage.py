"""Unit tests for homepage data service."""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import text

from theundercut.services.homepage import (
    get_current_season,
    get_latest_race,
    get_podium,
    get_homepage_data,
    _get_team_for_driver,
    _get_race_name,
)
from theundercut.models import LapTime


class TestGetCurrentSeason:
    """Tests for get_current_season function."""

    def test_returns_latest_season_with_data(self, db_session):
        """Should return the most recent season that has lap data."""
        # Add laps for 2024 and 2025
        db_session.add(LapTime(race_id="2024-1", driver="VER", lap=1, lap_ms=90000))
        db_session.add(LapTime(race_id="2025-5", driver="VER", lap=1, lap_ms=89000))
        db_session.commit()

        # Mock the PostgreSQL-specific query with SQLite-compatible version
        with patch.object(db_session, 'execute') as mock_execute:
            mock_result = MagicMock()
            mock_result.fetchone.return_value = (2025,)
            mock_execute.return_value = mock_result

            season = get_current_season(db_session)
            assert season == 2025

    def test_returns_default_when_no_data(self, db_session):
        """Should return 2024 as default when no lap data exists."""
        with patch.object(db_session, 'execute') as mock_execute:
            mock_result = MagicMock()
            mock_result.fetchone.return_value = None
            mock_execute.return_value = mock_result

            season = get_current_season(db_session)
            assert season == 2024


class TestGetLatestRace:
    """Tests for get_latest_race function."""

    def test_returns_most_recent_race(self, db_session):
        """Should return the race with highest round number for the season."""
        with patch.object(db_session, 'execute') as mock_execute:
            mock_result = MagicMock()
            mock_result.fetchone.return_value = ("2025-12", 12, 1277)
            mock_execute.return_value = mock_result

            race = get_latest_race(db_session, 2025)

            assert race is not None
            assert race["race_id"] == "2025-12"
            assert race["round"] == 12
            assert race["name"] == "British Grand Prix"
            assert race["season"] == 2025

    def test_returns_none_when_no_races(self, db_session):
        """Should return None when no race data exists for the season."""
        with patch.object(db_session, 'execute') as mock_execute:
            mock_result = MagicMock()
            mock_result.fetchone.return_value = None
            mock_execute.return_value = mock_result

            race = get_latest_race(db_session, 2026)
            assert race is None


class TestGetPodium:
    """Tests for get_podium function."""

    def test_returns_top_3_finishers(self, db_session):
        """Should return P1, P2, P3 based on laps completed and time."""
        # Seed race data - VER completes most laps with fastest time
        race_id = "2024-1"
        db_session.add_all([
            LapTime(race_id=race_id, driver="VER", lap=1, lap_ms=90000),
            LapTime(race_id=race_id, driver="VER", lap=2, lap_ms=89000),
            LapTime(race_id=race_id, driver="VER", lap=3, lap_ms=88000),
            LapTime(race_id=race_id, driver="HAM", lap=1, lap_ms=91000),
            LapTime(race_id=race_id, driver="HAM", lap=2, lap_ms=90000),
            LapTime(race_id=race_id, driver="HAM", lap=3, lap_ms=89500),
            LapTime(race_id=race_id, driver="LEC", lap=1, lap_ms=92000),
            LapTime(race_id=race_id, driver="LEC", lap=2, lap_ms=91000),
            LapTime(race_id=race_id, driver="LEC", lap=3, lap_ms=90000),
        ])
        db_session.commit()

        podium = get_podium(db_session, race_id)

        assert len(podium) == 3
        assert podium[0]["position"] == 1
        assert podium[0]["driver"] == "VER"
        assert podium[0]["team"] == "Red Bull"
        assert podium[1]["position"] == 2
        assert podium[2]["position"] == 3

    def test_returns_empty_list_for_missing_race(self, db_session):
        """Should return empty list when race has no data."""
        podium = get_podium(db_session, "9999-99")
        assert podium == []


class TestGetTeamForDriver:
    """Tests for driver-to-team mapping."""

    def test_2024_driver_mapping(self):
        """Should correctly map 2024 drivers to teams."""
        assert _get_team_for_driver("VER", "2024-1") == "Red Bull"
        assert _get_team_for_driver("HAM", "2024-1") == "Mercedes"
        assert _get_team_for_driver("LEC", "2024-1") == "Ferrari"
        assert _get_team_for_driver("NOR", "2024-1") == "McLaren"

    def test_2025_driver_mapping(self):
        """Should correctly map 2025 drivers to teams."""
        assert _get_team_for_driver("VER", "2025-1") == "Red Bull"
        assert _get_team_for_driver("HAM", "2025-1") == "Ferrari"  # Changed teams
        assert _get_team_for_driver("ANT", "2025-1") == "Mercedes"  # New driver
        assert _get_team_for_driver("LAW", "2025-1") == "Red Bull"  # Promoted

    def test_unknown_driver(self):
        """Should return 'Unknown' for unmapped drivers."""
        assert _get_team_for_driver("XXX", "2024-1") == "Unknown"


class TestGetRaceName:
    """Tests for race name lookup."""

    def test_known_race_names(self, db_session):
        """Should return correct race names for known rounds."""
        assert _get_race_name(db_session, 2024, 1) == "Bahrain Grand Prix"
        assert _get_race_name(db_session, 2024, 12) == "British Grand Prix"
        assert _get_race_name(db_session, 2025, 1) == "Australian Grand Prix"

    def test_unknown_round_fallback(self, db_session):
        """Should return 'Round X' for unknown rounds."""
        assert _get_race_name(db_session, 2024, 99) == "Round 99"


class TestGetHomepageData:
    """Tests for the combined homepage data function."""

    def test_returns_complete_data_structure(self, db_session):
        """Should return all homepage data in expected structure."""
        with patch('theundercut.services.homepage.get_current_season', return_value=2025):
            with patch('theundercut.services.homepage.get_latest_race', return_value={
                "race_id": "2025-12",
                "round": 12,
                "name": "British Grand Prix",
                "season": 2025,
            }):
                with patch('theundercut.services.homepage.get_podium', return_value=[
                    {"position": 1, "driver": "VER", "team": "Red Bull"},
                    {"position": 2, "driver": "NOR", "team": "McLaren"},
                    {"position": 3, "driver": "HAM", "team": "Ferrari"},
                ]):
                    data = get_homepage_data(db_session)

                    assert "season" in data
                    assert "latest_race" in data
                    assert "podium" in data
                    assert data["season"] == 2025
                    assert len(data["podium"]) == 3

    def test_handles_no_race_data(self, db_session):
        """Should handle case where no race data exists."""
        with patch('theundercut.services.homepage.get_current_season', return_value=2024):
            with patch('theundercut.services.homepage.get_latest_race', return_value=None):
                data = get_homepage_data(db_session)

                assert data["season"] == 2024
                assert data["latest_race"] is None
                assert data["podium"] == []
