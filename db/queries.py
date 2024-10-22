LATEST_RACE_CLEAR_SQL = """
    UPDATE tuc_schedule
    SET latest = False
"""

LATEST_RACE_SET_SQL = """
    UPDATE tuc_schedule
    SET latest = True 
    WHERE race_id = '%s'
"""


SCHEDULE_SELECT_SQL = """
    SELECT *
    FROM tuc_schedule
    WHERE race_name = '%s'
"""

CIRCUIT_CLEANUP_SQL = """
    TRUNCATE tuc_circuits;
"""

CIRCUIT_SELECT_SQL = """
    SELECT *
    FROM tuc_circuits
    WHERE circuit_id = '%s'
"""

CIRCUIT_INSERT_SQL = """
    INSERT INTO tuc_circuits
    (circuit_id, circuit_short_name, circuit_name, country_name, locality, circuit_hash, last_updated_dt)
    VALUES 
    ('%s', '%s', '%s', '%s', '%s', '%s', '%s');
"""

CIRCUIT_UPDATE_SQL = """
    UPDATE tuc_circuits
    SET 
        circuit_short_name = '%s',
        circuit_name = '%s',
        country_name = '%s',
        locality = '%s',
        circuit_hash = '%s',
        last_updated_dt = '%s'
    WHERE
        circuit_id = '%s'
"""

RACE_SELECT_SQL = """
    SELECT *
    FROM tuc_schedule
    WHERE race_id = '%s'
"""

RACE_INSERT_SQL = """
    INSERT INTO tuc_schedule
    (race_id, season, round, race_name, race_official_name, race_date, circuit_id, race_hash, last_updated_dt)
    VALUES
    ('%s', '%s', %d, '%s', '%s', '%s', '%s', '%s', '%s')
"""

RACE_UPDATE_SQL = """
    UPDATE tuc_schedule
    SET 
        season = '%s',
        round = %d,
        race_name = '%s',
        race_official_name = '%s',
        race_date = '%s',
        circuit_id = '%s',
        race_hash = '%s',
        last_updated_dt = '%s'
    WHERE
        race_id = '%s'
"""

SESSION_SELECT_SQL = """
    SELECT *
    FROM tuc_sessions
    WHERE session_id = '%s'
"""

SESSION_INSERT_SQL = """
    INSERT INTO tuc_sessions
    (session_id, race_id, session_type, session_date, session_time, session_hash, last_updated_dt)
    VALUES 
    ('%s', '%s', '%s', '%s', '%s', '%s', '%s');
"""

SESSION_UPDATE_SQL = """
    UPDATE tuc_sessions
    SET 
        race_id = '%s',
        session_type = '%s',
        session_date = '%s',
        session_time = '%s',
        session_hash = '%s',
        last_updated_dt = '%s'
    WHERE
        session_id = '%s'
"""

DRIVER_SELECT_SQL = """
    SELECT *
    FROM tuc_drivers
    WHERE driver_id = '%s'
"""

DRIVER_INSERT_SQL = """
    INSERT INTO tuc_drivers
    (driver_id, driver_number, first_name, last_name, driver_code, constructor_id, constructor_name, date_of_birth, nationality, driver_url, constructor_url, driver_hash, last_updated_dt)
    VALUES 
    ('%s', %d, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');
"""

DRIVER_UPDATE_SQL = """
    UPDATE tuc_drivers
    SET 
        driver_number=%d, 
        first_name='%s', 
        last_name='%s', 
        driver_code='%s', 
        constructor_id='%s', 
        constructor_name='%s', 
        date_of_birth='%s', 
        nationality='%s', 
        driver_url='%s', 
        constructor_url='%s',
        driver_hash='%s',
        last_updated_dt='%s'
    WHERE
        driver_id = '%s'
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

RESULT_SELECT_SQL = """
    SELECT *
    FROM tuc_results
    WHERE race_id = '%s' and session_id = '%s' and driver_id = '%s'
"""

RESULT_INSERT_SQL = """
    INSERT INTO tuc_results
    (race_id, session_id, driver_id, position, points, starting_grid, laps_completed, status, fastest_lap_rank, fastest_lap_time, fastest_lap_number, time_to_leader_ms, time_to_leader_text, result_hash, last_updated_dt)
    VALUES
    ('%s', '%s', '%s', %d, %d, %d, %d, '%s', %d, '%s', %d, %d, '%s', '%s', '%s');
"""

RESULT_UPDATE_SQL = """
    UPDATE tuc_results
    SET 
        race_id='%s', 
        session_id='%s', 
        driver_id='%s', 
        position=%d, 
        points=%d, 
        starting_grid=%d, 
        laps_completed=%d, 
        status='%s', 
        fastest_lap_rank=%d, 
        fastest_lap_time='%s',
        fastest_lap_number=%d,
        time_to_leader_ms=%d,
        time_to_leader_text='%s',
        result_hash='%s',
        last_updated_dt='%s'
    WHERE
        result_id = %d
"""

ANALYTICS_CLEANUP_SQL = """
    DELETE FROM tuc_race_analytics
    WHERE race_id = '%s' and session_id = '%s' and driver_id = '%s'
"""

ANALYTICS_INSERT_SQL = """
    INSERT INTO tuc_race_analytics
    (season, round, race_id, race_name, session_id, session_type, driver_id, driver_name, constructor_name, points, alternate_points, positions_won_lost, points_won_lost, alternate_points_won_lost, last_updated_dt)
    VALUES
    ('%s', %d, '%s', '%s', '%s', '%s', '%s', '%s', '%s', %d, %f, %d, %d, %f, '%s');
"""

POINTS_MAP_SELECT_SQL = """
    SELECT position, points::float as points
    FROM tuc_points_map
    WHERE mapping_template_id = %d
"""

SPRINT_SELECT_SQL = """
    SELECT sprint_date
    FROM tuc_schedule
    WHERE season = '%s' and round = '%s'
"""