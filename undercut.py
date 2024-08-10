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

def get_list_of_meetings(query_year=None):
    """ 
    Call the OpenF1 API Meetings Endpoint to get the list of meetings for a select year

    /meetings?year=YYYY

    """
    logging.debug('Retrieving list of meetings from OpenF1 for %s ...' % (query_year))
    meetings_url = urljoin(Config.OPENF1_API_URL, Config.OPENF1_API_MEETINGS_ENDPOINT)
    
    if query_year is not None:
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

        # meeting_data_str = '\',\''.join(
        #     [
        #         meeting['id'],
        #         meeting['date'],
        #         meeting['title'],
        #         meeting['description'],
        #         meeting['score_type'],
        #         meeting['results_link'],
        #         current_time_str
        #     ]
        # )
        # meeting_data_str = "'" + meeting_data_str + "'"

        # # Delete the meeting if it exists
        # try:
        #     cursor.execute(queries.WORKOUT_DELETE_SQL % meeting['id'])
        # except Exception as e:
        #     logging.error('Error deleting meeting!')
        #     raise e

        # # Insert the meeting
        # try:
        #     cursor.execute(queries.WORKOUT_INSERT_SQL % (Config.SUGARWOD_WORKOUT_DATA_HEADER, meeting_data_str))
        # except Exception as e:
        #     logging.error('Error inserting meeting!')
        #     raise e

def main(filter_year=None, download_only=False):

    logging.info('------------------')
    logging.info('The UnderCut - ETL')

    # Setting up query date
    query_year = datetime.now().year

    # If year is specified, use the provided selection, otherwise use the current year
    if filter_year is not None:
        query_year = filter_year

    logging.info('Getting meeting data for %s' % (query_year))
    meetings = get_list_of_meetings(query_year)
    logging.info('Retrieved %d meetings ...' % (len(meetings)))

    logging.info('Loading meetings in DB ...')
    load_meetings(meetings)

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

    main(filter_year=args.year, download_only=args.download_only)
