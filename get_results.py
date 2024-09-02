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

def add_results(race_id, session_id, results_list, points_map_dict, download_only):

    for result in results_list:

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

        if not download_only:
            logging.debug('Updating driver information for %s %s ...' % (first_name, last_name))
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

        logging.debug('Updating results for %s %s ...' % (first_name, last_name))
        finish_position = int(result['@position'])
        starting_position = 20 if int(result['Grid']) == 0 else int(result['Grid'])
        laps_completed = int(result['Laps'])
        status = result['Status']['#text']
        points = int(result['@points'])
        fastest_lap_time = ''
        fastest_lap_rank = -1
        fastest_lap_number = -1
        time_to_leader_ms = -1
        time_to_leader_text = '' 

        if 'FastestLap' in result:
            if '@rank' in result['FastestLap']:
                fastest_lap_rank = int(result['FastestLap']['@rank'])
            fastest_lap_time = result['FastestLap']['Time']
            fastest_lap_number = int(result['FastestLap']['@lap'])

        if 'Time' in result:
            time_to_leader_ms = int(result['Time']['@millis'])
            time_to_leader_text = result['Time']['#text']

        if not download_only:
            model.add_or_update_result(
                race_id=race_id, 
                session_id=session_id, 
                driver_id=driver_id, 
                finish_position=finish_position, 
                starting_position=starting_position, 
                points=points, 
                laps_completed=laps_completed, 
                status=status, 
                fastest_lap_rank=fastest_lap_rank, 
                fastest_lap_time=fastest_lap_time, 
                fastest_lap_number=fastest_lap_number, 
                time_to_leader_ms=time_to_leader_ms, 
                time_to_leader_text=time_to_leader_text
            )

        alternate_points = float(points_map_dict[finish_position]['alternate'])
        positions_won_lost = int(finish_position) - int(starting_position)
        points_won_lost = int(points) - int(points_map_dict[starting_position]['standard'])
        alternate_points_won_lost = float(points_map_dict[finish_position]['alternate']) - float(points_map_dict[starting_position]['alternate'])

        if not download_only:
            
            logging.debug('Loading race analytics into DB ...')
            model.update_race_analytics(race_id, session_id, driver_id, points, alternate_points, positions_won_lost, points_won_lost, alternate_points_won_lost)

