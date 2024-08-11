import time
import calendar
import os
import shutil
import csv
import psycopg2
import logging
import argparse
import queries
import uuid
import json
import requests
import hashlib

from urllib.parse import urljoin
from datetime import date, datetime, timedelta
from config import Config
from utils import db_connect, select_query, run_query

def get_meetings(query_year=None, query_start_dt=None):
    """ 
    Call the OpenF1 API Meetings Endpoint to get the list of meetings for a select year

    /meetings?year=YYYY

    """
    logging.debug('Retrieving list of meetings from OpenF1 for %s ...' % (query_year))
    meetings_url = urljoin(Config.OPENF1_API_URL, Config.OPENF1_API_MEETINGS_ENDPOINT)
    
    if query_start_dt is not None:
        meetings_url = meetings_url + '?date_start>' + str(query_start_dt)
    elif query_year is not None:
        meetings_url = meetings_url + '?year=' + str(query_year)

    logging.debug('URL: %s' % meetings_url)

    meetings_list = []
    try:
        
        response = requests.get(meetings_url)

        if response.status_code == 200:
            meetings_list = json.loads(response.text)
            logging.debug(meetings_list)

    except Exception as e:
        logging.error(meetings_url)
        raise e

    return meetings_list

def get_sessions(query_year=None, query_start_dt=None):
    """ 
    Call the OpenF1 API Sessions Endpoint to get the list of sessions for a select year

    /sessions?year=YYYY

    """
    logging.debug('Retrieving list of sessions from OpenF1 for %s ...' % (query_year))
    sessions_url = urljoin(Config.OPENF1_API_URL, Config.OPENF1_API_SESSIONS_ENDPOINT)
    
    if query_start_dt is not None:
        sessions_url = sessions_url + '?date_start>' + str(query_start_dt)
    elif query_year is not None:
        sessions_url = sessions_url + '?year=' + str(query_year)

    logging.info('URL: %s' % sessions_url)

    sessions_list = []
    try:
        
        response = requests.get(sessions_url)

        if response.status_code == 200:
            sessions_list = json.loads(response.text)
            logging.debug(sessions_list)

    except Exception as e:
        logging.error(sessions_url)
        raise e

    return sessions_list

def get_sessions_by_meeting(meeting_key):
    """ 
    Call the OpenF1 API Sessions Endpoint to get the list of sessions for a select meeting

    /sessions?meeting_key=

    """
    logging.debug('Retrieving list of sessions from OpenF1 for Meeting key %s ...' % (meeting_key))
    sessions_url = urljoin(Config.OPENF1_API_URL, Config.OPENF1_API_SESSIONS_ENDPOINT)
    sessions_url = sessions_url + '?meeting_key=' + str(meeting_key)
    logging.debug('URL: %s' % sessions_url)
    sessions_list = []
    try:
        
        response = requests.get(sessions_url)

        if response.status_code == 200:
            sessions_list = json.loads(response.text)
            logging.debug(sessions_list)

    except Exception as e:
        logging.error(sessions_url)
        raise e

    return sessions_list

def get_drivers_by_session(session_key):
    """ 
    Call the OpenF1 API Drivers Endpoint to get the list of drivers for a select session

    /drivers?session_key=

    """
    logging.debug('Retrieving list of drivers from OpenF1 for session key %s ...' % (session_key))
    drivers_url = urljoin(Config.OPENF1_API_URL, Config.OPENF1_API_DRIVERS_ENDPOINT)
    drivers_url = drivers_url + '?session_key=' + str(session_key)
    logging.debug('URL: %s' % drivers_url)
    drivers_list = []
    try:
        
        response = requests.get(drivers_url)

        if response.status_code == 200:
            drivers_list = json.loads(response.text)
            logging.debug(drivers_list)

    except Exception as e:
        logging.error(drivers_url)
        raise e

    return drivers_list

def load_meetings(meetings_list):

    current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for meeting in meetings_list:

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

        # Check ot see if the meeting exists, if not add it to the meetings table
        meetings_select_sql = queries.MEETING_SELECT_SQL % meeting['meeting_key']
        list_of_meetings = select_query(meetings_select_sql)
        if len(list_of_meetings) == 0:
            logging.info('Meeting %s with meeting key %s does not exist. Loading it into DB ...' % (meeting['meeting_name'], meeting['meeting_key']))
            meeting_add_sql = queries.MEETING_INSERT_SQL % (
                    meeting['meeting_key'],
                    meeting['meeting_name'],
                    meeting['meeting_official_name'].replace("'", "''"),
                    meeting['circuit_key'],
                    meeting['date_start'],
                    meeting['year'],
                    current_time_str
                )
            run_query(meeting_add_sql)

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
        driver_select_sql = queries.DRIVER_SELECT_SQL % (driver['full_name'], driver['country_code'])
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

        driver_select_sql = queries.DRIVER_SELECT_SQL % (driver['full_name'], driver['country_code'])
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


def main(filter_year=None, start_date=None,download_only=False):

    logging.info('------------------')
    logging.info('The UnderCut - ETL')

    # Setting up query date
    query_year = datetime.now().year
    query_start_dt = None

    # If year is specified, use the provided selection, otherwise use the current year
    if filter_year is not None:
        query_year = filter_year

    if start_date is not None:
        query_start_dt = start_date
        query_year = None

    logging.info('Getting meeting data for %s' % (query_year))
    meetings = get_meetings(query_year, query_start_dt)
    logging.info('Retrieved %d meetings ...' % (len(meetings)))

    if not download_only:
        logging.info('Loading meetings in DB ...')
        load_meetings(meetings)

    for meeting in meetings:
        logging.info('Getting session data for %s ...' % (meeting['meeting_name']))
        sessions = get_sessions_by_meeting(meeting['meeting_key'])
        logging.info('Retrieved %d sessions ...' % (len(sessions)))

        if not download_only:
            logging.info('Loading sessions in DB ...')
            load_sessions(sessions)

        for session in sessions:
            logging.info('Getting driver data for %s at %s ...' % (session['session_name'], meeting['meeting_name']))
            drivers = get_drivers_by_session(session['session_key'])
            logging.info('Retrieved %d drivers ...' % len(drivers))

            if not download_only:
                logging.info('Updating driver information in DB ...')
                update_drivers(drivers)

                logging.info('Complete. Loading session driver data ...')
                load_session_drivers(drivers, session['session_key'])


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

    main(filter_year=args.year, start_date=args.start_date, download_only=args.download_only)
