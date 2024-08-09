import logging
from config import Config

def load_config(config_file='config.ini'):
    CONFIG = {}
    with open(config_file, 'r') as cfg:
        for cfg_entry in cfg:
            cfg_key, cfg_val = cfg_entry.split('=')
            CONFIG[cfg_key] = cfg_val.strip()
    return CONFIG

def db_connect():
    import psycopg2
    try:
        connect_str = "dbname='%s' user='%s' host='%s' password='%s'" % (
            Config.POSTGRES_USER, 
            Config.POSTGRES_USER,
            Config.POSTGRES_HOST, 
            Config.POSTGRES_PASSWORD
        )
        conn = psycopg2.connect(connect_str)
    except Exception as e:
        logging.error('Oops ... cannot connect to Posgres!')
        logging.error(e)

    return conn

def select_query(select_stmt):
    conn = db_connect()
    cursor = conn.cursor()
    select_results = []

    try:
        cursor.execute(select_stmt)
        select_results = cursor.fetchall()
    except Exception as e:
        logging.error('Error running select statement: \n%s' % select_stmt)

    cursor.close()
    conn.close()
    return select_results

def run_query(exec_stmt):
    conn = db_connect()
    cursor = conn.cursor()

    try:
        cursor.execute(exec_stmt)
    except Exception as e:
        logging.error('Error executing statement: \n%s' % exec_stmt)

    conn.commit()
    cursor.close()
    conn.close()

def enable_download_in_headless_chrome(driver, download_dir):
    """
    there is currently a "feature" in chrome where
    headless does not allow file download: https://bugs.chromium.org/p/chromium/issues/detail?id=696481
    This method is a hacky work-around until the official chromedriver support for this.
    Requires chrome version 62.0.3196.0 or above.
    """

    # add missing support for chrome "send_command"  to selenium webdriver
    driver.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')

    params = {'cmd': 'Page.setDownloadBehavior', 'params': {'behavior': 'allow', 'downloadPath': download_dir}}
    command_result = driver.execute("send_command", params)
    logging.debug("response from browser:")
    for key in command_result:
        logging.debug("result:" + key + ":" + str(command_result[key]))