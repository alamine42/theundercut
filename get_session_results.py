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
import fastf1
import pandas as pd

from urllib.parse import urljoin
from datetime import date, datetime, timedelta
from config import Config
from utils import db_connect, select_query, run_query
from apis import ergast, openf1
from db import model, queries

def add_results(season, round, race_id, race_name, session_id, session_type, results_list, points_map_dict, download_only):

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
        positions_won_lost = int(starting_position) - int(finish_position)
        points_won_lost = int(points) - int(points_map_dict[starting_position]['standard'])
        alternate_points_won_lost = float(points_map_dict[finish_position]['alternate']) - float(points_map_dict[starting_position]['alternate'])

        if not download_only:
            
            logging.debug('Loading race analytics into DB ...')
            model.update_race_analytics(season, round, race_id, race_name, session_id, session_type, driver_id, first_name + ' ' + last_name, constructor_name, points, alternate_points, positions_won_lost, points_won_lost, alternate_points_won_lost)

def main(season_str=None, round_num_range='1-24', session='Race', download_only=False):

    logging.info('------------------')
    logging.info('The UnderCut - ETL')

    fastf1.set_log_level('ERROR')

    # Setting up query date
    query_year = datetime.now().year
    season_str = str(query_year) if season_str is None else season_str

    # If year is specified, use the provided selection, otherwise use the current year
    points_map_dict = model.get_points_map(Config.STANDARD_PTS_TEMPLATE_ID, Config.ALTERNATE_PTS_TEMPLATE_ID)

    round_num_start = 1
    round_num_end = 1

    if '-' in round_num_range:
        round_num_start = int(round_num_range.split('-')[0])
        round_num_end = int(round_num_range.split('-')[1])
    else:
        round_num_start = int(round_num_range)
        round_num_end = int(round_num_range)

    for round_num in range(round_num_start, round_num_end + 1):
    
        logging.info('-------')
        logging.info('Fetching web results for round %d %s ...' % (round_num, season_str))
        logging.info('-------')

        race_id = model.get_race_id(season_str, round_num)
        session_id = race_id + session

        if race_id is None:
            continue

        try:
            session_info = fastf1.get_session(int(season_str), round_num, session)
            session_info.load()
            # logging.info(session_info.laps)
        except Exception as e:
            logging.error('Error fetching session data!')
            logging.error(e)

        # model.update_latest_race(season_str=season_str, round_num=round_num)

            ## TODO ##
            ## 3. Validate the driver update
        race_name = session_info.event['OfficialEventName'].replace("'", "")

        for idx, result in session_info.results.iterrows():

            try:
                 finish_position = int(result['Position']) 
            except Exception as e:
                logging.error('NO DATA AVAILABLE')
                break

            driver_id = result['DriverId']

            model.add_or_update_driver(
                driver_id = driver_id,
                driver_number = int(result['DriverNumber']),
                first_name = result['FirstName'],
                last_name = result['LastName'],
                driver_code = result['Abbreviation'],
                constructor_id = result['TeamId'],
                constructor_name = result['TeamName'],
                nationality = result['CountryCode'],
                driver_url = result['HeadshotUrl']
                )

            logging.debug('Updating results for %s %s ...' % (result['FirstName'], result['LastName']))
            starting_position = 20 if int(result['GridPosition']) == 0 else int(result['GridPosition'])
            laps_completed = len(session_info.laps.pick_drivers(result['Abbreviation']))
            status = result['Status']
            points = int(result['Points'])
            fastest_lap_time = ''
            fastest_lap_rank = -1
            fastest_lap_number = -1
            time_to_leader_ms = -1
            time_to_leader_text = '' 

            if result['ClassifiedPosition'] == 'R':
                status = 'Retired'
                status_detailed = result['Status']
            else:
                status = result['Status']
                status_detailed = ''

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
                    status_detailed=status_detailed, 
                    fastest_lap_rank=fastest_lap_rank, 
                    fastest_lap_time=fastest_lap_time, 
                    fastest_lap_number=fastest_lap_number, 
                    time_to_leader_ms=time_to_leader_ms, 
                    time_to_leader_text=time_to_leader_text
                )

            alternate_points = float(points_map_dict[finish_position]['alternate'])
            positions_won_lost = int(starting_position) - int(finish_position)
            points_won_lost = int(points) - int(points_map_dict[starting_position]['standard'])
            alternate_points_won_lost = float(points_map_dict[finish_position]['alternate']) - float(points_map_dict[starting_position]['alternate'])

            if not download_only:
                
                logging.debug('Loading race analytics into DB ...')
                model.update_race_analytics(season_str, round_num, race_id, race_name, session_id, session, 
                    driver_id, result['FirstName'] + ' ' + result['LastName'], result['TeamName'], 
                    points, alternate_points, positions_won_lost, points_won_lost, alternate_points_won_lost)
        



    logging.info('All done.')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='The Undercut - ETL')
    parser.add_argument('-d', '--download_only', help='Download the file but do not load it into the DB.', action='store_true')
    parser.add_argument('-p', '--print', action='store_true', help='Specifies logging to command line instead of file')
    parser.add_argument('-l', '--log_level', type=str, action='store', help='Log level (INFO, DEBUG, ERROR)', default='INFO')
    parser.add_argument('-y', '--year', type=str, action='store', help='Specify the year for which to retrieve the meetings. Default is current year.')
    parser.add_argument('-r', '--round', type=str, action='store', help='Specify the meeting rounds. Year has to be specified. Example: 8-14 (Default: 1-24)', default='1-24')
    parser.add_argument('-s', '--session', type=str, action='store', help='Choose session type. Options are: Race, Qualifying, Sprint, Sprint Qualifying. Default is Race.', default='Race')

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

    fastf1.set_log_level('ERROR')

    main(season_str=args.year, round_num_range=args.round, session=args.session, download_only=args.download_only)
