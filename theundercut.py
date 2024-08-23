import time
import calendar
import os
import shutil
import csv
# import psycopg2
import logging
import argparse
import queries
import uuid
import json
import requests
import hashlib
import xmltodict

from urllib.parse import urljoin
from datetime import date, datetime, timedelta
from config import Config
from utils import db_connect, select_query, run_query
from apis import ergast, openf1

DRIVERS_DICT = {}

def load_meeting(meeting):

    current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Check to see if the circuit exists, if not add it to the circuits table
    circuit_select_sql = queries.CIRCUIT_SELECT_SQL % meeting['circuit_key']
    list_of_circuits = select_query(circuit_select_sql)

    if len(list_of_circuits) == 0:
        logging.info('Circuit %s with circuit key %s does not exist! Loading it into DB ...' % (meeting['circuit_short_name'], meeting['circuit_key']))
        circuit_add_sql = queries.CIRCUIT_INSERT_SQL % (
                meeting['circuit_key'],
                meeting['circuit_short_name'],
                meeting['country_code'],
                meeting['country_key'],
                meeting['country_name'],
                meeting['gmt_offset'],
                meeting['location'],
                current_time_str
            )
        run_query(circuit_add_sql)

    # Check to see if the meeting is on the schedule
    schedule_select_sql = queries.SCHEDULE_SELECT_SQL % meeting['meeting_name']
    schedule_select_result = select_query(schedule_select_sql)
    if len(schedule_select_result) == 0:
        logging.info('Meeting %s does not exist on the schedule!' % meeting['meeting_name'])
        return (meeting, 'error')
    else:

        meeting['meeting_round'] = schedule_select_result[0][1]

        # Check ot see if the meeting exists, if not add it to the meetings table
        meetings_select_sql = queries.MEETING_SELECT_SQL % meeting['meeting_key']
        list_of_meetings = select_query(meetings_select_sql)
        if len(list_of_meetings) == 0:
            logging.debug('Meeting %s with meeting key %s does not exist. Loading it into DB ...' % (meeting['meeting_name'], meeting['meeting_key']))
            meeting_add_sql = queries.MEETING_INSERT_SQL % (
                    meeting['meeting_key'],
                    meeting['meeting_name'],
                    meeting['meeting_official_name'].replace("'", "''"),
                    meeting['meeting_round'],
                    meeting['circuit_key'],
                    meeting['date_start'],
                    meeting['year'],
                    current_time_str
                )
            run_query(meeting_add_sql)
        else:
            logging.debug('Meeting %s with meeting key %s exists already. Skipping load ...' % (meeting['meeting_name'], meeting['meeting_key']))

        return (meeting, 'success')

def load_sessions(sessions_list):

    current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for session in sessions_list:

        # Check to see if the circuit exists, if not add it to the circuits table
        session_select_sql = queries.SESSION_SELECT_SQL % session['session_key']
        list_of_sessions = select_query(session_select_sql)

        if len(list_of_sessions) == 0:
            logging.info('Session with session key %s does not exist! Loading it into DB ...' % (session['session_key']))
            session_add_sql = queries.SESSION_INSERT_SQL % (
                    session['session_key'],
                    session['meeting_key'],
                    session['circuit_key'],
                    session['session_name'],
                    session['session_type'],
                    session['date_start'],
                    session['date_end'],
                    session['year'],
                    current_time_str
                )
            run_query(session_add_sql)

def update_drivers(drivers_list):

    current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for driver in drivers_list:

        concatenated_driver_info = ''.join([str(val) for (key, val) in driver.items() \
            if key in ('full_name', 'country_code', 'driver_number', 'headshot_url', 'name_acronym', 'team_name')])
        driver_hash = hashlib.md5(concatenated_driver_info.encode("utf-8")).hexdigest()

        # Check to see if the circuit exists, if not add it to the circuits table
        driver_select_sql = queries.DRIVER_SELECT_SQL % (driver['full_name'])
        list_of_drivers = select_query(driver_select_sql)

        if len(list_of_drivers) == 0:
            logging.info('Driver %s does not exist! Adding them into DB ...' % (driver['full_name']))

            # Create a hash for the driver to track changes in info
            driver_add_sql = queries.DRIVER_INSERT_SQL % (
                    driver['driver_number'],
                    driver['first_name'],
                    driver['last_name'],
                    driver['full_name'],
                    driver['headshot_url'],
                    driver['name_acronym'],
                    driver['country_code'],
                    driver['broadcast_name'],
                    driver['team_colour'],
                    driver['team_name'],
                    driver_hash,
                    current_time_str
                )
            logging.debug(driver_add_sql)
            run_query(driver_add_sql)
        else:

            if driver_hash != list_of_drivers[0][11]: # driver ifno is returned in a tuple, the driver_hash field is in the 12th slot
                logging.info('Info for driver %s has changed! Updating driver ...' % driver['full_name'])

                driver_update_sql = queries.DRIVER_UPDATE_SQL % (
                        driver['driver_number'],
                        driver['first_name'],
                        driver['last_name'],
                        driver['full_name'],
                        driver['headshot_url'],
                        driver['name_acronym'],
                        driver['country_code'],
                        driver['broadcast_name'],
                        driver['team_colour'],
                        driver['team_name'],
                        driver_hash,
                        current_time_str,
                        list_of_drivers[0][0]
                    )
                run_query(driver_update_sql)

