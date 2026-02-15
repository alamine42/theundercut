from f1_drive_grade.data_sources.ergast import (
    build_weekend_descriptor,
    derive_form_metrics,
    extract_lap_deltas,
    extract_pit_laps,
    lap_time_to_seconds,
    slugify_race,
)


def make_race_payload() -> dict:
    return {
        "MRData": {
            "RaceTable": {
                "Races": [
                    {
                        "season": "2024",
                        "round": "1",
                        "raceName": "Sample GP",
                        "Circuit": {"circuitName": "Sample Circuit"},
                        "Results": [
                            {
                                "Driver": {
                                    "driverId": "alpha",
                                    "code": "ALP",
                                    "givenName": "Alex",
                                    "familyName": "Alpha",
                                },
                                "Constructor": {"name": "Team A"},
                                "grid": "2",
                                "position": "1",
                            },
                            {
                                "Driver": {
                                    "driverId": "beta",
                                    "code": "BET",
                                    "givenName": "Bea",
                                    "familyName": "Beta",
                                },
                                "Constructor": {"name": "Team B"},
                                "grid": "1",
                                "position": "2",
                            },
                        ],
                    }
                ]
            }
        }
    }


def make_lap_payload() -> dict:
    return {
        "MRData": {
            "RaceTable": {
                "Races": [
                    {
                        "Laps": [
                            {
                                "number": "1",
                                "Timings": [
                                    {"driverId": "alpha", "time": "1:30.000"},
                                    {"driverId": "beta", "time": "1:31.000"},
                                ],
                            },
                            {
                                "number": "2",
                                "Timings": [
                                    {"driverId": "alpha", "time": "1:29.500"},
                                    {"driverId": "beta", "time": "1:32.000"},
                                ],
                            },
                        ]
                    }
                ]
            }
        }
    }


def make_pit_payload() -> dict:
    return {
        "MRData": {
            "RaceTable": {
                "Races": [
                    {
                        "PitStops": [
                            {"driverId": "alpha", "lap": "10"},
                            {"driverId": "beta", "lap": "12"},
                            {"driverId": "beta", "lap": "32"},
                        ]
                    }
                ]
            }
        }
    }


def test_lap_deltas_compute_relative_offsets() -> None:
    payload = make_lap_payload()
    lap_map = extract_lap_deltas(payload)
    assert len(lap_map["alpha"]) == 2
    # alpha is faster than beta on both laps, so deltas should be negative
    assert all(delta < 0 for delta in lap_map["alpha"])
    assert all(delta > 0 for delta in lap_map["beta"])


def test_pit_map_groups_and_sorts() -> None:
    pit_map = extract_pit_laps(make_pit_payload())
    assert pit_map["beta"] == [12, 32]
    assert pit_map["alpha"] == [10]


def test_build_weekend_descriptor_shapes_driver_entries() -> None:
    race_payload = make_race_payload()
    lap_payload = make_lap_payload()
    pit_payload = make_pit_payload()
    weekend = build_weekend_descriptor(race_payload, lap_payload, pit_payload)
    assert weekend["race_name"] == "Sample GP"
    drivers = {driver["driver"]: driver for driver in weekend["drivers"]}
    assert "ALP" in drivers
    assert drivers["ALP"]["strategy"]["actual_pit_laps"] == [10]
    assert len(drivers["BET"]["lap_deltas"]) == 2


def test_form_metrics_respect_position_changes() -> None:
    metrics = derive_form_metrics([-0.2, 0.1, 0.05], grid=5, position=2)
    assert 0 <= metrics["consistency"] <= 1
    assert metrics["start_precision"] > 0.5


def test_slugify_race_handles_special_chars() -> None:
    assert slugify_race("São Paulo Grand Prix") == "são_paulo_grand_prix"


def test_lap_time_to_seconds() -> None:
    assert abs(lap_time_to_seconds("1:32.500") - 92.5) < 1e-9
