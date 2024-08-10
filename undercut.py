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

    /meetings?year=YYYY

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

    logging.info('Loading meetings in DB ...')
    load_meetings(meetings)

    logging.info('Getting session data for %s' % (query_year))
    sessions = get_sessions(query_year, query_start_dt)
    logging.info('Retrieved %d sessions ...' % (len(sessions)))

    logging.info('Loading sessions in DB ...')
    load_sessions(sessions)

    # conn = db_connect()
    # cur = conn.cursor()

    # logging.debug('Start %s, End %s, Load %s' % (data_start_dt, data_end_dt, data_load_dt))
    # latest_scores_filename = 'latest_scores.csv'
    
    # if not reload_last:
    #     os.remove(latest_scores_filename) if os.path.exists(latest_scores_filename) else logging.info('No scores file')

    #     logging.info('Fetching meeting data ...')
    #     meetings_list = get_list_of_meetings(data_start_dt, data_end_dt)
    #     logging.info('Retrieved %d meetings ...' % len(meetings_list))

    #     logging.info('Loading meetings to database ...')
    #     load_meetings(cur, meetings_list)

    #     for meeting in meetings_list:
    #         logging.debug(meeting)
    #         logging.info('Fetching athlete & results data for meeting %s ...' % meeting['id'])
    #         athletes_list = get_list_of_athletes(meeting['id'])
    #         logging.info('%d athletes logged a score for this meeting!' % len(athletes_list))
    #         logging.debug('Loading athletes to database ...')
    #         load_meeting_athletes(cur, meeting['id'], athletes_list)

    #     # old_scores_filename = locate_scores_files()
    #     # if old_scores_filename is not None:
    #     #     logging.debug('Renaming downloaded file from %s to %s ...' % (old_scores_filename, latest_scores_filename))
    #     #     shutil.move(old_scores_filename, latest_scores_filename)

    # else:
    #     logging.info('Reloading last downloaded scores file ...')

    # conn.commit()
    # cur.close()
    # conn.close()

    # List of archive game months
    # archives_response = get_player_game_archives(Config.CHESS_COM_USERNAME)
    # list_of_months_in_archive = json.loads(archives_response.text)
    # for month_url in list_of_months_in_archive['archives']:
    #     logging.debug(month_url)

    # Player Stats -- not needed
    # player_stats_response = get_player_stats(Config.CHESS_COM_USERNAME)
    # player_stats_json = json.loads(player_stats_response.text)
    # print(json.dumps(player_stats_json, indent=4))


    logging.info('All done.')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='The Undercut - ETL')
    parser.add_argument('-d', '--download_only', help='Download the file but do not load it into the DB.', action='store_true')
    parser.add_argument('-p', '--print', action='store_true', help='Specifies logging to command line instead of file')
    parser.add_argument('-l', '--log_level', type=str, action='store', help='Log level (INFO, DEBUG, ERROR)', default='INFO')
    parser.add_argument('-y', '--year', type=int, action='store', help='Specify the year for which to retrieve the meetings. Default is current year.')
    parser.add_argument('-s', '--start_date', type=str, action='store', help='Specifies the date after which the data is to be retrieved (i.e. all data since that date). SUPERCEDES the Year argument. Format: YYYY-MM-DD.')

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
