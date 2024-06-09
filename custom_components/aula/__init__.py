"""
Based on https://github.com/JBoye/HA-Aula
"""

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.loader import async_get_integration

from .client import Client
from .const import (
    CONF_EASYIQ_UGEPLAN_CALENDAR,
    CONF_PARSE_EASYIQ_UGEPLAN,
    CONF_SCHOOLSCHEDULE,
    CONF_UGEPLAN,
    DOMAIN,
    MIN_TIME_BETWEEN_UPDATES,
    STARTUP,
)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.CALENDAR,
]

_LOGGER = logging.getLogger(__name__)


@dataclass
class AulaData:
    client: Client
    coordinator: DataUpdateCoordinator[None]


class AulaEntity(CoordinatorEntity[DataUpdateCoordinator[None]]):

    def __init__(
        self,
        client: Client,
        coordinator: DataUpdateCoordinator[None],
        name: str,
        unique_id: str,
    ):
        super().__init__(coordinator)
        self._client = client
        self._attr_name = name
        self._attr_unique_id = unique_id


type AulaConfigEntry = ConfigEntry[AulaData]


async def async_setup_entry(hass: HomeAssistant, entry: AulaConfigEntry) -> bool:
    """Set up platform from a ConfigEntry."""

    username: str = entry.data[CONF_USERNAME]
    password: str = entry.data[CONF_PASSWORD]
    schoolschedule: bool = entry.data[CONF_SCHOOLSCHEDULE]
    ugeplan: bool = entry.data[CONF_UGEPLAN]
    parse_easyiq_ugeplan: bool = entry.data[CONF_PARSE_EASYIQ_UGEPLAN]
    easyiq_ugeplan_calendar: bool = entry.data[CONF_EASYIQ_UGEPLAN_CALENDAR]

    integration = await async_get_integration(hass, DOMAIN)
    _LOGGER.info(STARTUP, integration.version)

    client = Client(
        username,
        password,
        schoolschedule,
        ugeplan,
        parse_easyiq_ugeplan,
        easyiq_ugeplan_calendar,
    )

    async def async_update_data() -> None:
        await hass.async_add_executor_job(client.update_data)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"aula_{username}",
        update_method=async_update_data,
        update_interval=MIN_TIME_BETWEEN_UPDATES,
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = AulaData(client, coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    return unload_ok
