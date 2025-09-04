from collections import namedtuple
from enum import StrEnum

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
API_VERSION = "20"
MIN_UDDANNELSE_API = "https://api.minuddannelse.net/aula"
MEEBOOK_API = "https://app.meebook.com/aulaapi"
SYSTEMATIC_API = "https://systematic-momo.dk/api/aula"
EASYIQ_API = "https://api.easyiqcloud.dk/api/aula"
EASYIQ_NEW_API = "https://skoleportal.easyiqcloud.dk"
CONF_SCHOOLSCHEDULE = "schoolschedule"
CONF_UGEPLAN = "ugeplan"
CONF_MU_OPGAVER = "mu_opgaver"


class AulaWidgetId(StrEnum):
    EASYIQ_UGEPLAN = "0128"
