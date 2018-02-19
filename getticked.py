from datetime import datetime, timedelta
import requests
from pytz.tzinfo import StaticTzInfo
import pytz

import settings


# Timezone helpers

def is_dst(zonename):
    """
    Find out whether it's Daylight Saving Time in this timezone
    """
    tz = pytz.timezone(zonename)
    now = pytz.utc.localize(datetime.utcnow())
    return now.astimezone(tz).dst() != timedelta(0)


class OffsetTime(StaticTzInfo):
    """
    A dumb timezone based on offset such as +0530, -0600, etc.
    """
    def __init__(self, offset):
        hours = int(offset[:3])
        minutes = int(offset[0] + offset[3:])
        self._utcoffset = timedelta(hours=hours, minutes=minutes)


def load_datetime(value, dt_format):
    """
    Create timezone-aware datetime object
    """
    if dt_format.endswith('%z'):
        dt_format = dt_format[:-2]
        offset = value[-5:]
        value = value[:-5]
        if offset != offset.replace(':', ''):
            # strip : from HHMM if needed (isoformat() adds it between HH and MM)
            offset = '+' + offset.replace(':', '')
            value = value[:-1]
        return OffsetTime(offset).localize(datetime.strptime(value, dt_format))

    return datetime.strptime(value, dt_format)


def string_to_timestamp(input):
    """ Get datetime object from a string like:
    2018-02-23T14:30:00.000+0000
    """


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def pretty_print(item):
    """ Pretty print a todo item """
    formatted_item = '{}{}{}'.format(bcolors.OKBLUE, item['title'], bcolors.ENDC)
    if 'dueDateObject' in item:
        formatted_item = '{}{}{} '.format(bcolors.WARNING, item['dueDateObject'], bcolors.ENDC) + formatted_item

    print(formatted_item)


def get_all_items():
    login_data = settings.login_data
    login_url = 'https://api.ticktick.com/api/v2/user/signon?wc=true&remember=true'

    tasks_url = 'https://api.ticktick.com/api/v2/batch/check/0?_={}'.format(str(datetime.now()).split('.')[0])


    s = requests.session()

    s.post(login_url, json=login_data)

    response = s.get(tasks_url)
    #print(response)
    #print(response.json())

    for item in response.json()['syncTaskBean']['update']:
        if item['dueDate']:
            item['dueDateObject'] = load_datetime(item['dueDate'], '%Y-%m-%dT%H:%M:%S.000%z')
        pretty_print(item)


get_all_items()
