from theundercut.models import Driver, DriverMetrics, Entry, Race, Season, Team
from theundercut.services.analytics import fetch_race_analytics
from tests.conftest import seed_sample_race


def test_fetch_race_analytics_returns_sections(db_session):
    seed_sample_race(db_session)

    payload = fetch_race_analytics(db_session, 2024, 1)

    assert payload["race"] == {"season": 2024, "round": 1}
    assert len(payload["laps"]) == 4
    assert len(payload["stints"]) == 2
    assert {grade["driver"] for grade in payload["driver_pace_grades"]} == {"VER", "HAM"}


def test_fetch_race_analytics_filters_drivers(db_session):
    seed_sample_race(db_session)

    payload = fetch_race_analytics(db_session, 2024, 1, drivers=["VER"])

    assert {lap["driver"] for lap in payload["laps"]} == {"VER"}
    assert {stint["driver"] for stint in payload["stints"]} == {"VER"}
    assert len(payload["driver_pace_grades"]) == 1
    assert payload["driver_pace_grades"][0]["driver"] == "VER"


def test_fetch_race_analytics_uses_driver_metrics(db_session):
    seed_sample_race(db_session)
    season = Season(year=2024, status="active")
    team = Team(name="Red Bull")
    driver = Driver(code="VER")
    db_session.add_all([season, team, driver])
    db_session.flush()
    race = Race(season_id=season.id, round_number=1, slug="2024-1")
    db_session.add(race)
    db_session.flush()
    entry = Entry(race_id=race.id, driver_id=driver.id, team_id=team.id)
    db_session.add(entry)
    db_session.flush()
    db_session.add(
        DriverMetrics(
            entry_id=entry.id,
            total_grade=88.5,
            consistency_score=0.7,
            team_strategy_score=0.65,
            racecraft_score=0.6,
            penalty_score=0.1,
        )
    )
    db_session.commit()

    payload = fetch_race_analytics(db_session, 2024, 1)
    assert payload["driver_pace_grades"][0]["source"] == "drive_grade_db"
    assert payload["driver_pace_grades"][0]["total_grade"] == 88.5
