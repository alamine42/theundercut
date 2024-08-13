SCHEDULE_SELECT_SQL = """
    SELECT *
    FROM tuc_schedule
    WHERE race_name = '%s'
"""


CIRCUIT_SELECT_SQL = """
    SELECT *
    FROM tuc_circuits
    WHERE circuit_key = %d
"""

CIRCUIT_INSERT_SQL = """
    INSERT INTO tuc_circuits
    (circuit_key, circuit_short_name, country_code, country_key, country_name, gmt_offset, location, last_updated_dt)
    VALUES 
    (%d, '%s', '%s', %d, '%s', '%s', '%s', '%s');
"""

MEETING_SELECT_SQL = """
    SELECT *
    FROM tuc_meetings
    WHERE meeting_key = %d
"""

MEETING_INSERT_SQL = """
    INSERT INTO tuc_meetings
    (meeting_key, meeting_name, meeting_official_name, meeting_round, circuit_key, date_start, year, last_updated_dt)
    VALUES 
    (%d, '%s', '%s', %d, %d, '%s', %d, '%s');
"""

SESSION_SELECT_SQL = """
    SELECT *
    FROM tuc_sessions
    WHERE session_key = %d
"""

SESSION_INSERT_SQL = """
    INSERT INTO tuc_sessions
    (session_key, meeting_key, circuit_key, session_name, session_type, date_start, date_end, year, last_updated_dt)
    VALUES 
    (%d, %d, %d, '%s', '%s', '%s', '%s', %d, '%s');
"""

DRIVER_SELECT_SQL = """
    SELECT *
    FROM tuc_drivers
    WHERE lower(full_name) = lower('%s')
"""

DRIVER_INSERT_SQL = """
    INSERT INTO tuc_drivers
    (driver_number, first_name, last_name, full_name, headshot_url, name_acronym, country_code, broadcast_name, team_color, team_name, driver_hash, last_updated_dt)
    VALUES 
    (%d, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');
"""

DRIVER_UPDATE_SQL = """
    UPDATE tuc_drivers
    SET 
        driver_number = %d,
        first_name = '%s',
        last_name = '%s',
        full_name = '%s',
        headshot_url = '%s',
        name_acronym = '%s',
        country_code = '%s',
        broadcast_name = '%s',
        team_color = '%s',
        team_name = '%s',
        driver_hash = '%s',
        last_updated_dt = '%s'
    WHERE
        driver_key = %d
"""

SESSION_DRIVER_SELECT_SQL = """
    SELECT *
    FROM tuc_session_drivers
    WHERE lower(full_name) = lower('%s')
    AND session_key = '%s'
    AND meeting_key = '%s'
"""

SESSION_DRIVERS_DELETE_SQL = """
    DELETE FROM tuc_session_drivers
    WHERE session_key = '%s'
"""

SESSION_DRIVER_INSERT_SQL = """
    INSERT INTO tuc_session_drivers
    (driver_key, session_key, meeting_key, team_name, team_color, driver_number, full_name, headshot_url, last_updated_dt)
    VALUES
    (%d, %d, %d, '%s', '%s', %d, '%s', '%s', '%s');
"""

RESULTS_CLEANUP_SQL = """
    DELETE FROM tuc_results
    WHERE meeting_key = %d and session_key = %d
"""

RESULT_INSERT_SQL = """
    INSERT INTO tuc_results
    (meeting_key, session_key, driver_key, position, points, grid, laps, status_id, status_text, fastest_lap_rank, last_updated_dt)
    VALUES
    (%d, %d, %d, '%s', %d, '%s', %d, %d, '%s', %d, '%s');
"""