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

    current_dir = os.path.dirname(__file__)
    if season is not None and round is not None:
        cache_file_rel_path = 'data/' + season + '_' + round + '.json'
        meeting_description = 'round %d of the %s season' % (int(round), season)
    else:
        cache_file_rel_path = 'data/latest.json'
        meeting_description = 'most recent meeting'
    cache_file_path = os.path.join(current_dir, cache_file_rel_path)

    if not os.path.exists(cache_file_path):
        reload_from_web = True

    if reload_from_web:
        logging.info('Fetching web results for %s ...' % meeting_description)
        meeting_results = ergast.get_race_results(season, round)
        # logging.info(meeting_results)

        with open(cache_file_path, 'w+') as f:
            f.write(json.dumps(meeting_results))

    else:
        logging.info('Fetching cached results for %s ...' % meeting_description)

        with open(cache_file_path, 'r') as f:
            meeting_results = json.load(f)

    # print(meeting_results)    
    # Resetting the values for season & round just in case they weren't originally provided
    season = meeting_results['@season']
    round = meeting_results['@round']

    circuit_id = meeting_results['Race']['Circuit']['@circuitId']
    circuit_name = meeting_results['Race']['Circuit']['CircuitName']
    locality = meeting_results['Race']['Circuit']['Location']['Locality']
    country = meeting_results['Race']['Circuit']['Location']['Country']

    logging.info('Updating circuit, meeting and session details ...')
    model.add_or_update_circuit(
            circuit_id=circuit_id,
            circuit_name=circuit_name,
            locality=locality,
            country=country
        )

    model.add_or_update_race(
            race_id=circuit_id+season,
            season=season,
            round=round,
            race_name=meeting_results['Race']['RaceName'],
            race_official_name='',
            race_date=meeting_results['Race']['Date'],
            race_time=meeting_results['Race']['Time'],
            circuit_id=circuit_id
        )

    model.add_or_update_session(
            session_type='Race',
            race_id=circuit_id+season,
            session_date=meeting_results['Race']['Date'],
            session_time=meeting_results['Race']['Time']
        )

    # TODO 
    # 2. Load results + figure out fastest lap
    # 3. Figure out sprint races

    for result in meeting_results['Race']['ResultsList']['Result']:

        logging.debug(result)
        
        driver_id = str(result['Driver']['GivenName']).lower() + '_' + result['Driver']['FamilyName'].lower()
        driver_number = int(result['Driver']['PermanentNumber'])
        first_name = result['Driver']['GivenName']
        last_name = result['Driver']['FamilyName']
        driver_code = result['Driver']['@code']
        driver_url = result['Driver']['@url']
        nationality = result['Driver']['Nationality']
        date_of_birth = result['Driver']['DateOfBirth']

        constructor_id = result['Constructor']['@constructorId']
        constructor_url = result['Constructor']['@url']
        constructor_name = result['Constructor']['Name']

        logging.info('Updating driver information for %s %s ...' % (first_name, last_name))
        model.add_or_update_driver(
            driver_id=driver_id, 
            driver_number=driver_number, 
            first_name=first_name, 
            last_name=last_name, 
            driver_code=driver_code, 
            constructor_id=constructor_id, 
            constructor_name=constructor_name, 
            date_of_birth=date_of_birth, 
            nationality=nationality, 
            driver_url=driver_url, 
            constructor_url=constructor_url
        )

        # DRIVERS_DICT[driver_id]['position'] = int(result['@position'])
        # DRIVERS_DICT[driver_id]['starting_grid'] = 20 if int(result['Grid']) == 0 else int(result['Grid'])
        # DRIVERS_DICT[driver_id]['laps_completed'] = int(result['Laps'])
        # DRIVERS_DICT[driver_id]['status'] = result['Status']['#text']
        # DRIVERS_DICT[driver_id]['points'] = int(result['@points'])

        # if 'FastestLap' in result:
        #     if '@rank' in result['FastestLap']:
        #         DRIVERS_DICT[driver_id]['fastest_lap_rank'] = int(result['FastestLap']['@rank'])
        #     DRIVERS_DICT[driver_id]['fastest_lap_time'] = result['FastestLap']['Time']
        #     DRIVERS_DICT[driver_id]['fastest_lap_number'] = int(result['FastestLap']['@lap'])

        # if 'Time' in result:
        #     DRIVERS_DICT[driver_id]['time_to_leader_ms'] = int(result['Time']['@millis'])
        #     DRIVERS_DICT[driver_id]['time_to_leader_text'] = result['Time']['#text']

        # if driver_id not in ANALYTICS_DICT:
        #     ANALYTICS_DICT[driver_id] = {}

        # ANALYTICS_DICT[driver_id]['name'] = DRIVERS_DICT[driver_id]['name']
        # ANALYTICS_DICT[driver_id]['points'] = DRIVERS_DICT[driver_id]['points']
        # ANALYTICS_DICT[driver_id]['alternate_points'] = PTS_MAP_DICT[DRIVERS_DICT[driver_id]['position']]['alternate']
        # ANALYTICS_DICT[driver_id]['positions_won_lost'] = DRIVERS_DICT[driver_id]['position'] - DRIVERS_DICT[driver_id]['starting_grid']
        # ANALYTICS_DICT[driver_id]['points_won_lost'] = DRIVERS_DICT[driver_id]['points'] - PTS_MAP_DICT[DRIVERS_DICT[driver_id]['starting_grid']]['standard']
        # ANALYTICS_DICT[driver_id]['alternate_points_won_lost'] = PTS_MAP_DICT[DRIVERS_DICT[driver_id]['position']]['alternate'] - PTS_MAP_DICT[DRIVERS_DICT[driver_id]['starting_grid']]['alternate']

    # if not download_only:
    #     logging.info('Loading race session results into DB ...')
    #     add_session_results(meeting_details['meeting_id'], session['session_key'], DRIVERS_DICT)
    #     logging.info('Loading race analytics into DB ...')
    #     add_race_analytics(meeting_details['meeting_id'], session['session_key'], ANALYTICS_DICT)

    # logging.info(json.dumps(DRIVERS_DICT, indent=4))
    # logging.info(json.dumps(ANALYTICS_DICT, indent=4))

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
