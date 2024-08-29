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
import requests
import hashlib

from urllib.parse import urljoin
from datetime import date, datetime, timedelta
from config import Config
from utils import db_connect, select_query, run_query
from apis import ergast

def is_valid_year(year):
  """Checks if the given year is a valid integer year."""

  # You can adjust the range if you have specific requirements
  return 1 <= year <= 9999

def add_or_update_circuit(circuit_info):

    circuit_id = circuit_info['@circuitId']
    circuit_name = circuit_info['CircuitName']
    locality = circuit_info['Location']['Locality']
    country = circuit_info['Location']['Country']
    
    # First, check to see if the circuit already exists
    logging.debug('Add/Updating Ciruit: %s - %s - %s - %s' % (circuit_id, circuit_name, locality, country))
    circuit_select_sql = queries.CIRCUIT_SELECT_SQL % circuit_id
    logging.debug('Checking if circuit exists ...')
    circuit_select_results = select_query(circuit_select_sql)
    logging.debug('Found %d results ...' % len(circuit_select_results))

    # creating a unique hash of the ciruit info
    concatenated_circuit_info = json.dumps(circuit_info)
    circuit_hash = hashlib.md5(concatenated_circuit_info.encode("utf-8")).hexdigest()

    if len(circuit_select_results) == 0:
    
        # It doesn't exist, adding it
        logging.debug('Adding the circuit ...')

        circuit_add_sql = queries.CIRCUIT_INSERT_SQL % (
                circuit_id,
                '',
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
                    '',
                    circuit_name,
                    country,
                    locality,
                    circuit_hash,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    circuit_id
                )
            run_query(circuit_update_sql)

def add_or_update_meeting(race_info):

    race_id = race_info['Circuit']['@circuitId'] + race_info['@season']
    season = race_info['@season']
    round = int(race_info['@round'])
    race_name = race_info['RaceName'] 
    race_official_name = ''
    race_date = race_info['Date']
    circuit_id = race_info['Circuit']['@circuitId']

    # First, check to see if the meeting already exists
    logging.debug('Add/Updating meeting: %s - %s' % (race_id, race_name))
    race_select_sql = queries.RACE_SELECT_SQL % race_id
    logging.debug('Checking if meeting exists ...')
    race_select_results = select_query(race_select_sql)
    logging.debug('Found %d results ...' % len(race_select_results))

    race_info_str = str(json.dumps(race_info))
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

def main(filter_year=None, download_only=False):

    logging.info('------------------')
    logging.info('The UnderCut - ETL')

    # Setting up query date
    if filter_year is None:
        query_year = datetime.now().year
    else:
        if not is_valid_year(args.year):
            logging.info('Please provide a valid year!')
            exit(0)

        query_year = filter_year

    logging.info('------------------')
    logging.info('New Season Setup: %s' % query_year)

    logging.info('Fetching & updating circuits ...')
    circuits_list = ergast.get_circuits(query_year)
    for circuit in circuits_list:
        add_or_update_circuit(circuit)

    logging.info('Fetching & updating races ...')
    race_list = ergast.get_schedule(query_year)
    for race in race_list:
        add_or_update_meeting(race)

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