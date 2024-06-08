import logging
from datetime import datetime
from typing import Optional

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import AulaConfigEntry, AulaEntity
from .client import Client
from .clienttypes import AulaChildFirstName, AulaChildId
from .const import (
    CONF_EASYIQ_UGEPLAN_CALENDAR,
    CONF_PARSE_EASYIQ_UGEPLAN,
    CONF_SCHOOLSCHEDULE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: AulaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    if not config_entry.data[CONF_SCHOOLSCHEDULE] and not (
        config_entry.data[CONF_EASYIQ_UGEPLAN_CALENDAR]
        and config_entry.data[CONF_PARSE_EASYIQ_UGEPLAN]
    ):
        return

    client = config_entry.runtime_data.client
    calendar_devices: list[CalendarDevice] = []

    for child_id in client._childids:
        first_name = client._childfirstnames[child_id]
        calendar_devices.append(
            CalendarDevice(
                hass,
                client,
                config_entry.runtime_data.coordinator,
                first_name,
                child_id,
            )
        )

    async_add_entities(calendar_devices, True)


class CalendarDevice(AulaEntity, CalendarEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        client: Client,
        coordinator: DataUpdateCoordinator[None],
        first_name: AulaChildFirstName,
        child_id: AulaChildId,
    ):
        super().__init__(
            client, coordinator, f"Skoleskema {first_name}", f"aulacalendar{child_id}"
        )

        self._child_id = child_id

    @property
    def event(self) -> Optional[CalendarEvent]:
        """Return the next upcoming event."""

        if self._child_id not in self._client.child_calendar_data:
            _LOGGER.warning(f"Calendar data for {self._child_id} not loaded")
            return None

        return self._client.child_calendar_data[self._child_id].event

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Get all events in a specific time frame."""

        if self._child_id not in self._client.child_calendar_data:
            _LOGGER.warning(f"Calendar data for {self._child_id} not loaded")
            return []

        return list(
            filter(
                lambda event: event.end > start_date and event.start < end_date,
                self._client.child_calendar_data[self._child_id].all_events,
            )
        )
