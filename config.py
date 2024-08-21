import os
import sys
import json
from pprint import pprint

basedir = os.path.abspath(os.path.dirname(__file__))

if os.path.exists('config.env'):
    # print('Importing environment from .env file')
    for line in open('config.env'):
        var = line.strip().split('=')
        if len(var) == 2:
            os.environ[var[0]] = var[1].replace("\"", "")

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
    POSTGRES_USER = os.environ.get('POSTGRES_USER')
    POSTGRES_HOST = os.environ.get('POSTGRES_HOST')
    OPENF1_API_URL = 'https://api.openf1.org/v1/'
    OPENF1_API_MEETINGS_ENDPOINT = 'meetings'
    OPENF1_API_SESSIONS_ENDPOINT = 'sessions'
    OPENF1_API_DRIVERS_ENDPOINT = 'drivers'
    OPENF1_API_LAPS_ENDPOINT = 'laps'
    ERGAST_API_URL = 'https://ergast.com/api/f1/'
    LOG_FILE = 'etl_theundercut.log'