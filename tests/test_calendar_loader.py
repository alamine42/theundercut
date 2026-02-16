"""Tests for calendar_loader adapter."""
import pytest
from theundercut.adapters.calendar_loader import _normalize_openf1


def test_normalize_openf1_excludes_preseason_testing():
    """Pre-season testing sessions (Day 1, Day 2, etc.) should be filtered out."""
    rows = [
        # Pre-season testing (meeting 1228)
        {"session_name": "Day 1", "meeting_key": 1228, "date_start": "2024-02-21T10:00:00Z", "date_end": "2024-02-21T12:00:00Z", "year": 2024},
        {"session_name": "Day 2", "meeting_key": 1228, "date_start": "2024-02-22T10:00:00Z", "date_end": "2024-02-22T12:00:00Z", "year": 2024},
        {"session_name": "Day 3", "meeting_key": 1228, "date_start": "2024-02-23T10:00:00Z", "date_end": "2024-02-23T12:00:00Z", "year": 2024},
        # Actual race weekend (meeting 1229)
        {"session_name": "Practice 1", "meeting_key": 1229, "date_start": "2024-02-29T10:00:00Z", "date_end": "2024-02-29T12:00:00Z", "year": 2024},
        {"session_name": "Qualifying", "meeting_key": 1229, "date_start": "2024-03-01T14:00:00Z", "date_end": "2024-03-01T16:00:00Z", "year": 2024},
        {"session_name": "Race", "meeting_key": 1229, "date_start": "2024-03-02T14:00:00Z", "date_end": "2024-03-02T16:00:00Z", "year": 2024},
    ]

    df = _normalize_openf1(rows)

    # Testing sessions should be excluded
    assert "Day 1" not in df["session_type"].values
    assert "Day 2" not in df["session_type"].values
    assert "Day 3" not in df["session_type"].values

    # Race weekend sessions should be included
    assert "Practice 1" in df["session_type"].values
    assert "Qualifying" in df["session_type"].values
    assert "Race" in df["session_type"].values

    # Round 1 should be the actual race, not testing
    assert df["round"].min() == 1
    assert set(df[df["round"] == 1]["session_type"]) == {"Practice 1", "Qualifying", "Race"}