def load_session_drivers(drivers_list, session_key):
    current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    session_cleanup_sql = queries.SESSION_DRIVERS_DELETE_SQL % session_key
    run_query(session_cleanup_sql)

    for driver in drivers_list:

        driver_select_sql = queries.DRIVER_SELECT_SQL % (driver['full_name'])
        list_of_drivers = select_query(driver_select_sql)

        if len(list_of_drivers) == 0:
            logging.info('Something odd happened. Driver %s does not exist ...' % driver['full_name'])
        else:
            driver_key = list_of_drivers[0][0]

            session_driver_add_sql = queries.SESSION_DRIVER_INSERT_SQL % (
                driver_key,
                driver['session_key'],
                driver['meeting_key'],
                driver['team_name'],
                driver['team_colour'],
                driver['driver_number'],
                driver['full_name'],
                driver['headshot_url'],
                current_time_str
            )
            run_query(session_driver_add_sql)

def identify_key_sessions(sessions_list):
    race_session_key = 0
    sprint_session_key = 0
    qualifying_session_key = 0
    for session in sessions_list:
        if session['session_name'] == 'Qualifying':
            qualifying_session_key = session['session_key']
        elif session['session_name'] == 'Race':
            race_session_key = session['session_key']
        elif session['session_name'] == 'Sprint':
            sprint_qualifying_session_key = session['session_key']
    return (race_session_key, qualifying_session_key, sprint_qualifying_session_key)

def add_session_results(meeting_key, session_key, results_dict):
    current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Step 1 -- clean up any prior existing results for this session
    results_cleanup_sql = queries.RESULTS_CLEANUP_SQL % (meeting_key, session_key)
    run_query(results_cleanup_sql)

    for driver_num, driver_result in results_dict.items():
        # Find the driver
        driver_select_sql = queries.SESSION_DRIVER_SELECT_SQL % (driver_result['name'], session_key, meeting_key)
        driver_select_result = select_query(driver_select_sql)
        
        if len(driver_select_result) > 0:
            driver_key = driver_select_result[0][0]
            result_add_sql = queries.RESULT_INSERT_SQL % (
                    meeting_key,
                    session_key,
                    driver_key,
                    int(driver_result['position']),
                    int(driver_result['points']),
                    driver_result['starting_grid'],
                    int(driver_result['laps_completed']),
                    driver_result['status'],
                    int(driver_result['fastest_lap_rank']),
                    driver_result['fastest_lap_time'],
                    int(driver_result['fastest_lap_number']),
                    int(driver_result['time_to_leader_ms']),
                    driver_result['time_to_leader_text'],
                    current_time_str
                )
            run_query(result_add_sql)

