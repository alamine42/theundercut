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
    

def get_race_results(meeting_info):
    """
    Call the Ergast API race results endpoint to get the winners.
    If no year is specified, the default behavior is to get the race schedule for the current year.

    Example: https://ergast.com/api/f1/2024/5/results

    """
    logging.debug('Retrieving the race results for %s ' % meeting_info['meeting_name'])
    results_url = urljoin(Config.ERGAST_API_URL, str(meeting_info['year']) + '/' + str(meeting_info['meeting_round']) + '/results')
    logging.debug('URL: %s' % results_url)

    results_dict = request_ergast_data(results_url)

    logging.debug(results_dict)
    
    return results_dict['MRData']['RaceTable']['Race']['ResultsList']['Result']


def get_sprint_results(meeting_info):
    """
    Call the Ergast API Sprint results endpoint to get the winners.
    If no year is specified, the default behavior is to get the race schedule for the current year.

    Example: https://ergast.com/api/f1/2024/5/sprint

    """
    logging.debug('Retrieving the Sprint results for %s ' % meeting_info['meeting_name'])
    results_url = urljoin(Config.ERGAST_API_URL, str(meeting_info['year']) + '/' + str(meeting_info['meeting_round']) + '/sprint')
    logging.debug('URL: %s' % results_url)

    results_dict = request_ergast_data(results_url)

    logging.debug(results_dict)
    
    return results_dict['MRData']['RaceTable']['Race']['SprintList']['SprintResult']