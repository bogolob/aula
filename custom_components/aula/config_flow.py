import logging
from typing import Any, Optional

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.entity_registry import (
    async_entries_for_config_entry,
    async_get,
)

from .const import (
    CONF_EASYIQ_UGEPLAN_CALENDAR,
    CONF_PARSE_EASYIQ_UGEPLAN,
    CONF_SCHOOLSCHEDULE,
    CONF_UGEPLAN,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

AUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_SCHOOLSCHEDULE, default=False): cv.boolean,
        vol.Optional(CONF_UGEPLAN, default=False): cv.boolean,
        vol.Optional(CONF_PARSE_EASYIQ_UGEPLAN, default=False): cv.boolean,
        vol.Optional(CONF_EASYIQ_UGEPLAN_CALENDAR, default=False): cv.boolean,
    }
)


class AulaCustomConfigFlow(ConfigFlow, domain=DOMAIN):
    """Aula Custom config flow."""

    VERSION = 1
    MINOR_VERSION = 1

    _config_entry: Optional[ConfigEntry] = None
    data: Optional[dict[str, Any]]

    def _process_user_input(self, user_input: dict[str, Any]) -> ConfigFlowResult:
        self.data = user_input

        _LOGGER.debug(self.data.get(CONF_SCHOOLSCHEDULE))
        if self.data.get(CONF_SCHOOLSCHEDULE) is None:
            self.data[CONF_SCHOOLSCHEDULE] = False

        _LOGGER.debug(self.data.get(CONF_UGEPLAN))
        if self.data.get(CONF_UGEPLAN) is None:
            self.data[CONF_UGEPLAN] = False

        _LOGGER.debug(self.data.get(CONF_PARSE_EASYIQ_UGEPLAN))
        if self.data.get(CONF_PARSE_EASYIQ_UGEPLAN) is None:
            self.data[CONF_PARSE_EASYIQ_UGEPLAN] = False

        _LOGGER.debug(self.data.get(CONF_EASYIQ_UGEPLAN_CALENDAR))
        if self.data.get(CONF_EASYIQ_UGEPLAN_CALENDAR) is None:
            self.data[CONF_EASYIQ_UGEPLAN_CALENDAR] = False

        # This will log password in plain text: _LOGGER.debug(self.data)

        if self._config_entry:
            return self.async_update_reload_and_abort(
                self._config_entry,
                title="Aula",
                data=self.data,
                reason="reconfigure_successful",
            )

        return self.async_create_entry(title="Aula", data=self.data)

    async def async_step_user(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> ConfigFlowResult:
        """Invoked when a user initiates a flow via the user interface."""
        errors: dict[str, str] = {}

        if user_input is not None:
            return self._process_user_input(user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=AUTH_SCHEMA,
            errors=errors,
            last_step=True,
        )

    async def async_step_reconfigure(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> ConfigFlowResult:
        self._config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        assert self._config_entry

        if user_input:
            return self._process_user_input(user_input)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                AUTH_SCHEMA, self._config_entry.data
            ),
            last_step=True,
        )


# reconfiguration (options flow), to be implemented
#    @staticmethod
#    @callback
#    def async_get_options_flow(config_entry):
#        return OptionsFlowHandler(config_entry)


# class OptionsFlowHandler(OptionsFlow):
#     """Blueprint config flow options handler."""

#     def __init__(self, config_entry: ConfigEntry):
#         """Initialize HACS options flow."""
#         self.config_entry = config_entry
#         self.options = dict(config_entry.options)

#     async def async_step_init(
#         self, user_input: Optional[dict[str, Any]] = None
#     ) -> ConfigFlowResult:
#         """Manage the options."""
#         _LOGGER.debug("Options......")
#         _LOGGER.debug(self.config_entry)
#         entity_registry = async_get(self.hass)
#         entries = async_entries_for_config_entry(
#             entity_registry, self.config_entry.entry_id
#         )
#         repo_map = {e.entity_id: e for e in entries}
#         for entity_id in repo_map.keys():
#             # Unregister from HA
#             _LOGGER.debug(entity_id)
#             # entity_registry.async_remove(entity_id)
#         return await self.async_step_user()

#     async def async_step_user(
#         self, user_input: Optional[dict[str, Any]] = None
#     ) -> ConfigFlowResult:
#         """Handle a flow initialized by the user."""
#         if user_input is not None:
#             self.options.update(user_input)
#             return await self._update_options()

#         return self.async_show_form(
#             step_id="user",
#             data_schema=AUTH_SCHEMA,
#         )

#     async def _update_options(self) -> ConfigFlowResult:
#         """Update config entry options."""
#         return self.async_create_entry(title="Aula", data=self.options)