def get_race_data_from_openf1(filter_year=None, start_date=None, download_only=False, meeting_key=False):

    logging.info('------------------')
    logging.info('The UnderCut - Open F1 based')

    # Setting up query date
    query_year = datetime.now().year
    query_start_dt = None

    # If year is specified, use the provided selection, otherwise use the current year
    if filter_year is not None:
        query_year = filter_year

    meeting_info = openf1.get_meeting(meeting_key)

    meeting_info, load_result = load_meeting(meeting_info[0])

    if load_result == 'success':

        logging.info('Getting session data for %s ...' % (meeting_info['meeting_name']))
        sessions = openf1.get_sessions_by_meeting(meeting_info['meeting_key'])
        logging.info('Retrieved %d sessions ...' % (len(sessions)))

        race_session_key, qualifying_session_key = identify_key_sessions(sessions)
        logging.debug('Race session key: %d -- Qualifying session key: %d' % (race_session_key, qualifying_session_key))

        if not download_only:
            logging.info('Loading sessions in DB ...')
            load_sessions(sessions)

        for session in sessions:
            
            if session['session_key'] not in (race_session_key, qualifying_session_key):
                continue

            # Getting session driver data
            logging.info('Getting driver data for %s at %s ...' % (session['session_name'], meeting_info['meeting_name']))
            drivers = openf1.get_drivers_by_session(session['session_key'])
            logging.info('Retrieved %d drivers ...' % len(drivers))

            for driver in drivers:
                if driver['driver_number'] not in DRIVERS_DICT:
                    DRIVERS_DICT[driver['driver_number']] = {
                        'name': driver['first_name'] + ' '  + driver['last_name'],
                        'laps_completed': 0,
                        'status': 'DNF',
                        'fastest_lap_time': 1000,
                        'fastest_lap_of_race': 0,
                        'points': 0
                    }

            if not download_only:
                logging.info('Updating driver information in DB ...')
                update_drivers(drivers)

                logging.info('Complete. Loading session driver data for %s at %s ...' % (session['session_name'], meeting_info['meeting_name']))
                load_session_drivers(drivers, session['session_key'])

            
            if session['session_key'] == race_session_key:

                # Getting Race info from Open F1
                lap_data = openf1.get_session_lap_data(session['session_key'])
                max_laps = lap_data[-1]['lap_number']
                logging.info('This race has %d laps ...' % max_laps)
                
                driver_finishing_status = {}
                fastest_lap_time = 1000
                fastest_lap_driver_num = -1

                print(lap_data[0])

                for lap in lap_data:
                    if lap['driver_number'] not in driver_finishing_status.keys():
                        driver_finishing_status[lap['driver_number']] = lap['lap_number']
                    elif lap['lap_number'] > driver_finishing_status[lap['driver_number']]:
                        driver_finishing_status[lap['driver_number']] = lap['lap_number']

                    DRIVERS_DICT[lap['driver_number']]['laps_completed'] = lap['lap_number']

                    if lap['lap_duration'] is not None:
                        if lap['lap_duration'] < DRIVERS_DICT[lap['driver_number']]['fastest_lap_time']:
                            DRIVERS_DICT[lap['driver_number']]['fastest_lap_time'] = lap['lap_duration']

                    if lap['lap_number'] >= 0.9 * max_laps:
                        DRIVERS_DICT[lap['driver_number']]['status'] = 'Finished'

                    if lap['lap_duration'] is not None:
                        if lap['lap_duration'] < fastest_lap_time:
                            fastest_lap_time = lap['lap_duration']
                            fastest_lap_driver_num = lap['driver_number']

                logging.info(driver_finishing_status)
                logging.info('Fastest lap belongs to driver id %d with a lap time of %s.' % (fastest_lap_driver_num, str(fastest_lap_time)))
                DRIVERS_DICT[fastest_lap_driver_num]['fastest_lap_of_race'] = 1
                logging.debug(json.dumps(DRIVERS_DICT, sort_keys=True, indent=4))

    else:
        logging.info('Failed to load meeting info ...')

    logging.info('All done.')

