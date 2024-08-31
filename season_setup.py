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

from urllib.parse import urljoin
from datetime import date, datetime, timedelta
from config import Config
from utils import db_connect, select_query, run_query
from apis import ergast
from db import model, queries

def is_valid_year(year):
  """Checks if the given year is a valid integer year."""

  # You can adjust the range if you have specific requirements
  return 1 <= year <= 9999

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
        try:
            model.add_or_update_circuit(
                circuit_id=circuit['@circuitId'],
                circuit_name=circuit['CircuitName'],
                locality=circuit['Location']['Locality'],
                country=circuit['Location']['Country']
            )
        except Exception as e:
            logging.error('Error adding circuit: \n%s' % json.dumps(circuit))
            raise e

    logging.info('Fetching & updating races + sessions ...')
    race_list = ergast.get_schedule(query_year)
    for race in race_list:
        race_id = race['Circuit']['@circuitId'] + race['@season']
        logging.info('Loading round %d - %s ' % (int(race['@round']), race['RaceName']))
        try:
            model.add_or_update_race(
                race_id = race_id,
                season = race['@season'],
                round = int(race['@round']),
                race_name = race['RaceName'],
                race_official_name = '',
                race_date = race['Date'],
                race_time = race['Time'],
                circuit_id = race['Circuit']['@circuitId']
            )
        except Exception as e:
            logging.error('Error adding race: \n%s' % json.dumps(race))
            raise e

        session_type = 'Race'
        try:
            model.add_or_update_session(session_type, race_id, race['Date'], race['Time'])
            for session_type in ('FirstPractice', 'SecondPractice', 'ThirdPractice', 'Qualifying', 'Sprint'):
                if session_type in race:
                    model.add_or_update_session(session_type, race_id, race[session_type]['Date'], race[session_type]['Time'] if 'Time' in race[session_type] else '')
        except Exception as e:
            logging.error('Error adding %s session for race %s' % (session_type, race_id))
            raise e

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