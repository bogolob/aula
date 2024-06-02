from datetime import datetime, timedelta
import logging, time
from typing import List, Union
from .const import DOMAIN, CONF_SCHOOLSCHEDULE
from homeassistant import config_entries, core
from .client import AulaChildId, Child, Client
from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEvent,
)
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=10)
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    config = hass.data[DOMAIN][config_entry.entry_id]
    if config_entry.options:
        config.update(config_entry.options)

    if not config[CONF_SCHOOLSCHEDULE] == True:
        return True

    client: Client = hass.data[DOMAIN]["client"]

    calendar_devices = [CalendarDevice(hass, child) for child in client.children]
    async_add_entities(calendar_devices)


class CalendarDevice(CalendarEntity):
    def __init__(self, hass: core.HomeAssistant, child: Child):
        self._data = CalendarData(hass, child)
        self._name = f"Skoleskema {child.first_name}"

    @property
    def event(self):
        """Return the next upcoming event."""
        return self._data.event

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        unique_id = "aulacalendar" + str(self._child.id)
        _LOGGER.debug("Unique ID for calendar " + self._child.id + " " + unique_id)
        return unique_id

    def update(self) -> None:
        """Update all Calendars."""
        self._data.update()

    async def async_get_events(
        self, hass: core.HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Get all events in a specific time frame."""
        return await self._data.async_get_events(hass, start_date, end_date)


class CalendarData:
    def __init__(self, hass: core.HomeAssistant, child: Child):
        self.event = None

        self._hass = hass
        self._child = child

        self._client: Client = hass.data[DOMAIN]["client"]

    def parse_calendar_data(self) -> Union[None, list[CalendarEvent]]:
        import json

        events: list[CalendarEvent] = []

        try:
            with open("skoleskema.json", "r") as openfile:
                _data = json.load(openfile)
            data = json.loads(_data)
        except:
            _LOGGER.warn("Could not open and parse file skoleskema.json!")
            return None

        _LOGGER.debug("Parsing skoleskema.json...")
        for c in data["data"]:
            if c["type"] == "lesson" and c["belongsToProfiles"][0] == self._childid:
                summary = c["title"]
                start = datetime.strptime(c["startDateTime"], "%Y-%m-%dT%H:%M:%S%z")
                end = datetime.strptime(c["endDateTime"], "%Y-%m-%dT%H:%M:%S%z")
                vikar = 0
                for p in c["lesson"]["participants"]:
                    if p["participantRole"] == "substituteTeacher":
                        teacher = "VIKAR: " + p["teacherName"]
                        vikar = 1
                        break
                if vikar == 0:
                    try:
                        teacher = c["lesson"]["participants"][0]["teacherInitials"]
                    except:
                        try:
                            _LOGGER.debug("Lesson json dump" + str(c["lesson"]))
                            teacher = c["lesson"]["participants"][0]["teacherName"]
                        except:
                            _LOGGER.debug(
                                "Could not find any teacher information for "
                                + summary
                                + " at "
                                + str(start)
                            )
                            teacher = ""
                event = CalendarEvent(
                    summary=summary + ", " + teacher,
                    start=start,
                    end=end,
                )
                events.append(event)

        return events

    def parse_easyiq_ugeplan_events(self) -> Union[None, list[CalendarEvent]]:
        if not "0001" in self._client.widgets:
            return None

        _LOGGER.debug("Parsing EasyIQ Ugeplan data")

    async def async_get_events(
        self, hass: core.HomeAssistant, start_date: datetime, end_date: datetime
    ):
        return self._events

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        new_events: list[CalendarEvent] = []

        _LOGGER.debug("Updating calendars...")
        skoleskema_events = self.parse_calendar_data()
        new_events.append(skoleskema_events)

        if skoleskema_events is None:
            new_events.append(self.parse_easyiq_ugeplan_events())

        self._events = new_events
        self.event = self._events[0] if len(self._events) > 0 else None