def main(filter_year=None, start_date=None, download_only=False, meeting_key=False):

    logging.info('------------------')
    logging.info('The UnderCut - ETL')

    # Setting up query date
    query_year = datetime.now().year
    query_start_dt = None

    # If year is specified, use the provided selection, otherwise use the current year

    if meeting_key is not None:
        meeting_list = openf1.get_meeting(meeting_key)
    elif filter_year is not None:
        query_year = filter_year
        meeting_list = openf1.get_meetings_historical(query_year=filter_year)
    else:
        meeting_list = openf1.get_meeting()

    for meeting in meeting_list:
        meeting_details, load_result = load_meeting(meeting)
        
        logging.debug(meeting_details)

        if load_result == 'success':

            logging.info('Getting session data for %s ...' % (meeting_details['meeting_name']))
            sessions = openf1.get_sessions_by_meeting(meeting_details['meeting_key'])
            logging.info('Retrieved %d sessions ...' % (len(sessions)))

            # race_session_key, qualifying_session_key, spring = identify_key_sessions(sessions)
            # logging.debug('Race session key: %d -- Qualifying session key: %d' % (race_session_key, qualifying_session_key))

            if not download_only:
                logging.info('Loading sessions in DB ...')
                load_sessions(sessions)

            for session in sessions:
                
                if session['session_name'] not in ('Race', 'Sprint'):
                    continue

                # Getting session driver data
                logging.info('Getting driver data for %s at %s ...' % (session['session_name'], meeting_details['meeting_name']))
                drivers = openf1.get_drivers_by_session(session['session_key'])
                logging.info('Retrieved %d drivers ...' % len(drivers))

                for driver in drivers:
                    if driver['driver_number'] not in DRIVERS_DICT:
                        DRIVERS_DICT[driver['driver_number']] = {
                            'name': driver['first_name'] + ' '  + driver['last_name'],
                            'laps_completed': 0,
                            'status': 'DNF',
                            'position': 20,
                            'points': 0,
                            'starting_grid': -1,
                            'fastest_lap_rank': 0,
                            'fastest_lap_time': 1000,
                            'fastest_lap_number': -1,
                            'time_to_leader_ms': 1000000000,
                            'time_to_leader_text': '',
                        }

                if not download_only:
                    logging.info('Updating driver information in DB ...')
                    update_drivers(drivers)

                    logging.info('Complete. Loading session driver data for %s at %s ...' % (session['session_name'], meeting_details['meeting_name']))
                    load_session_drivers(drivers, session['session_key'])
                
                if session['session_name'] == 'Race':

                    # Getting Race and Qualifying Results from Ergast
                    logging.info('Getting Race session results ...')
                    meeting_results = ergast.get_race_results_from_ergast(meeting_details)
                    logging.debug(meeting_results)

                elif session['session_name'] == 'Sprint':
                    # Getting Spring results from Ergast
                    logging.info('Getting Sprint session results ...')
                    meeting_results = ergast.get_sprint_results_from_ergast(meeting_details)
                    logging.debug(meeting_results)

                else:
                    continue

                for result in meeting_results:

                    DRIVERS_DICT[int(result['@number'])]['position'] = result['@position']
                    DRIVERS_DICT[int(result['@number'])]['starting_grid'] = result['Grid']
                    DRIVERS_DICT[int(result['@number'])]['laps_completed'] = result['Laps']
                    DRIVERS_DICT[int(result['@number'])]['status'] = result['Status']['#text']
                    DRIVERS_DICT[int(result['@number'])]['points'] = result['@points']

                    if 'FastestLap' in result:
                        if '@rank' in result['FastestLap']:
                            DRIVERS_DICT[int(result['@number'])]['fastest_lap_rank'] = result['FastestLap']['@rank']
                        DRIVERS_DICT[int(result['@number'])]['fastest_lap_time'] = result['FastestLap']['Time']
                        DRIVERS_DICT[int(result['@number'])]['fastest_lap_number'] = result['FastestLap']['@lap']

                    if 'Time' in result:
                        DRIVERS_DICT[int(result['@number'])]['time_to_leader_ms'] = result['Time']['@millis']
                        DRIVERS_DICT[int(result['@number'])]['time_to_leader_text'] = result['Time']['#text']

                if not download_only:
                    logging.info('Loading race session results into DB ...')
                    add_session_results(meeting_details['meeting_key'], session['session_key'], DRIVERS_DICT)

                logging.debug(json.dumps(DRIVERS_DICT, indent=4))

        else:
            logging.info('Failed to load meeting info ...')

    logging.info('All done.')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='The Undercut - ETL')
    parser.add_argument('-d', '--download_only', help='Download the file but do not load it into the DB.', action='store_true')
    parser.add_argument('-p', '--print', action='store_true', help='Specifies logging to command line instead of file')
    parser.add_argument('-l', '--log_level', type=str, action='store', help='Log level (INFO, DEBUG, ERROR)', default='INFO')
    parser.add_argument('-y', '--year', type=int, action='store', help='Specify the year for which to retrieve the meetings. Default is current year.')
    parser.add_argument('-s', '--start_date', type=str, action='store', help='Specifies the date after which the data is to be retrieved (i.e. all data since that date). SUPERCEDES the Year argument. Format: YYYY-MM-DD.')
    parser.add_argument('-m', '--meeting_key', type=int, action='store', help='Specifies the key for the meeting desired.')

    args = parser.parse_args()
    log_format = '%(levelname)s:%(asctime)s:%(message)s'

    if args.log_level == 'DEBUG':
        log_level = logging.DEBUG
    elif args.log_level == 'ERROR':
        log_level = logging.ERROR
    else:
        log_level = logging.INFO

    if args.print:
        logging.basicConfig(format=log_format, level=log_level)
    else:
        logging.basicConfig(format=log_format, level=log_level, filename=Config.LOG_FILE)

    main(filter_year=args.year, start_date=args.start_date, download_only=args.download_only, meeting_key=args.meeting_key)
