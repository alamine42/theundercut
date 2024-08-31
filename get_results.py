import time
import calendar
import os
import shutil
import csv
import logging
import argparse
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
from db import model, queries

DRIVERS_DICT = {}
ANALYTICS_DICT = {}

def main(season=None, round=None, download_only=False, update_cache=False):

    logging.info('------------------')
    logging.info('The UnderCut - ETL')

    # Setting up query date
    query_year = datetime.now().year

    # If year is specified, use the provided selection, otherwise use the current year
    PTS_MAP_DICT = model.get_points_map(Config.STANDARD_PTS_TEMPLATE_ID, Config.ALTERNATE_PTS_TEMPLATE_ID)

    reload_from_web = False
    if update_cache:
        logging.info('Forced cache update selected. Reloading data from web.')
        reload_from_web = True

    if season is not None and round is not None:
        cache_file_name = 'data/' + season + '/' + round + '.json'
        meeting_description = 'round %d of the %s season' % (int(round), season)
    else:
        cache_file_name = 'data/latest.json'
        meeting_description = 'most recent meeting'

    if not os.path.exists(cache_file_name):
        reload_from_web = True

    if reload_from_web:
        logging.info('Fetching web results for %s ...' % meeting_description)
        meeting_results = ergast.get_race_results(season, round)
        logging.info(meeting_results)

        with open(cache_file_name, 'w+') as f:
            f.write(json.dumps(meeting_results))

    else:
        logging.info('Fetching cached results for %s ...' % meeting_description)

        with open(cache_file_name, 'r') as f:
            meeting_results = json.load(f)

    print(meeting_results)    
    # Resetting the values for season & round just in case they weren't originally provided
    season = meeting_results['@season']
    round = meeting_results['@round']

    circuit_id = meeting_results['Race']['Circuit']['@circuitId']
    circuit_name = meeting_results['Race']['Circuit']['CircuitName']
    locality = meeting_results['Race']['Circuit']['Location']['Locality']
    country = meeting_results['Race']['Circuit']['Location']['Country']

    model.add_or_update_circuit(
            circuit_id=circuit_id,
            circuit_name=circuit_name,
            locality=locality,
            country=country
        )

    # model.add_or_update_race()
    # for result in meeting_results:
    #     print(result)



    # Get meeting info from DB
    # Step 1 - Check if meeting exists in DB --> If not, then get meeting info from Ergast
    # Step 2 - Then check if circuit exists in DB --> if not, then get circuit info from Ergast
    # Step 3 - Add the circuit & the meeting & the sessions
    # Step 4 - Get the results --> add them to DB

    # meeting_info = queries.get_meeting(meeting_id)


    # # Getting Race and Qualifying Results from Ergast
    # meeting_results = ergast.get_race_results_from_ergast(meeting_details)

    # for result in meeting_results:
        
    #     driver_number = int(result['@number'])
    #     if driver_number not in DRIVERS_DICT:
    #         DRIVERS_DICT[driver_number] = {}

    #     DRIVERS_DICT[driver_number]['position'] = int(result['@position'])
    #     DRIVERS_DICT[driver_number]['starting_grid'] = 20 if int(result['Grid']) == 0 else int(result['Grid'])
    #     DRIVERS_DICT[driver_number]['laps_completed'] = int(result['Laps'])
    #     DRIVERS_DICT[driver_number]['status'] = result['Status']['#text']
    #     DRIVERS_DICT[driver_number]['points'] = int(result['@points'])

    #     if 'FastestLap' in result:
    #         if '@rank' in result['FastestLap']:
    #             DRIVERS_DICT[driver_number]['fastest_lap_rank'] = int(result['FastestLap']['@rank'])
    #         DRIVERS_DICT[driver_number]['fastest_lap_time'] = result['FastestLap']['Time']
    #         DRIVERS_DICT[driver_number]['fastest_lap_number'] = int(result['FastestLap']['@lap'])

    #     if 'Time' in result:
    #         DRIVERS_DICT[driver_number]['time_to_leader_ms'] = int(result['Time']['@millis'])
    #         DRIVERS_DICT[driver_number]['time_to_leader_text'] = result['Time']['#text']

    #     if driver_number not in ANALYTICS_DICT:
    #         ANALYTICS_DICT[driver_number] = {}

    #     ANALYTICS_DICT[driver_number]['name'] = DRIVERS_DICT[driver_number]['name']
    #     ANALYTICS_DICT[driver_number]['points'] = DRIVERS_DICT[driver_number]['points']
    #     ANALYTICS_DICT[driver_number]['alternate_points'] = PTS_MAP_DICT[DRIVERS_DICT[driver_number]['position']]['alternate']
    #     ANALYTICS_DICT[driver_number]['positions_won_lost'] = DRIVERS_DICT[driver_number]['position'] - DRIVERS_DICT[driver_number]['starting_grid']
    #     ANALYTICS_DICT[driver_number]['points_won_lost'] = DRIVERS_DICT[driver_number]['points'] - PTS_MAP_DICT[DRIVERS_DICT[driver_number]['starting_grid']]['standard']
    #     ANALYTICS_DICT[driver_number]['alternate_points_won_lost'] = PTS_MAP_DICT[DRIVERS_DICT[driver_number]['position']]['alternate'] - PTS_MAP_DICT[DRIVERS_DICT[driver_number]['starting_grid']]['alternate']

    # if not download_only:
    #     logging.info('Loading race session results into DB ...')
    #     add_session_results(meeting_details['meeting_id'], session['session_key'], DRIVERS_DICT)
    #     logging.info('Loading race analytics into DB ...')
    #     add_race_analytics(meeting_details['meeting_id'], session['session_key'], ANALYTICS_DICT)

    # logging.debug(json.dumps(DRIVERS_DICT, indent=4))
    # logging.debug(json.dumps(ANALYTICS_DICT, indent=4))

    logging.info('All done.')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='The Undercut - ETL')
    parser.add_argument('-d', '--download_only', help='Download the file but do not load it into the DB.', action='store_true')
    parser.add_argument('-u', '--update_cache', help='Reload cached data from source, if exists', action='store_true')
    parser.add_argument('-p', '--print', action='store_true', help='Specifies logging to command line instead of file')
    parser.add_argument('-l', '--log_level', type=str, action='store', help='Log level (INFO, DEBUG, ERROR)', default='INFO')
    parser.add_argument('-y', '--year', type=str, action='store', help='Specify the year for which to retrieve the meetings. Default is current year.')
    parser.add_argument('-r', '--round', type=str, action='store', help='Specify the meeting round. Year has to be specified.')
    # parser.add_argument('-m', '--meeting_id', type=str, action='store', help='Specifies the id for the meeting event desired.')

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

    main(season=args.year, round=args.round, download_only=args.download_only, update_cache=args.update_cache)
