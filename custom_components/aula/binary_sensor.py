# from homeassistant.util import Throttle
import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import AulaConfigEntry, AulaEntity
from .client import Client

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=300.0)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: AulaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    aula_data = config_entry.runtime_data

    sensors = []
    device = AulaBinarySensor(hass, aula_data.client, aula_data.coordinator)
    sensors.append(device)
    async_add_entities(sensors, True)


class AulaBinarySensor(BinarySensorEntity, RestoreEntity, AulaEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        client: Client,
        coordinator: DataUpdateCoordinator[None],
    ):
        super().__init__(client, coordinator, "Aula message", "aulamessage")
        self._attr_icon = "mdi:email"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attributes: dict[str, Any] = {}

        if self._client.unread_messages == 1:
            _LOGGER.debug("There are unread message(s)")
            # _LOGGER.debug("Latest message: "+str(self._client.message))
            attributes["subject"] = self._client.message["subject"]
            attributes["text"] = self._client.message["text"]
            attributes["sender"] = self._client.message["sender"]
            self._state = True
        else:
            _LOGGER.debug("There are NO unread messages")
            attributes["subject"] = ""
            attributes["text"] = ""
            attributes["sender"] = ""

        return attributes

    @property
    def is_on(self) -> bool:
        return self._client.unread_messages == 1
