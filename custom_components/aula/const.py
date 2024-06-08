from datetime import timedelta

STARTUP = r"""
                _
     /\        | |
    /  \  _   _| | __ _
   / /\ \| | | | |/ _` |
  / ____ \ |_| | | (_| |
 /_/    \_\__,_|_|\__,_|
Aula integration, version: %s
This is a custom integration
If you have any issues with this you need to open an issue here:
https://github.com/scaarup/aula/issues
-------------------------------------------------------------------
"""

DOMAIN = "aula"
API = "https://www.aula.dk/api/v"
API_VERSION = "19"
MIN_UDDANNELSE_API = "https://api.minuddannelse.net/aula"
MEEBOOK_API = "https://app.meebook.com/aulaapi"
SYSTEMATIC_API = "https://systematic-momo.dk/api/aula"
EASYIQ_API = "https://api.easyiqcloud.dk/api/aula"
CONF_SCHOOLSCHEDULE = "schoolschedule"
CONF_UGEPLAN = "ugeplan"
CONF_PARSE_EASYIQ_UGEPLAN = "parse_easyiq_ugeplan"
CONF_EASYIQ_UGEPLAN_CALENDAR = "easyid_ugeplan_calendar"
EASYIQ_UGEPLAN_WEEKPLAN = "WeekPlan"
EASYIQ_UGEPLAN_EVENTS = "Events"
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)
TIME_BETWEEN_UGEPLAN_UPDATES = timedelta(hours=1)
TIME_BETWEEN_CALENDAR_UPDATES = timedelta(hours=1)