def main(season=None, round=None, download_only=False, update_cache=False):

    logging.info('------------------')
    logging.info('The UnderCut - ETL')

    # Setting up query date
    query_year = datetime.now().year

    # If year is specified, use the provided selection, otherwise use the current year
    points_map_dict = model.get_points_map(Config.STANDARD_PTS_TEMPLATE_ID, Config.ALTERNATE_PTS_TEMPLATE_ID)

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

        with open(cache_file_path, 'w+') as f:
            f.write(json.dumps(meeting_results, indent=4))

    else:
        logging.info('Fetching cached results for %s ...' % meeting_description)

        with open(cache_file_path, 'r') as f:
            meeting_results = json.load(f)

    logging.debug(json.dumps(meeting_results, indent=4))

    # Resetting the values for season & round just in case they weren't originally provided
    season = meeting_results['@season']
    round = int(meeting_results['@round'])

    circuit_id = meeting_results['Race']['Circuit']['@circuitId']
    circuit_name = meeting_results['Race']['Circuit']['CircuitName']
    locality = meeting_results['Race']['Circuit']['Location']['Locality']
    country = meeting_results['Race']['Circuit']['Location']['Country']
    race_id = circuit_id + season
    session_id = race_id + 'Race'

    logging.info('Updating circuit, meeting and session details for %s ...' % circuit_name)
    model.add_or_update_circuit(
            circuit_id=circuit_id,
            circuit_name=circuit_name,
            locality=locality,
            country=country
        )

    model.add_or_update_race(
            race_id=race_id,
            season=season,
            round=round,
            race_name=meeting_results['Race']['RaceName'],
            race_official_name='',
            race_date=meeting_results['Race']['Date'],
            race_time=meeting_results['Race']['Time'],
            circuit_id=circuit_id
        )

    model.add_or_update_session(
            session_id=session_id,
            session_type='Race',
            race_id=race_id,
            session_date=meeting_results['Race']['Date'],
            session_time=meeting_results['Race']['Time']
        )

    logging.info('Updating race results ...')
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

        if not download_only:
            logging.debug('Updating driver information for %s %s ...' % (first_name, last_name))
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

        logging.debug('Updating results for %s %s ...' % (first_name, last_name))
        finish_position = int(result['@position'])
        starting_position = 20 if int(result['Grid']) == 0 else int(result['Grid'])
        laps_completed = int(result['Laps'])
        status = result['Status']['#text']
        points = int(result['@points'])
        fastest_lap_time = ''
        fastest_lap_rank = -1
        fastest_lap_number = -1
        time_to_leader_ms = -1
        time_to_leader_text = '' 

        if 'FastestLap' in result:
            if '@rank' in result['FastestLap']:
                fastest_lap_rank = int(result['FastestLap']['@rank'])
            fastest_lap_time = result['FastestLap']['Time']
            fastest_lap_number = int(result['FastestLap']['@lap'])

        if 'Time' in result:
            time_to_leader_ms = int(result['Time']['@millis'])
            time_to_leader_text = result['Time']['#text']

        if not download_only:
            model.add_or_update_result(
                race_id=race_id, 
                session_id=session_id, 
                driver_id=driver_id, 
                finish_position=finish_position, 
                starting_position=starting_position, 
                points=points, 
                laps_completed=laps_completed, 
                status=status, 
                fastest_lap_rank=fastest_lap_rank, 
                fastest_lap_time=fastest_lap_time, 
                fastest_lap_number=fastest_lap_number, 
                time_to_leader_ms=time_to_leader_ms, 
                time_to_leader_text=time_to_leader_text
            )

        alternate_points = float(points_map_dict[finish_position]['alternate'])
        positions_won_lost = int(finish_position) - int(starting_position)
        points_won_lost = int(points) - int(points_map_dict[starting_position]['standard'])
        alternate_points_won_lost = float(points_map_dict[finish_position]['alternate']) - float(points_map_dict[starting_position]['alternate'])

        if not download_only:
            
            logging.debug('Loading race analytics into DB ...')
            model.update_race_analytics(race_id, session_id, driver_id, points, alternate_points, positions_won_lost, points_won_lost, alternate_points_won_lost)

    race_schedule = ergast.get_race_schedule(season, round)
    if 'Sprint' in race_schedule:    

        logging.info('Sprint Weekend! Getting sprint session data & results ...')

        cache_file_rel_path = 'data/' + season + '_' + str(round) + '_sprint.json'
        cache_file_path = os.path.join(current_dir, cache_file_rel_path)

        if not os.path.exists(cache_file_path):
            reload_from_web = True

        if reload_from_web:
            logging.info('Fetching web data for the Sprint session ...' )
            sprint_results = ergast.get_sprint_results(season, round)

            with open(cache_file_path, 'w+') as f:
                f.write(json.dumps(sprint_results, indent=4))

        else:
            logging.info('Fetching cached results for the Sprint session ...')

            with open(cache_file_path, 'r') as f:
                sprint_results = json.load(f)
        

        # logging.info(json.dumps(sprint_results))
        if not download_only:
            model.add_or_update_session(
                session_id=race_id + 'Sprint',
                session_type='Sprint',
                race_id=race_id,
                session_date=race_schedule['Sprint']['Date'],
                session_time=race_schedule['Sprint']['Time']
            )

        add_results(race_id, race_id + 'Sprint', sprint_results['Race']['SprintList']['SprintResult'], points_map_dict, download_only)


    # TODO 
    # 1. Handle future events
    # 3. Support getting results for all races in a season + collect historical data starting from 2020
    # 4. Build UI
    # 5. Deploy

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
