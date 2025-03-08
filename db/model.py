import time
import calendar
import os
import shutil
import csv
import logging
import argparse
import uuid
import json
import hashlib

from datetime import date, datetime, timedelta
from config import Config
from db import queries
from utils import db_connect, select_query, run_query, get_function_parameters

def update_latest_race(season, circuit_id):

    race_id = circuit_id + season
    logging.debug('Setting %s as latest race ...' % race_id)

    clear_latest_meeting_flag_sql = queries.LATEST_RACE_CLEAR_SQL
    run_query(clear_latest_meeting_flag_sql)

    set_latest_meeting_flag_sql = queries.LATEST_RACE_SET_SQL % race_id
    run_query(set_latest_meeting_flag_sql)

def get_meeting(meeting_id):

    meeting_select_sql = queries.RACE_SELECT_SQL % meeting_id
    meeting_select_results = select_query(meeting_select_sql)
    return None if len(meeting_select_results) == 0 else meeting_select_results[0]

def get_points_map(standard_template_id=1, alternate_template_id=2):
    """
    Fetches a dictionary mapping of positions to points based on both the standard
    and the alternate points schemes in the db
    """
    pts_map_dict = {}

    standard_pts_map_sql = queries.POINTS_MAP_SELECT_SQL % (standard_template_id)
    standard_pts_map_results = select_query(standard_pts_map_sql)
    for result in standard_pts_map_results:
        if result[0] in pts_map_dict:
            pts_map_dict[result[0]]['standard'] = result[1]
        else:
            pts_map_dict[result[0]] = {}
            pts_map_dict[result[0]]['standard'] = result[1]

    alternate_pts_map_sql = queries.POINTS_MAP_SELECT_SQL % (alternate_template_id)
    alternate_pts_map_results = select_query(alternate_pts_map_sql)
    for result in alternate_pts_map_results:
        if result[0] in pts_map_dict:
            pts_map_dict[result[0]]['alternate'] = result[1]
        else:
            pts_map_dict[result[0]] = {}
            pts_map_dict[result[0]]['alternate'] = result[1]

    return pts_map_dict

