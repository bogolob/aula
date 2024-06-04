# from homeassistant.util import Throttle
import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=300.0)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client = hass.data[DOMAIN]["client"]
    if client.unread_messages == 1:
        try:
            subject = client.message["subject"]
        except:
            subject = ""
        try:
            text = client.message["text"]
        except:
            text = ""
        try:
            sender = client.message["sender"]
        except:
            sender = ""
    else:
        subject = ""
        text = ""
        sender = ""

    sensors = []
    device = AulaBinarySensor(
        hass=hass,
        unread=client.unread_messages,
        subject=subject,
        text=text,
        sender=sender,
    )
    sensors.append(device)
    async_add_entities(sensors, True)


class AulaBinarySensor(BinarySensorEntity, RestoreEntity):
    def __init__(
        self, hass: HomeAssistant, unread: bool, subject: str, text: str, sender: str
    ):
        self._hass = hass
        self._unread = unread
        self._subject = subject
        self._text = text
        self._sender = sender
        self._state = False
        self._client = self._hass.data[DOMAIN]["client"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attributes = {}
        attributes["subject"] = self._subject
        attributes["text"] = self._text
        attributes["sender"] = self._sender
        attributes["friendly_name"] = "Aula message"
        return attributes

    @property
    def unique_id(self) -> str:
        unique_id = "aulamessage"
        return unique_id

    @property
    def icon(self) -> str:
        return "mdi:email"

    @property
    def friendly_name(self) -> str:
        return "Aula message"

    @property
    def is_on(self) -> bool:
        return self._state

    def update(self) -> None:
        if self._client.unread_messages == 1:
            _LOGGER.debug("There are unread message(s)")
            # _LOGGER.debug("Latest message: "+str(self._client.message))
            self._subject = self._client.message["subject"]
            self._text = self._client.message["text"]
            self._sender = self._client.message["sender"]
            self._state = True
        else:
            _LOGGER.debug("There are NO unread messages")
            self._state = False
            self._subject = ""
            self._text = ""
            self._sender = ""
