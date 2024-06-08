import logging
from datetime import datetime
from typing import Optional, override

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt

from . import AulaConfigEntry, AulaEntity
from .client import AulaChildFirstName, AulaChildId, Client
from .const import (
    CONF_EASYIQ_UGEPLAN_CALENDAR,
    CONF_PARSE_EASYIQ_UGEPLAN,
    CONF_SCHOOLSCHEDULE,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: AulaConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    if not config_entry.data[CONF_SCHOOLSCHEDULE] and not (config_entry.data[CONF_EASYIQ_UGEPLAN_CALENDAR] and config_entry.data[CONF_PARSE_EASYIQ_UGEPLAN]):
        return

    client = config_entry.runtime_data.client
    calendar_devices: list[CalendarDevice] = []

    for child in client._children:
        childid = child["id"]
        first_name = AulaChildFirstName(child["name"].split()[0])
        calendar_devices.append(CalendarDevice(hass, client, config_entry.runtime_data.coordinator, first_name, childid))

    async_add_entities(calendar_devices, True)

class CalendarDevice(AulaEntity, CalendarEntity):
    def __init__(self, hass: HomeAssistant, client: Client, coordinator: DataUpdateCoordinator[None], first_name: AulaChildFirstName, childid: AulaChildId):
        super().__init__(client, coordinator, f"Skoleskema {first_name}", f"aulacalendar{childid}")
        self.data = CalendarData(hass, client, childid, first_name)

    @property
    def event(self) -> Optional[CalendarEvent]:
        """Return the next upcoming event."""
        return self.data.event

    @override
    def _handle_coordinator_update(self) -> None:
        super()._handle_coordinator_update()

        self.data.parse_skoleskema_json()
        self.data.parse_easyiq_calendar_events()

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        """Get all events in a specific time frame."""
        return list(filter(lambda event: event.end > start_date and event.start < end_date, self.data.all_events))

class CalendarData:
    def __init__(self, hass: HomeAssistant, client: Client, childid: AulaChildId, first_name: AulaChildFirstName):
        self.event: Optional[CalendarEvent] = None

        self._hass = hass
        self._client = client
        self._childid = childid
        self._first_name = first_name

        self.all_events: list[CalendarEvent] = []

    def parse_skoleskema_json(self) -> list[CalendarEvent]:
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
        if "Events" not in ugep_attr:
            return []

        return [
            calendar_event for easyiq_event in ugep_attr["Events"] if (calendar_event := CalendarData._easyiq_event_to_calendar_event(easyiq_event)) is not None
        ]

    def parse_easyiq_calendar_events(self) -> list[CalendarEvent]:
        events: list[CalendarEvent] = []

        if self._client.ugep_attr and self._first_name in self._client.ugep_attr:
            events += self._parse_easyiq_ugep_attr(self._client.ugep_attr[self._first_name])

        if self._client.ugepnext_attr and self._first_name in self._client.ugepnext_attr:
            events += self._parse_easyiq_ugep_attr(self._client.ugepnext_attr[self._first_name])

        return events
