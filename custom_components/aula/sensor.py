from typing import Optional
from .const import DOMAIN
import logging
import json
from datetime import datetime, timedelta
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant import config_entries, core
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .client import Client, Child, PresenceType

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from .const import (
    CONF_SCHOOLSCHEDULE,
    CONF_UGEPLAN,
    CONF_RAWUGEPLAN,
    DOMAIN,
)

API_CALL_SERVICE_NAME = "api_call"
API_CALL_SCHEMA = vol.Schema(
    {
        vol.Required("uri"): cv.string,
        vol.Optional("post_data"): cv.string,
    }
)

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]

    if config_entry.options:
        config.update(config_entry.options)
    # from .client import Client
    client = Client(
        config[CONF_USERNAME],
        config[CONF_PASSWORD],
        config[CONF_SCHOOLSCHEDULE],
        config[CONF_UGEPLAN],
        config[CONF_RAWUGEPLAN],
    )
    hass.data[DOMAIN]["client"] = client

    async def async_update_data():
        client = hass.data[DOMAIN]["client"]
        await hass.async_add_executor_job(client.update_data)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="sensor",
        update_method=async_update_data,
        update_interval=timedelta(minutes=5),
    )

    # Immediate refresh
    await coordinator.async_request_refresh()

    entities = []

    await hass.async_add_executor_job(client.update_data)

    for child in client.children:
        # _LOGGER.debug("Presence data for child "+str(child["id"])+" : "+str(client.presence[str(child["id"])]))
        if not client.presence[child.id] is None:
            _LOGGER.debug(
                f"Found presence data for childid {child.id}, adding sensor entity."
            )
            entities.append(AulaSensor(hass, coordinator, child))
        else:
            entities.append(AulaSensor(hass, coordinator, child))
    # We have data and can now set up the calendar platform:
    if config[CONF_SCHOOLSCHEDULE]:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, "calendar")
        )
    ####
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "binary_sensor")
    )
    ####

    global ugeplan
    global rawugeplan
    if config[CONF_UGEPLAN]:
        ugeplan = True
    else:
        ugeplan = False

    if config[CONF_RAWUGEPLAN]:
        rawugeplan = True
    else:
        rawugeplan = False

    async_add_entities(entities, update_before_add=True)

    def custom_api_call_service(call: ServiceCall) -> ServiceResponse:
        if "post_data" in call.data and len(call.data["post_data"]) > 0:
            data = client.custom_api_call(call.data["uri"], call.data["post_data"])
        else:
            data = client.custom_api_call(call.data["uri"])
        return data

    hass.services.async_register(
        DOMAIN,
        API_CALL_SERVICE_NAME,
        custom_api_call_service,
        schema=API_CALL_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


class AulaSensor(Entity):
    _client: Client
    _child: Child

    def __init__(
        self, hass: HomeAssistant, coordinator: DataUpdateCoordinator, child: Child
    ) -> None:
        self._hass = hass
        self._coordinator = coordinator
        self._child = child
        self._client: Client = hass.data[DOMAIN]["client"]

    @property
    def name(self) -> str:
        return f"{self._child.institution_name} {self._child.first_name}"

    @property
    def state(self) -> str:
        if not (daily_info := self._client.presence[self._child.id]) is None:
            return PresenceType(int(daily_info["status"])).to_string()
        else:
            _LOGGER.debug(f"Setting state to n/a for child {self._child.id}")
            return "n/a"

    @property
    def extra_state_attributes(self) -> dict:
        attributes = {}

        if not (daily_info := self._client.presence[self._child.id]) is None:
            attributes["institutionProfileId"] = daily_info["institutionProfile"]["id"]

            try:
                profilePicture = daily_info["institutionProfile"]["profilePicture"][
                    "url"
                ]
            except:
                profilePicture = None

            attributes["profilePicture"] = profilePicture

            fields = [
                "location",
                "sleepIntervals",
                "checkInTime",
                "checkOutTime",
                "activityType",
                "entryTime",
                "exitTime",
                "exitWith",
                "comment",
                "spareTimeActivity",
                "selfDeciderStartTime",
                "selfDeciderEndTime",
            ]

            for attribute in fields:
                if attribute == "exitTime" and daily_info[attribute] == "23:59:00":
                    attributes[attribute] = None
                else:
                    try:
                        attributes[attribute] = datetime.strptime(
                            daily_info[attribute], "%H:%M:%S"
                        ).strftime("%H:%M")
                    except:
                        attributes[attribute] = daily_info[attribute]

        # _LOGGER.debug("Dump of ugep_attr: "+str(self._client.ugep_attr))
        # _LOGGER.debug("Dump of ugepnext_attr: "+str(self._client.ugepnext_attr))
        if ugeplan:
            if "0062" in self._client.widgets:
                self.populate_ugeplan_attributes_0062(attributes)

            try:
                child_ugeplan = self._client.ugep_attr[self._child.first_name]
            except:
                child_ugeplan = None

            try:
                child_ugeplan_next = self._client.ugepnext_attr[self._child.first_name]
            except:
                child_ugeplan_next = None
                _LOGGER.debug(
                    "Could not get ugeplan for next week for child "
                    + str(self._child.first_name)
                    + ". Perhaps not available yet."
                )

            if rawugeplan and "0001" in self._client.widgets:
                self.populate_rawugeplan_attributes_0001(attributes)
            else:
                attributes["ugeplan"] = (
                    child_ugeplan if child_ugeplan else "Not available"
                )
                attributes["ugeplan_next"] = (
                    child_ugeplan_next if child_ugeplan_next else "Not available"
                )

        return attributes

    def populate_ugeplan_attributes_0062(self, attributes: dict):
        try:
            attributes["huskelisten"] = self._client.huskeliste[
                self._child["first_name"]
            ]
        except:
            attributes["huskelisten"] = "Not available"

    def populate_rawugeplan_attributes_0001(
        self,
        attributes: dict,
        child_ugeplan: Optional[dict],
        child_ugeplan_next: Optional[dict],
    ):
        def parse_easyiq_ugeplan(ugeplan_json: dict, varname: str):
            attribute_prefix = f"easyiq_{varname}"

            try:
                attributes[f"{attribute_prefix}_fromDate"] = datetime.fromisoformat(
                    ugeplan_json["fromDate"]
                )
                attributes[f"{attribute_prefix}_toDate"] = datetime.fromisoformat(
                    ugeplan_json["toDate"]
                )
                attributes[f"{attribute_prefix}_weekplan"] = (
                    {
                        "activity_name": ugeplan_json["WeekPlan"]["ActivityName"],
                        "year": ugeplan_json["WeekPlan"]["Year"],
                        "week_number": ugeplan_json["WeekPlan"]["WeekNo"],
                        "text": ugeplan_json["WeekPlan"]["Text"],
                    }
                    if ("WeekPlan" in ugeplan_json)
                    else "Not available"
                )
                attributes[f"{attribute_prefix}_events"] = (
                    sorted(
                        [
                            {
                                "start": datetime.strptime(
                                    event["start"], "%Y/%m/%d %H:%M"
                                ),
                                "end": datetime.strptime(
                                    event["end"], "%Y/%m/%d %H:%M"
                                ),
                                "weekday": datetime.strptime(
                                    event["start"], "%Y/%m/%d %H:%M"
                                ).weekday(),
                                "description": event["description"],
                                "courses": event["courses"],
                                "activities": event["activities"],
                            }
                            for event in ugeplan_json["Events"]
                        ],
                        key=lambda x: x["start"],
                    )
                    if ("Events" in ugeplan_json)
                    else "Not available"
                )

            except Exception as e:
                _LOGGER.error(f"Error parsing EasyIQ JSON: {e}")

                attributes[f"{attribute_prefix}_fromDate"] = datetime.min
                attributes[f"{attribute_prefix}_toDate"] = datetime.min
                attributes[f"{attribute_prefix}_weekplan"] = "Not available"
                attributes[f"{attribute_prefix}_events"] = "Not available"

        if child_ugeplan:
            parse_easyiq_ugeplan(child_ugeplan, "ugeplan")

        if child_ugeplan_next:
            parse_easyiq_ugeplan(child_ugeplan_next, "ugeplan_next")

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._coordinator.last_update_success

    @property
    def unique_id(self) -> str:
        unique_id = "aula" + str(self._child["id"])
        _LOGGER.debug("Unique ID for child " + str(self._child["id"]) + " " + unique_id)
        return unique_id

    @property
    def icon(self) -> str:
        return "mdi:account-school"

    async def async_update(self) -> None:
        """Update the entity. Only used by the generic entity update service."""
        await self._coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )
