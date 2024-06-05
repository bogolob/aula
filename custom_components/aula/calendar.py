import logging
from datetime import datetime, timedelta
from typing import Optional

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import Throttle, dt

from .client import AulaChildFirstName, AulaChildId, Client
from .const import (
    CONF_EASYIQ_UGEPLAN_CALENDAR,
    CONF_PARSE_EASYIQ_UGEPLAN,
    CONF_SCHOOLSCHEDULE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=10)
PARALLEL_UPDATES = 1

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    config = hass.data[DOMAIN][config_entry.entry_id]
    if config_entry.options:
        config.update(config_entry.options)

    if not config[CONF_SCHOOLSCHEDULE] and not (config[CONF_EASYIQ_UGEPLAN_CALENDAR] and config[CONF_PARSE_EASYIQ_UGEPLAN]):
        return

    client = hass.data[DOMAIN]["client"]
    calendar_devices = []

    for child in client._children:
        childid = child["id"]
        name = child["name"]
        calendar_devices.append(CalendarDevice(hass, name, childid))

    async_add_entities(calendar_devices)

class CalendarDevice(CalendarEntity):
    def __init__(self, hass: HomeAssistant, name: str, childid: AulaChildId):
        self._name = f"Skoleskema {name}"
        self._first_name = AulaChildFirstName(name.split()[0])
        self._childid = childid

        self.data = CalendarData(hass, self._childid, self._first_name)

    @property
    def event(self) -> Optional[CalendarEvent]:
        """Return the next upcoming event."""
        return self.data.event

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        unique_id = f"aulacalendar{str(self._childid)}"
        _LOGGER.debug(f"Unique ID for calendar {self._childid} {unique_id}")
        return unique_id

    def update(self) -> None:
        """Update all Calendars."""
        self.data.update()

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        """Get all events in a specific time frame."""
        return list(filter(lambda event: event.end > start_date and event.start < end_date, self.data.all_events))

class CalendarData:
    def __init__(self, hass: HomeAssistant, childid: AulaChildId, first_name: AulaChildFirstName):
        self.event: Optional[CalendarEvent] = None

        self._hass = hass
        self._childid = childid
        self._first_name = first_name

        self.all_events: list[CalendarEvent] = []
        self._client: Client = hass.data[DOMAIN]["client"]

    def _parse_skoleskema_json(self) -> list[CalendarEvent]:
        events: list[CalendarEvent] = []

        import json
        try:
            with open('skoleskema.json', 'r') as openfile:
                _data = json.load(openfile)
            data = json.loads(_data)
        except:
            _LOGGER.warn("Could not open and parse file skoleskema.json!")
            return events

        _LOGGER.debug("Parsing skoleskema.json...")
        for c in data['data']:
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
        return events

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
        if not "Events" in ugep_attr:
            return []

        return [
            calendar_event for easyiq_event in ugep_attr["Events"] if (calendar_event := CalendarData._easyiq_event_to_calendar_event(easyiq_event)) is not None
        ]

    def _parse_easyiq_calendar_events(self) -> list[CalendarEvent]:
        events: list[CalendarEvent] = []

        if self._client.ugep_attr and self._first_name in self._client.ugep_attr:
            events += self._parse_easyiq_ugep_attr(self._client.ugep_attr[self._first_name])

        if self._client.ugepnext_attr and self._first_name in self._client.ugepnext_attr:
            events += self._parse_easyiq_ugep_attr(self._client.ugepnext_attr[self._first_name])

        return events

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self) -> None:
        _LOGGER.debug("Updating calendars...")

        self.all_events = []
        self.all_events += self._parse_skoleskema_json()
        self.all_events += self._parse_easyiq_calendar_events()
