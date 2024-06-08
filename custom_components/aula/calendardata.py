import logging
from datetime import datetime
from typing import Any, Optional

from homeassistant.components.calendar import CalendarEvent
from homeassistant.util import dt

from .clienttypes import AulaChildFirstName, AulaChildId

_LOGGER = logging.getLogger(__name__)

class AulaCalendarData:
    def __init__(self, childid: AulaChildId, first_name: AulaChildFirstName):
        self.event: Optional[CalendarEvent] = None

        self._childid = childid
        self._first_name = first_name

        self.all_events: list[CalendarEvent] = []

    def load_skoleskema_json(self, skoleskema_json_data: Any) -> None:
        events: list[CalendarEvent] = []

        _LOGGER.debug("Parsing skoleskema.json...")
        for c in skoleskema_json_data['data']:
            if c['type'] == "lesson" and c['belongsToProfiles'][0] == self._childid:
                summary = c['title']
                start = datetime.strptime(c['startDateTime'],"%Y-%m-%dT%H:%M:%S%z").replace(tzinfo=dt.now().tzinfo)
                end = datetime.strptime(c['endDateTime'],"%Y-%m-%dT%H:%M:%S%z").replace(tzinfo=dt.now().tzinfo)
                vikar = 0
                for p in c['lesson']['participants']:
                    if p['participantRole'] == 'substituteTeacher':
                        teacher = "VIKAR: "+p['teacherName']
                        vikar = 1
                        break
                if vikar == 0:
                    try:
                        teacher = c['lesson']['participants'][0]['teacherInitials']
                    except:
                        try:
                            _LOGGER.debug("Lesson json dump"+str(c['lesson']))
                            teacher = c['lesson']['participants'][0]['teacherName']
                        except:
                            _LOGGER.debug("Could not find any teacher information for "+summary+" at "+str(start))
                            teacher = ""
                event = CalendarEvent(
                    summary=summary+", "+teacher,
                    start = start,
                    end = end,
                )
                events.append(event)

        self.all_events += events

    @staticmethod
    def _easyiq_event_to_calendar_event(easyiq_event: dict) -> Optional[CalendarEvent]:
        start: datetime
        end: datetime

        try:
            start = datetime.strptime(easyiq_event["start"], "%Y/%m/%d %H:%M").replace(tzinfo=dt.now().tzinfo)
        except ValueError:
            return None

        try:
            end = datetime.strptime(easyiq_event["end"], "%Y/%m/%d %H:%M").replace(tzinfo=dt.now().tzinfo)
        except ValueError:
            return None

        return CalendarEvent(
                start = start,
                end = end,
                description = easyiq_event["description"],
                summary = f"{easyiq_event["courses"]} - {easyiq_event["activities"]}"
            )

    def _parse_easyiq_ugep_attr(self, ugep_attr: dict) -> list[CalendarEvent]:
        if "Events" not in ugep_attr:
            return []

        return [
            calendar_event for easyiq_event in ugep_attr["Events"] if (calendar_event := AulaCalendarData._easyiq_event_to_calendar_event(easyiq_event)) is not None
        ]

    def load_easyiq_calendar_events(self, ugep_attr: Any, ugepnext_attr: Any) -> None:
        events: list[CalendarEvent] = []

        if ugep_attr and self._first_name in ugep_attr:
            _LOGGER.debug("Loading EasyIQ calendar events from ugep_attr")
            events += self._parse_easyiq_ugep_attr(ugep_attr[self._first_name])

        if ugepnext_attr and self._first_name in ugepnext_attr:
            _LOGGER.debug("Loading EasyIQ calendar events from ugepnext_attr")
            events += self._parse_easyiq_ugep_attr(ugepnext_attr[self._first_name])

        self.all_events += events
