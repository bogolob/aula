import logging
from datetime import datetime
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.json import (
    JSON_DECODE_EXCEPTIONS,
    JsonObjectType,
    json_loads_object,
)

from . import AulaConfigEntry, AulaEntity
from .client import Client
from .clienttypes import AulaChildFirstName, AulaChildId, AulaChildPresenceType
from .const import CONF_PARSE_EASYIQ_UGEPLAN, CONF_UGEPLAN, DOMAIN

_LOGGER = logging.getLogger(__name__)

API_CALL_SERVICE_NAME = "api_call"
API_CALL_SCHEMA = vol.Schema(
    {
        vol.Required("uri"): cv.string,
        vol.Optional("post_data"): cv.string,
    }
)

STATE_NOT_AVAILABLE = "n_a"

AULACHILDPRESENCETYPE_TO_STATE_MAPPING = {
    AulaChildPresenceType.IKKE_KOMMET: "ikke_kommet",
    AulaChildPresenceType.SYG: "syg",
    AulaChildPresenceType.FERIE_FRI: "ferie_fri",
    AulaChildPresenceType.KOMMET: "kommet",
    AulaChildPresenceType.PAA_TUR: "paa_tur",
    AulaChildPresenceType.SOVER: "sover",
    AulaChildPresenceType.HENTET_GAAET: "hentet_gaaet",
    AulaChildPresenceType.UNKNOWN: STATE_NOT_AVAILABLE,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: AulaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup sensors from a config entry created in the integrations UI."""

    client = config_entry.runtime_data.client

    entities = []

    if CONF_UGEPLAN in config_entry.data and config_entry.data[CONF_UGEPLAN]:
        ugeplan = True
    else:
        ugeplan = False

    if (
        CONF_PARSE_EASYIQ_UGEPLAN in config_entry.data
        and config_entry.data[CONF_PARSE_EASYIQ_UGEPLAN]
    ):
        parse_easyiq_ugeplan = True
    else:
        parse_easyiq_ugeplan = False

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
                    AulaSensor(
                        hass,
                        client,
                        config_entry.runtime_data.coordinator,
                        child,
                        ugeplan,
                        parse_easyiq_ugeplan,
                    )
                )
        else:
            entities.append(
                AulaSensor(
                    hass,
                    client,
                    config_entry.runtime_data.coordinator,
                    child,
                    ugeplan,
                    parse_easyiq_ugeplan,
                )
            )

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


class AulaSensor(AulaEntity, SensorEntity):

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(AULACHILDPRESENCETYPE_TO_STATE_MAPPING.values())
    _attr_translation_key = "aulapresence"

    def __init__(
        self,
        hass: HomeAssistant,
        api: Client,
        coordinator: DataUpdateCoordinator[None],
        child: dict,
        ugeplan: bool,
        parse_easyiq_ugeplan: bool,
    ) -> None:
        childname = api._childfirstnames[AulaChildId(str(child["id"]))]
        institution = api._institutions[AulaChildId(str(child["id"]))]
        name = f"{institution} {childname}"

        unique_id = "aula" + str(child["id"])
        _LOGGER.debug("Unique ID for child " + str(child["id"]) + " " + unique_id)

        super().__init__(api, coordinator, name, unique_id)

        self._hass = hass
        self._child = child
        self._ugeplan = ugeplan
        self._parse_easyiq_ugeplan = parse_easyiq_ugeplan
        self._client = api

    @property
    def native_value(self) -> StateType:
        if self._client.presence[AulaChildId(str(self._child["id"]))] == 1:
            daily_info = self._client._daily_overview[
                AulaChildId(str(self._child["id"]))
            ]

            daily_info_status = int(daily_info["status"])
            if daily_info_status not in AulaChildPresenceType:
                daily_info_status = AulaChildPresenceType.UNKNOWN

            return AULACHILDPRESENCETYPE_TO_STATE_MAPPING[
                AulaChildPresenceType(daily_info_status)
            ]
        else:
            _LOGGER.debug("Setting state to n/a for child " + str(self._child["id"]))
            return STATE_NOT_AVAILABLE

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
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

            if self._parse_easyiq_ugeplan and "0001" in self._client.widgets:

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
