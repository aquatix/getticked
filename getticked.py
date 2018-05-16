from datetime import datetime, timedelta
import requests
from pytz.tzinfo import StaticTzInfo
import pytz
from tzlocal import get_localzone

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


# Date/time formatting

def datetime_to_string(timestamp, dt_format='%Y-%m-%d %H:%M:%S'):
    """
    Format datetime object to string
    """
    return timestamp.strftime(dt_format)


def pretty_date(datetime):
    """ Convert a datetime object into a nicely readable string """
    if datetime_to_string(datetime, dt_format='%H:%M') == '00:00':
        # all-day event; TODO: better check? Items have 'isAllDay' boolean.
        return datetime_to_string(datetime, dt_format='%Y-%m-%d')
    return datetime_to_string(datetime, dt_format='%Y-%m-%d %H:%M')


# Output

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'

    DARKGRAY = '\033[90m'
    YELLOW = '\033[33m'
    WHITE = '\033[97m'

    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def pretty_print(item, color=bcolors.OKBLUE):
    """ Pretty print a todo item """
    formatted_item = '{}{}{}'.format(color, item['title'].strip(), bcolors.ENDC)
    if 'dueDateObject' in item:
        formatted_item = '{begin}{message: <{width}}{end} '.format(begin=bcolors.WARNING, message=pretty_date(item['dueDateObject'].astimezone(get_localzone())), width=17, end=bcolors.ENDC) + formatted_item

    if item['reminder'] and not item['remindTime']:
        formatted_item += ' {}⏰{}'.format(bcolors.WHITE, bcolors.ENDC)

    if item['remindTime']:
        formatted_item += '  {}⏰{}{}'.format(bcolors.WARNING, pretty_date(item['remindTimeObject'].astimezone(get_localzone())), bcolors.ENDC)

    if item['repeatFlag']:
        formatted_item += ' {}🔃{}'.format(bcolors.WHITE, bcolors.ENDC)

    formatted_item += ' {} {}{}'.format(bcolors.DARKGRAY, item['projectName'], bcolors.ENDC)

    print(formatted_item)


def print_section(section, items, color=bcolors.OKBLUE):
    print()
    print('{}== {} ======{}'.format(bcolors.BOLD, section.upper(), bcolors.ENDC))
    print()
    for item in items:
        pretty_print(item, color)
    if items:
        # Provide some padding after the list
        print()


# Data handling

def make_projects_list(projects):
    result = {}
    for project in projects:
        result[project['id']] = project['name']
    return result


def get_date_sortkey(item):
    return item['dueDate']


def get_order_sortkey(item):
    return item['sortOrder']


def create_lists(items, project_names):
    items_due = []
    items_today = []
    items_future = []
    items_rest = []

    current_moment = datetime.now(get_localzone())

    for item in items:
        try:
            item['projectName'] = project_names[item['projectId']]
        except KeyError:
            # Fallback
            item['projectName'] = 'Inbox'

        if item['remindTime']:
            item['remindTimeObject'] = load_datetime(item['remindTime'], '%Y-%m-%dT%H:%M:%S.000%z')

        if item['dueDate']:
            # 2018-02-23T14:30:00.000+0000
            item['dueDateObject'] = load_datetime(item['dueDate'], '%Y-%m-%dT%H:%M:%S.000%z')
            if item['dueDateObject'].astimezone(get_localzone()) < current_moment and item['dueDateObject'].astimezone(get_localzone()).date() != current_moment.date():
                items_due.append(item)
            elif item['dueDateObject'].astimezone(get_localzone()).date() == current_moment.date():
                items_today.append(item)
            else:
                items_future.append(item)
        else:
            items_rest.append(item)

    items_due = sorted(items_due, key=get_date_sortkey)
    items_today = sorted(items_today, key=get_date_sortkey)
    items_future = sorted(items_future, key=get_date_sortkey)
    items_rest = sorted(items_future, key=get_order_sortkey)
    return items_due, items_today, items_future, items_rest


def get_all_items():
    login_data = settings.login_data
    login_url = 'https://api.ticktick.com/api/v2/user/signon?wc=true&remember=true'
    tasks_url = 'https://api.ticktick.com/api/v2/batch/check/0?_={}'.format(str(datetime.now()).split('.')[0])
    projects_url = 'https://api.ticktick.com/api/v2/projects?_={}'.format(str(datetime.now()).split('.')[0])

    s = requests.session()
    try:
        s.post(login_url, json=login_data)
    except requests.exceptions.ConnectionError:
        print('{begin}ERROR:{end} Cannot connect to api.ticktick.com, connection error'.format(begin=bcolors.FAIL, end=bcolors.ENDC))
        return
    response = s.get(tasks_url)

    projects = s.get(projects_url)
    project_names = make_projects_list(projects.json())

    items_due, items_today, items_future, items_rest = create_lists(response.json()['syncTaskBean']['update'], project_names)
    print_section('today', items_today, color=bcolors.OKGREEN)
    print_section('overdue', items_due, color=bcolors.FAIL)
    #print_section('rest', items_rest)


get_all_items()