def add_or_update_circuit(circuit_id, circuit_name, locality, country, circuit_short_name=''):

    # First, check to see if the circuit already exists
    logging.debug('Add/Updating Ciruit: %s - %s - %s - %s' % (circuit_id, circuit_name, locality, country))
    circuit_select_sql = queries.CIRCUIT_SELECT_SQL % circuit_id
    logging.debug('Checking if circuit exists ...')
    circuit_select_results = select_query(circuit_select_sql)
    logging.debug('Found %d results ...' % len(circuit_select_results))

    # creating a unique hash of the ciruit info
    concatenated_circuit_info = ''.join([circuit_id, circuit_name, locality, country, circuit_short_name])
    circuit_hash = hashlib.md5(concatenated_circuit_info.encode("utf-8")).hexdigest()

    if len(circuit_select_results) == 0:
    
        # It doesn't exist, adding it
        logging.debug('Adding the circuit ...')

        circuit_add_sql = queries.CIRCUIT_INSERT_SQL % (
                circuit_id,
                circuit_short_name,
                circuit_name,
                country,
                locality,
                circuit_hash,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
        run_query(circuit_add_sql)

    else:
        logging.debug('Circuit already exists. Checking if any info has changed ...')
        if circuit_hash != circuit_select_results[0][5]:
            logging.info('Info for circuit %s has changed! Updating circuit ...' % circuit_id)

            circuit_update_sql = queries.CIRCUIT_UPDATE_SQL % (
                    circuit_short_name,
                    circuit_name,
                    country,
                    locality,
                    circuit_hash,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    circuit_id
                )
            run_query(circuit_update_sql)

def add_or_update_race(race_id_str, season_str, round_num, race_name_str, race_official_name_str, race_date_str, race_time_str, circuit_id_str):

    # First, check to see if the race already exists
    logging.debug('Add/Updating race: %s - %s' % (race_id_str, race_name_str))
    race_select_sql = queries.RACE_SELECT_SQL % race_id_str
    logging.debug('Checking if race exists ...')
    race_select_results = select_query(race_select_sql)
    logging.debug('Found %d results ...' % len(race_select_results))

    race_info_str = ''.join([race_id_str, season_str, str(round_num), race_name_str, race_official_name_str, race_date_str, race_time_str, circuit_id_str])
    race_hash = hashlib.md5(race_info_str.encode("utf-8")).hexdigest()
    
    if len(race_select_results) == 0:

        logging.debug('Race does not exist. Adding it ...')
        race_add_sql = queries.RACE_INSERT_SQL % (
            race_id_str, 
            season_str, 
            round_num, 
            race_name_str, 
            race_official_name_str.replace("'", ""), 
            race_date_str, 
            circuit_id_str, 
            race_hash, 
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        run_query(race_add_sql)

    else:
        logging.debug('Race already exists. Checking if any info has changed ...')
        if race_hash != race_select_results[0][7]:
            logging.info('Info for race %s %s has changed! Updating race ...' % (race_name_str, season_str))

            race_update_sql = queries.RACE_UPDATE_SQL % (
                season_str, 
                round_num, 
                race_name_str, 
                race_official_name_str.replace("'", ""), 
                race_date_str, 
                circuit_id_str, 
                race_hash, 
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                race_id_str
            )
            run_query(race_update_sql)

def add_or_update_session(session_id, session_type, race_id, session_date, session_time, season_str):

    # First, check to see if the session already exists
    logging.debug('Add/Update session: %s - %s' % (race_id, session_type))
    session_select_sql = queries.SESSION_SELECT_SQL % session_id
    logging.debug('Checking if session exists ...')
    session_select_results = select_query(session_select_sql)
    logging.debug('Found %d results ...' % len(session_select_results))

    session_info_str = ''.join([session_type, race_id, session_date, session_time])
    session_hash = hashlib.md5(session_info_str.encode("utf-8")).hexdigest()

    if len(session_select_results) == 0:

        logging.debug('Session does not exist. Adding it ...')
        session_add_sql = queries.SESSION_INSERT_SQL % (
            session_id,
            race_id,
            session_type,
            session_date,
            session_time,
            session_hash,
            season_str,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        run_query(session_add_sql)

    else:
        if session_hash != session_select_results[0][5]:
            logging.info('Info for session %s of %s has changed! Updating session with id %s ...' % (session_type, race_id, session_id))

            session_update_sql = queries.SESSION_UPDATE_SQL % (
                race_id,
                session_type,
                session_date,
                session_time,
                session_hash,
                season_str,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                session_id
            )
            run_query(session_update_sql)

def add_or_update_driver(driver_id, driver_number, first_name, last_name, driver_code, constructor_id, constructor_name, date_of_birth=None, nationality=None, driver_url=None, constructor_url=None):

     # First, check to see if the driver already exists
    logging.debug('Add/Update driver: %s %s' % (first_name, last_name))
    driver_select_sql = queries.DRIVER_SELECT_SQL % driver_id
    logging.debug('Checking if driver exists ...')
    driver_select_results = select_query(driver_select_sql)
    logging.debug('Found %d results ...' % len(driver_select_results))

    driver_info_str = ''.join([driver_id, str(driver_number), first_name, last_name, driver_code, constructor_id, constructor_name, date_of_birth, nationality, driver_url, constructor_url])
    driver_hash = hashlib.md5(driver_info_str.encode("utf-8")).hexdigest()

    if len(driver_select_results) == 0:
        logging.debug('Driver does not exist. Adding them ...')
        driver_add_sql = queries.DRIVER_INSERT_SQL % (
            driver_id, 
            driver_number, 
            first_name, 
            last_name, 
            driver_code, 
            constructor_id, 
            constructor_name, 
            date_of_birth, 
            nationality, 
            driver_url, 
            constructor_url,
            driver_hash,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        run_query(driver_add_sql)
    else:
        logging.debug('Driver already exists. Checking if any info has changed ...')
        if driver_hash != driver_select_results[0][11]:
            logging.info('Info for driver %s %s has changed! Updating driver with id %s ...' % (first_name, last_name, driver_id))

            driver_update_sql = queries.DRIVER_UPDATE_SQL % (
                driver_number, 
                first_name, 
                last_name, 
                driver_code, 
                constructor_id, 
                constructor_name, 
                date_of_birth, 
                nationality, 
                driver_url, 
                constructor_url,
                driver_hash,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                driver_id
            )
            run_query(driver_update_sql)

def add_or_update_result(race_id, session_id, driver_id, finish_position, starting_position, points, laps_completed, status, fastest_lap_rank, fastest_lap_time=None, fastest_lap_number=None, time_to_leader_ms=None, time_to_leader_text=None):

    # First, check to see if the result already exists
    logging.debug('Add/Update result: %s - %s' % (session_id, driver_id))
    result_select_sql = queries.RESULT_SELECT_SQL % (race_id, session_id, driver_id)
    logging.debug('Checking if result exists ...')
    result_select_results = select_query(result_select_sql)
    logging.debug('Found %d results ...' % len(result_select_results))

    result_info_str = ''.join([race_id, session_id, driver_id, str(finish_position), str(starting_position), str(points), str(laps_completed), status, str(fastest_lap_rank), fastest_lap_time, str(fastest_lap_number), str(time_to_leader_ms), time_to_leader_text])
    result_hash = hashlib.md5(result_info_str.encode("utf-8")).hexdigest()

    if len(result_select_results) == 0:

        logging.debug('Result does not exist. Adding it ...')
        result_add_sql = queries.RESULT_INSERT_SQL % (
            race_id, 
            session_id, 
            driver_id, 
            finish_position, 
            points, 
            starting_position, 
            laps_completed, 
            status, 
            fastest_lap_rank, 
            fastest_lap_time, 
            fastest_lap_number, 
            time_to_leader_ms, 
            time_to_leader_text, 
            result_hash,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        run_query(result_add_sql)

    else:
        if result_hash != result_select_results[0][14]:
            logging.info('Info for %s result for %s has changed! Updating result ...' % (session_id, driver_id))

            result_update_sql = queries.RESULT_UPDATE_SQL % (
                race_id, 
                session_id, 
                driver_id, 
                finish_position, 
                points, 
                starting_position, 
                laps_completed, 
                status, 
                fastest_lap_rank, 
                fastest_lap_time, 
                fastest_lap_number, 
                time_to_leader_ms, 
                time_to_leader_text, 
                result_hash,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                result_select_results[0][0] # <-- this is the result id
            )
            run_query(result_update_sql)

def update_race_analytics(season, round, race_id, race_name, session_id, session_type, driver_id, driver_name, constructor_name, points, alternate_points, positions_won_lost, points_won_lost, alternate_points_won_lost):

    # First, cleanup any existing analytics for this race/session/driver combo
    analytics_cleanup_sql = queries.ANALYTICS_CLEANUP_SQL % (race_id, session_id, driver_id)
    run_query(analytics_cleanup_sql)

    # Second, load new analytics
    analytics_add_sql = queries.ANALYTICS_INSERT_SQL % (
        season, 
        round, 
        race_id, 
        race_name, 
        session_id, 
        session_type, 
        driver_id, 
        driver_name, 
        constructor_name, 
        points, 
        alternate_points, 
        positions_won_lost, 
        points_won_lost, 
        alternate_points_won_lost,
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    run_query(analytics_add_sql)


def is_sprint_weekend(season, round):

    sprint_select_query = queries.SPRINT_SELECT_SQL % (season, round)
    sprint_select_results = select_query(sprint_select_query)

    if len(sprint_select_results) == 0:
        return False
    
    if sprint_select_results[0][9] is not None:
        return True
    else:
        return False