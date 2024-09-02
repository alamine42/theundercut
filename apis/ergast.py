import time
import calendar
import logging
import json
import requests
import xmltodict

from urllib.parse import urljoin
from config import Config

def request_ergast_data(url):
    response_data = None
    try:
        
        response = requests.get(url)

        if response.status_code == 200:
            response_data = xmltodict.parse(response.text)
            logging.debug(response_data)

    except Exception as e:
        logging.error(url)
        raise e

    return response_data

def get_circuits(query_year=None):
    """
    Call the Ergast API circuits endpoint to get the list of events for a select year.
    If no year is specified, the default behavior is to get the circuits for the current year.

    Example: https://ergast.com/api/f1/2024/circuits

    """
    logging.debug('Retrieving the circuits for %s ' % (query_year if query_year is not None else 'this year'))
    if query_year is None:
        circuits_url = urljoin(Config.ERGAST_API_URL, 'circuits')
    else:
        circuits_url = urljoin(Config.ERGAST_API_URL, str(query_year) + '/circuits')

    logging.debug('URL: %s' % circuits_url)

    circuits_dict = request_ergast_data(circuits_url)
    return circuits_dict['MRData']['CircuitTable']['Circuit']


def get_schedule(query_year=None):
    """
    Call the Ergast API race schedule endpoint to get the list of events for a select year.
    If no year is specified, the default behavior is to get the race schedule for the current year.

    Example: https://ergast.com/api/f1/2024

    """
    logging.debug('Retrieving the schedule for %s ' % (query_year if query_year is not None else 'this year'))
    if query_year is None:
        schedule_url = urljoin(Config.ERGAST_API_URL, 'current')
    else:
        schedule_url = urljoin(Config.ERGAST_API_URL, str(query_year))

    logging.debug('URL: %s' % schedule_url)

    schedule_dict = request_ergast_data(schedule_url)
    return schedule_dict['MRData']['RaceTable']['Race']

def get_race_schedule(season, round):
    """
    Call the Ergast API race schedule endpoint for a particular season + round.
    Figure out if there's a sprint race during that weekend.

    Example: https://ergast.com/api/f1/2024/5

    """
    logging.debug('Checking if round %d of season %s is a sprint weekend ...' % (round, season))
    race_schedule_url = urljoin(Config.ERGAST_API_URL, season + '/' + str(round))
    logging.debug('URL: %s' % race_schedule_url)
    race_schedule_results = request_ergast_data(race_schedule_url)
    return race_schedule_results['MRData']['RaceTable']['Race']

def get_race_results(year=None, round=None):
    """
    Call the Ergast API race results endpoint to get the winners.
    If no year is specified, the default behavior is to get the race schedule for the current year.

    Example: https://ergast.com/api/f1/2024/5/results

    """
    if year is not None and round is not None:
        results_url = urljoin(Config.ERGAST_API_URL, str(year) + '/' + str(round) + '/results')    
    else:
        results_url = urljoin(Config.ERGAST_API_URL, 'current/last/results')
    logging.debug('URL: %s' % results_url)

    results_dict = request_ergast_data(results_url)

    logging.debug(results_dict)
    
    return results_dict['MRData']['RaceTable']


def get_sprint_results(season, round):
    """
    Call the Ergast API Sprint results endpoint to get the winners.
    If no year is specified, the default behavior is to get the race schedule for the current year.

    Example: https://ergast.com/api/f1/2024/5/sprint

    """
    results_url = urljoin(Config.ERGAST_API_URL, str(season) + '/' + str(round) + '/sprint')
    logging.debug('URL: %s' % results_url)

    results_dict = request_ergast_data(results_url)

    logging.debug(results_dict)
    
    return results_dict['MRData']['RaceTable']