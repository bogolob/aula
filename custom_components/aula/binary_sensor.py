from datetime import timedelta
from typing import Any
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

# from homeassistant.util import Throttle
import logging

from .client import Client, Message
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=300.0)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    async_add_entities([AulaBinarySensor(hass)], update_before_add=True)


class AulaBinarySensor(BinarySensorEntity, RestoreEntity):
    _subject: str
    _text: str
    _sender: str
    _unread: int
    _client: Client
    _state: bool

    def __init__(self, hass: HomeAssistant):
        self._client = self._hass.data[DOMAIN]["client"]

    @property
    def extra_stat_attributes(self) -> dict[str, Any]:
        attributes = {}
        attributes["subject"] = self._subject
        attributes["text"] = self._text
        attributes["sender"] = self._sender
        attributes["friendly_name"] = "Aula message"
        return attributes

    @property
    def unique_id(self) -> str:
        return "aulamessage"

    @property
    def icon(self) -> str:
        return "mdi:email"

    @property
    def friendly_name(self) -> str:
        return "Aula message"

    @property
    def is_on(self) -> bool:
        return self._state

    def update(self):
        if self._client.unread_message_count >= 1:
            _LOGGER.debug("There are unread message(s)")

            unread_thread = self._client.unread_message_thread
            unread_message = unread_thread.messages[0]

            # _LOGGER.debug("Latest message: "+str(self._client.message))
            self._subject = unread_thread.subject
            self._text = unread_message.text
            self._sender = unread_message.sender
            self._state = True
        else:
            _LOGGER.debug("There are NO unread messages")
            self._state = False
            self._subject = ""
            self._text = ""
            self._sender = ""
