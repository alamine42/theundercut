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
import fastf1
import pandas as pd

from urllib.parse import urljoin
from datetime import date, datetime, timedelta
from config import Config
from utils import db_connect, select_query, run_query
from db import model, queries

def is_valid_year(year):
  """Checks if the given year is a valid integer year."""

  # You can adjust the range if you have specific requirements
  return 1 <= year <= 9999

def get_circuit_id(circuit_short_name='Monza'):

    select_sql = queries.CIRCUIT_SELECT_USING_SHORTNAME_SQL % circuit_short_name
    select_results = select_query(select_sql)

    if len(select_results) == 0:
        return None
    else:
        return select_results[0][0]


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

    # -- IF A NEW CIRCUIT HAS BEEN ADDED TO THE SCHEDULE, ADD IT TO THE DB MANUALLY, SORRY BOSS --

    # logging.info('Fetching & updating circuits ...')
    # circuits_list = ergast.get_circuits(query_year)
    # for circuit in circuits_list:
    #     try:
    #         model.add_or_update_circuit(
    #             circuit_id=circuit['@circuitId'],
    #             circuit_name=circuit['CircuitName'],
    #             locality=circuit['Location']['Locality'],
    #             country=circuit['Location']['Country']
    #         )
    #     except Exception as e:
    #         logging.error('Error adding circuit: \n%s' % json.dumps(circuit))
    #         raise e

    logging.info('Fetching & updating races + sessions ...')
    schedule_df = fastf1.get_event_schedule(year=query_year)

    for idx, race in schedule_df.iterrows():

        if race['RoundNumber'] == 0:
            continue

        circuit_id = get_circuit_id(race['Location'])
        race_id = str(circuit_id) + str(query_year)
        logging.info('Loading round %d - %s' % (int(race['RoundNumber']), race['EventName']))

        if race['EventFormat'] == 'sprint_qualifying':
            logging.info('SPRINT WEEKEND!')

        logging.debug(race)
        if not download_only:
            try:
                model.add_or_update_race(
                    race_id_str = race_id,
                    season_str = str(query_year),
                    round_num = race['RoundNumber'],
                    race_name_str = str(race['EventName']),
                    race_official_name_str = str(race['OfficialEventName']),
                    race_date_str = str(race['EventDate'])[0:10],
                    race_time_str = str(race['Session5Date'])[11:16],
                    circuit_id_str = circuit_id
                )
            except Exception as e:
                logging.error('Error adding race: \n%s' % json.dumps(race))
                raise e

            for i in range(1, 6):
                session_index = 'Session' + str(i)
                session_date_index = session_index + 'DateUtc'

                try:
                    model.add_or_update_session(
                        session_id = race_id + race[session_index], 
                        session_type = race[session_index],
                        race_id = race_id,
                        session_date = str(race[session_date_index]).split(' ')[0],
                        session_time = str(race[session_date_index]).split(' ')[1],
                        season_str = str(query_year)
                    )
                except Exception as e:
                    logging.error('Error adding race: \n%s' % json.dumps(race))
                    raise e

        else:
            logging.info('Skipping DB ...')

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