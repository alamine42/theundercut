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
    (meeting_key, meeting_name, meeting_official_name, circuit_key, date_start, year, last_updated_dt)
    VALUES 
    (%d, '%s', '%s', %d, '%s', %d, '%s');
"""

