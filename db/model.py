import time
import calendar
import os
import shutil
import csv
import logging
import argparse
import queries
import uuid
import json
import hashlib

from datetime import date, datetime, timedelta
from config import Config
from utils import db_connect, select_query, run_query

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

def add_or_update_race(race_id, season, round, race_name, race_official_name, race_date, race_time, circuit_id):

    # First, check to see if the race already exists
    logging.debug('Add/Updating race: %s - %s' % (race_id, race_name))
    race_select_sql = queries.RACE_SELECT_SQL % race_id
    logging.debug('Checking if race exists ...')
    race_select_results = select_query(race_select_sql)
    logging.debug('Found %d results ...' % len(race_select_results))

    race_info_str = ''.join([race_id, season, str(round), race_name, race_official_name, race_date, race_time, circuit_id])
    race_hash = hashlib.md5(race_info_str.encode("utf-8")).hexdigest()
    
    if len(race_select_results) == 0:

        logging.debug('Race does not exist. Adding it ...')
        race_add_sql = queries.RACE_INSERT_SQL % (
            race_id, 
            season, 
            round, 
            race_name, 
            race_official_name, 
            race_date, 
            circuit_id, 
            race_hash, 
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        run_query(race_add_sql)

    else:
        if race_hash != race_select_results[0][7]:
            logging.info('Info for race %s %s has changed! Updating race ...' % (race_name, season))

            race_update_sql = queries.RACE_UPDATE_SQL % (
                season, 
                round, 
                race_name, 
                race_official_name, 
                race_date, 
                circuit_id, 
                race_hash, 
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                race_id
            )
            run_query(race_update_sql)

def add_or_update_session(session_type, race_id, session_date, session_time):
    
    session_id = race_id + session_type

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
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                session_id
            )
            run_query(session_update_sql)