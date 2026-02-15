from pathlib import Path

from theundercut.drive_grade import calibration_store
from theundercut.drive_grade.calibration import load_calibration_profile


def test_upsert_and_fetch_profile(tmp_path, session_factory, monkeypatch):
    monkeypatch.setattr(calibration_store, "SessionLocal", session_factory)
    profile_file = tmp_path / "custom.json"
    profile_file.write_text("""{\"name\": \"custom\", \"consistency_tolerance\": 5.5}""")

    stored_profile = calibration_store.upsert_profile_from_file(
        "custom", profile_file, activate=True
    )
    assert stored_profile.consistency_tolerance == 5.5

    fetched = calibration_store.fetch_profile_from_db("custom")
    assert fetched is not None
    assert fetched.name == "custom"
    assert fetched.consistency_tolerance == 5.5

    assert calibration_store.set_active_profile("custom")
    # load_calibration_profile should now read from DB instead of disk
    monkeypatch.setenv("DRIVE_GRADE_CALIBRATION_PROFILE", "custom")
    profile = load_calibration_profile()
    assert profile.name == "custom"
    assert profile.consistency_tolerance == 5.5
