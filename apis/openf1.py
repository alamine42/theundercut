import time
import calendar
import logging
import json
import requests
import xmltodict

from urllib.parse import urljoin
from config import Config

def request_json_data(url):
    response_data = None
    try:
        
        response = requests.get(url)

        if response.status_code == 200:
            response_data = json.loads(response.text)
            logging.debug(response_data)

    except Exception as e:
        logging.error(url)
        raise e

    return response_data

def get_meeting(meeting_key=None):
    """ 
    Call the OpenF1 API Meetings Endpoint to get a specific meeting.

    https://api.openf1.org/v1/meetings?meeting_key=1229

    """

    meeting_url = urljoin(Config.OPENF1_API_URL, Config.OPENF1_API_MEETINGS_ENDPOINT)

    if meeting_key is None:
        logging.debug('Retrieving latest meeting from OpenF1 ...')
        meeting_url = meeting_url + '?meeting_key=latest'
    else:
        logging.debug('Retrieving meeting %d from OpenF1 ...' % meeting_key)
        meeting_url = meeting_url + '?meeting_key=%d' % meeting_key

    logging.debug('URL: %s' % meeting_url)

    return request_json_data(meeting_url)


def search_meetings(meeting_year=None, meeting_name=None):
    """ 
    UPDATE THE CODE LOGIC FOR THIS ONE
    """

    meeting_url = urljoin(Config.OPENF1_API_URL, Config.OPENF1_API_MEETINGS_ENDPOINT)

    if meeting_year is None or meeting_name is None:
        logging.debug('Retrieving latest meeting from OpenF1 ...')
        meeting_url = meeting_url + '?meeting_key=latest'
    else:
        logging.debug('Retrieving the %s %s meeting from OpenF1 ...' % (str(meeting_year), meeting_name))
        meeting_url = meeting_url + '?year=%s&meeting_name=%s' % (str(meeting_year), meeting_name)

    logging.debug('URL: %s' % meeting_url)

    return request_json_data(meeting_url)

def get_meetings_historical(query_year=None, query_start_dt=None):
    """ 
    Call the OpenF1 API Meetings Endpoint to get the list of meetings for a select year

    /meetings?year=YYYY

    """
    logging.debug('Retrieving list of meetings from OpenF1 for %s ...' % (query_year))
    meetings_url = urljoin(Config.OPENF1_API_URL, Config.OPENF1_API_MEETINGS_ENDPOINT)
    
    if query_start_dt is not None:
        meetings_url = meetings_url + '?date_start>' + str(query_start_dt)
    elif query_year is not None:
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

def get_sessions_historical(query_year=None, query_start_dt=None):
    """ 
    Call the OpenF1 API Sessions Endpoint to get the list of sessions for a select year

    /sessions?year=YYYY

    """
    logging.debug('Retrieving list of sessions from OpenF1 for %s ...' % (query_year))
    sessions_url = urljoin(Config.OPENF1_API_URL, Config.OPENF1_API_SESSIONS_ENDPOINT)
    
    if query_start_dt is not None:
        sessions_url = sessions_url + '?date_start>' + str(query_start_dt)
    elif query_year is not None:
        sessions_url = sessions_url + '?year=' + str(query_year)

    logging.info('URL: %s' % sessions_url)

    sessions_list = []
    try:
        
        response = requests.get(sessions_url)

        if response.status_code == 200:
            sessions_list = json.loads(response.text)
            logging.debug(sessions_list)

    except Exception as e:
        logging.error(sessions_url)
        raise e

    return sessions_list

def get_sessions_by_meeting(meeting_key):
    """ 
    Call the OpenF1 API Sessions Endpoint to get the list of sessions for a select meeting

    /sessions?meeting_key=

    """
    logging.debug('Retrieving list of sessions from OpenF1 for Meeting key %s ...' % (meeting_key))
    sessions_url = urljoin(Config.OPENF1_API_URL, Config.OPENF1_API_SESSIONS_ENDPOINT)
    sessions_url = sessions_url + '?meeting_key=' + str(meeting_key)
    logging.debug('URL: %s' % sessions_url)
    sessions_list = []
    try:
        
        response = requests.get(sessions_url)

        if response.status_code == 200:
            sessions_list = json.loads(response.text)
            logging.debug(sessions_list)

    except Exception as e:
        logging.error(sessions_url)
        raise e

    return sessions_list

def get_drivers_by_session(session_key):
    """ 
    Call the OpenF1 API Drivers Endpoint to get the list of drivers for a select session

    /drivers?session_key=

    """
    logging.debug('Retrieving list of drivers from OpenF1 for session key %s ...' % (session_key))
    drivers_url = urljoin(Config.OPENF1_API_URL, Config.OPENF1_API_DRIVERS_ENDPOINT)
    drivers_url = drivers_url + '?session_key=' + str(session_key)
    logging.debug('URL: %s' % drivers_url)
    drivers_list = []
    try:
        
        response = requests.get(drivers_url)

        if response.status_code == 200:
            drivers_list = json.loads(response.text)
            logging.debug(drivers_list)

    except Exception as e:
        logging.error(drivers_url)
        raise e

    return drivers_list

def get_session_lap_data(session_key):

    """ 
    Call the OpenF1 API Laps Endpoint to get the lap data for a select session

    /drivers?session_key=

    """
    logging.debug('Retrieving lap data from OpenF1 for session key %s ...' % (session_key))
    laps_url = urljoin(Config.OPENF1_API_URL, Config.OPENF1_API_LAPS_ENDPOINT)
    laps_url = laps_url + '?session_key=' + str(session_key)
    logging.debug('URL: %s' % laps_url)
    laps_data = request_json_data(laps_url)

    return laps_data
