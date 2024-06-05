import logging
from datetime import datetime, timedelta
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.json import (
    JSON_DECODE_EXCEPTIONS,
    JsonObjectType,
    json_loads_object,
)

from .client import AulaChildFirstName, AulaChildId, Client
from .const import CONF_RAWUGEPLAN, CONF_SCHOOLSCHEDULE, CONF_UGEPLAN, DOMAIN

_LOGGER = logging.getLogger(__name__)

API_CALL_SERVICE_NAME = "api_call"
API_CALL_SCHEMA = vol.Schema(
    {
        vol.Required("uri"): cv.string,
        vol.Optional("post_data"): cv.string,
    }
)


PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]

    if config_entry.options:
        config.update(config_entry.options)

    client = Client(
        config[CONF_USERNAME],
        config[CONF_PASSWORD],
        config[CONF_SCHOOLSCHEDULE],
        config[CONF_UGEPLAN],
        config[CONF_RAWUGEPLAN],
    )
    hass.data[DOMAIN]["client"] = client

    async def async_update_data() -> None:
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

    if config[CONF_UGEPLAN]:
        ugeplan = True
    else:
        ugeplan = False

    if config[CONF_RAWUGEPLAN]:
        rawugeplan = True
    else:
        rawugeplan = False

    for i, child in enumerate(client._children):
        # _LOGGER.debug("Presence data for child "+str(child["id"])+" : "+str(client.presence[str(child["id"])]))
        if client.presence[AulaChildId(str(child["id"]))] == 1:
            if AulaChildId(str(child["id"])) in client._daily_overview:
                _LOGGER.debug(
                    "Found presence data for childid "
                    + str(child["id"])
                    + " adding sensor entity."
                )
                entities.append(
                    AulaSensor(hass, coordinator, child, ugeplan, rawugeplan)
                )
        else:
            entities.append(AulaSensor(hass, coordinator, child, ugeplan, rawugeplan))
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

    async_add_entities(entities, update_before_add=True)

    def custom_api_call_service(call: ServiceCall) -> ServiceResponse:
        if "post_data" in call.data and len(call.data["post_data"]) > 0:
            data = client.custom_api_call(call.data["uri"], call.data["post_data"])
        else:
            data = client.custom_api_call(call.data["uri"], None)

        ret: JsonObjectType

        if "error" in data:
            ret = {"error": data["error"]}
        elif "response" in data:
            try:
                ret = json_loads_object(data["response"])
            except JSON_DECODE_EXCEPTIONS:
                ret = {"response": data["response"]}
        else:
            return None

        return ret

    hass.services.async_register(
        DOMAIN,
        API_CALL_SERVICE_NAME,
        custom_api_call_service,
        schema=API_CALL_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


class AulaSensor(Entity):
    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        child: dict,
        ugeplan: bool,
        rawugeplan: bool,
    ) -> None:
        self._hass = hass
        self._coordinator = coordinator
        self._child = child
        self._ugeplan = ugeplan
        self._rawugeplan = rawugeplan
        self._client: Client = hass.data[DOMAIN]["client"]

    @property
    def name(self) -> str:
        childname = self._client._childfirstnames[AulaChildId(str(self._child["id"]))]
        institution = self._client._institutions[AulaChildId(str(self._child["id"]))]
        return f"{institution} {childname}"

    @property
    def state(self) -> str:
        """
        0 = IKKE KOMMET
        1 = SYG
        2 = FERIE/FRI
        3 = KOMMET/TIL STEDE
        4 = PÅ TUR
        5 = SOVER
        8 = HENTET/GÅET
        """
        if self._client.presence[AulaChildId(str(self._child["id"]))] == 1:
            states: list[str] = [
                "Ikke kommet",
                "Syg",
                "Ferie/Fri",
                "Kommet/Til stede",
                "På tur",
                "Sover",
                "6",
                "7",
                "Gået",
                "9",
                "10",
                "11",
                "12",
                "13",
                "14",
                "15",
            ]
            daily_info = self._client._daily_overview[
                AulaChildId(str(self._child["id"]))
            ]
            return states[int(daily_info["status"])]
        else:
            _LOGGER.debug("Setting state to n/a for child " + str(self._child["id"]))
            return "n/a"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._client.presence[AulaChildId(str(self._child["id"]))] == 1:
            daily_info = self._client._daily_overview[
                AulaChildId(str(self._child["id"]))
            ]
            try:
                profilePicture = daily_info["institutionProfile"]["profilePicture"][
                    "url"
                ]
            except:
                profilePicture = None

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
        attributes: dict[str, Any] = {}
        # _LOGGER.debug("Dump of ugep_attr: "+str(self._client.ugep_attr))
        # _LOGGER.debug("Dump of ugepnext_attr: "+str(self._client.ugepnext_attr))
        if self._ugeplan:
            if "0062" in self._client.widgets:
                try:
                    attributes["huskelisten"] = self._client.huskeliste[
                        AulaChildFirstName(self._child["first_name"])
                    ]
                except:
                    attributes["huskelisten"] = "Not available"

            try:
                child_ugeplan = self._client.ugep_attr[
                    AulaChildFirstName(self._child["first_name"])
                ]
            except:
                child_ugeplan = None

            try:
                child_ugeplan_next = self._client.ugepnext_attr[
                    AulaChildFirstName(self._child["first_name"])
                ]
            except:
                child_ugeplan_next = None
                _LOGGER.debug(
                    "Could not get ugeplan for next week for child "
                    + str(self._child["first_name"])
                    + ". Perhaps not available yet."
                )

            if self._rawugeplan and "0001" in self._client.widgets:

                def parse_easyiq_ugeplan(
                    ugeplan_json: dict[str, Any], varname: str
                ) -> None:
                    attribute_prefix = f"easyiq_{varname}"

                    try:
                        attributes[f"{attribute_prefix}_fromDate"] = (
                            datetime.fromisoformat(ugeplan_json["fromDate"])
                        )
                        attributes[f"{attribute_prefix}_toDate"] = (
                            datetime.fromisoformat(ugeplan_json["toDate"])
                        )
                        attributes[f"{attribute_prefix}_weekplan"] = (
                            {
                                "activity_name": ugeplan_json["WeekPlan"][
                                    "ActivityName"
                                ],
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
            else:
                attributes["ugeplan"] = (
                    child_ugeplan if child_ugeplan else "Not available"
                )
                attributes["ugeplan_next"] = (
                    child_ugeplan_next if child_ugeplan_next else "Not available"
                )

        if self._client.presence[AulaChildId(str(self._child["id"]))] == 1:
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
            attributes["profilePicture"] = profilePicture
            attributes["institutionProfileId"] = daily_info["institutionProfile"]["id"]
        return attributes

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
