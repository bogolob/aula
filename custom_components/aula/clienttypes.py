from enum import IntEnum
from typing import NewType

AulaChildId = NewType("AulaChildId", str)
AulaChildUserId = NewType("AulaChildUserId", str)
AulaChildFirstName = NewType("AulaChildFirstName", str)
AulaInstitutionId = NewType("AulaInstitutionId", str)


class AulaChildPresenceType(IntEnum):
    IKKE_KOMMET = 0
    SYG = 1
    FERIE_FRI = 2
    KOMMET = 3
    PAA_TUR = 4
    SOVER = 5
    HENTET_GAAET = 8
    UNKNOWN = -1
