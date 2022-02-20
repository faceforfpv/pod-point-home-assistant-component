"""PodPointEntity class"""
import logging
from typing import Any, Dict
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from datetime import datetime, timedelta

_LOGGER: logging.Logger = logging.getLogger(__package__)

from .const import (
    ATTR_STATE_CHARGING,
    DOMAIN,
    NAME,
    VERSION,
    ATTRIBUTION,
    ATTR_COMMISSIONED,
    ATTR_CONNECTOR,
    ATTR_CONNECTOR_CHARGE_METHOD,
    ATTR_CONNECTOR_CURRENT,
    ATTR_CONNECTOR_DOOR,
    ATTR_CONNECTOR_DOOR_ID,
    ATTR_CONNECTOR_HAS_CABLE,
    ATTR_CONNECTOR_ID,
    ATTR_CONNECTOR_POWER,
    ATTR_CONNECTOR_SOCKET,
    ATTR_CONNECTOR_SOCKET_OCPP_CODE,
    ATTR_CONNECTOR_SOCKET_OCPP_NAME,
    ATTR_CONNECTOR_SOCKET_TYPE,
    ATTR_CONNECTOR_VOLTAGE,
    ATTR_CONTACTLESS_ENABLED,
    ATTR_CREATED,
    ATTR_EVZONE,
    ATTR_HOME,
    ATTR_ID,
    ATTR_LAST_CONTACT,
    ATTR_LAT,
    ATTR_LNG,
    ATTR_MODEL,
    ATTR_PAYG,
    ATTR_PRICE,
    ATTR_PSL,
    ATTR_PUBLIC,
    ATTR_STATUS,
    ATTR_STATUS_DOOR,
    ATTR_STATUS_DOOR_ID,
    ATTR_STATUS_KEY_NAME,
    ATTR_STATUS_LABEL,
    ATTR_STATUS_NAME,
    ATTR_TIMEZONE,
    ATTR_UNIT_ID,
    ATTR_STATE_RANKING,
    ATTR_STATE,
    ATTR_STATE_WAITING,
    ATTR_IMAGE,
    APP_IMAGE_URL_BASE,
)


class PodPointEntity(CoordinatorEntity):
    """Pod Point Entity"""

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator)
        self._pod_id = None
        self.config_entry = config_entry

    @property
    def pod_id(self):
        """Set the pod index for this entity"""
        return self._pod_id

    @pod_id.setter
    def pod_id(self, pod_id):
        self._pod_id = pod_id

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return self.config_entry.entry_id

    @property
    def device_info(self):
        name = NAME
        if len(self.psl) > 0:
            name = self.psl

        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": name,
            "model": self.model,
            "manufacturer": NAME,
        }

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        # return {
        #     "attribution": ATTRIBUTION,
        #     "id": str(self.coordinator.data.get("id")),
        #     "integration": DOMAIN,
        # }
        data = self.coordinator.data[self.pod_id]

        attrs = {
            "attribution": ATTRIBUTION,
            "id": str(data.get("id")),
            "integration": DOMAIN,
            "suggested_area": "Outside",
        }

        state = None

        attrs[ATTR_ID] = data.get("id")
        attrs[ATTR_PSL] = data.get("ppid", None)
        attrs[ATTR_PAYG] = data.get("payg", None)
        attrs[ATTR_HOME] = data.get("home", None)
        attrs[ATTR_PUBLIC] = data.get("public", None)
        attrs[ATTR_EVZONE] = data.get("evZone", None)
        attrs[ATTR_COMMISSIONED] = data.get("commissioned_at", None)
        attrs[ATTR_CREATED] = data.get("created_at", None)
        attrs[ATTR_LAST_CONTACT] = data.get("last_contact_at", None)
        attrs[ATTR_UNIT_ID] = data.get("unit_id", None)
        attrs[ATTR_CONTACTLESS_ENABLED] = data.get("contactless_enabled", None)
        attrs[ATTR_TIMEZONE] = data.get("timezone", None)
        attrs[ATTR_PRICE] = data.get("price", None)

        if data.get("location", False):
            location_obj = data.get("location", {})
            attrs[ATTR_LAT] = location_obj.get("lat", None)
            attrs[ATTR_LNG] = location_obj.get("lng", None)

        if data.get("model", False):
            attrs[ATTR_MODEL] = data.get("model", {}).get("name", None)

        statuses = data.get("statuses", [])
        if len(statuses) > 0:
            status_prefix = ATTR_STATUS

            if len(statuses) == 1:
                status_object = statuses[0]
                status_attributes = self.__populate_status_attr(
                    status_prefix, status_object
                )
                pod_state = status_attributes.get(
                    f"{status_prefix}_{ATTR_STATUS_KEY_NAME}", None
                )
                _LOGGER.debug(status_attributes)
                _LOGGER.debug(pod_state)
                state = self.compare_state(
                    state,
                    pod_state,
                )
                attrs.update(status_attributes)
            else:
                for i in range(len(statuses)):
                    status_obj = data.get("statuses", None)[i]
                    status_attributes = self.__populate_status_attr(
                        f"{status_prefix}_{i}", status_obj
                    )
                    pod_state = status_attributes.get(
                        f"{status_prefix}_{i}_{ATTR_STATUS_KEY_NAME}", None
                    )
                    _LOGGER.debug(status_attributes)
                    _LOGGER.debug(pod_state)
                    state = self.compare_state(
                        state,
                        pod_state,
                    )
                    attrs.update(status_attributes)

        connectors_list = data.get("unit_connectors", [])
        if len(connectors_list) > 0:
            connector_prefix = ATTR_CONNECTOR

            if len(connectors_list) == 1:
                connector_object = connectors_list[0].get("connector", {})
                connector_attributes = self.__populate_connector_attr(
                    connector_prefix, connector_object
                )
                attrs.update(connector_attributes)
            else:
                for i in range(len(connectors_list)):
                    connector_object = connectors_list[i]
                    connector_attributes = self.__populate_connector_attr(
                        f"{connector_prefix}_{i}", connector_object.get("connector", {})
                    )
                    attrs.update(connector_attributes)

        _LOGGER.debug(state)
        _LOGGER.debug(f"Charging allowed: {self.charging_allowed}")

        is_charging_state = state == ATTR_STATE_CHARGING
        charging_not_allowed = self.charging_allowed is False
        should_be_waiting_state = is_charging_state and charging_not_allowed

        _LOGGER.debug(f"Is charging state: {is_charging_state}")
        _LOGGER.debug(f"Charging not allowed: {charging_not_allowed}")
        _LOGGER.debug(f"Should be waiting state: {should_be_waiting_state}")

        if should_be_waiting_state:
            state = ATTR_STATE_WAITING

        _LOGGER.info(f"Computed state: {state}")

        attrs[ATTR_STATE] = state
        return attrs

    @property
    def charging_allowed(self):
        """Is charging allowed by schedule?"""
        _LOGGER.info("Getting schedules")

        schedules = self.coordinator.data[self.pod_id].get("charge_schedules", [])

        _LOGGER.debug(schedules)

        # No schedules are found, we will assume we can charge
        if len(schedules) <= 0:
            return True

        _LOGGER.debug("More than 0")

        weekday = datetime.today().weekday() + 1
        schedule_for_day = next(
            (
                schedule
                for schedule in schedules
                if schedule.get("start_day", 100) == weekday
            ),
            None,
        )

        _LOGGER.debug(f"Weekday {weekday}")
        _LOGGER.debug(f"Schedule for day:")
        _LOGGER.debug(schedule_for_day)

        # If no schedule is set for our day, return False early, there should always be a
        # schedule for each day, even if it is inactive
        if schedule_for_day is None:
            return False

        schedule_active = schedule_for_day.get("status", {}).get("is_active", None)

        # If schedule_active is None, there was a problem. we will return False
        if schedule_active is None:
            return False

        _LOGGER.debug(f"Schedule active: {schedule_active}")

        # If the schedule for this day is not active, we can charge
        if schedule_active is False:
            return True

        start_time = list(
            map(
                lambda x: int(x), schedule_for_day.get("start_time", "0:0:0").split(":")
            )
        )

        start_date = datetime.now().replace(
            hour=start_time[0], minute=start_time[1], second=start_time[2]
        )

        _LOGGER.debug(f"start: {start_date}")

        end_time = list(
            map(lambda x: int(x), schedule_for_day.get("end_time", "0:0:0").split(":"))
        )
        end_day = schedule_for_day.get("end_day", weekday)
        end_date = None
        if end_day < weekday:
            # roll into next week
            end_time = end_date = datetime.now().replace(
                hour=end_time[0], minute=end_time[1], second=end_time[2]
            )

            # How many days do we add to the current date to get to the desired end day?
            day_offset = (7 - weekday) + (end_day - 1)
            end_date = end_time + timedelta(days=day_offset)
        elif end_day > weekday:
            offset = end_day - weekday

            end_time = end_date = datetime.now().replace(
                hour=end_time[0], minute=end_time[1], second=end_time[2]
            )
            end_date = end_time + timedelta(days=day_offset)
        else:
            end_date = datetime.now().replace(
                hour=end_time[0], minute=end_time[1], second=end_time[2]
            )

        _LOGGER.debug(f"end: {end_date}")

        # Problem creating the end_date, so we will exit with False
        if end_date is None:
            return False

        in_range = start_date <= datetime.now() <= end_date

        _LOGGER.debug(f"in range: {in_range}")

        # Are we within the range for today?
        return in_range

    @property
    def unit_id(self):
        """Return the unit id - used for schedule updates"""
        return self.extra_state_attributes[ATTR_UNIT_ID]

    @property
    def psl(self):
        """Return the PSL - used for identifying multiple pods"""
        return self.extra_state_attributes.get(ATTR_PSL, "")

    @property
    def model(self):
        """Return the model of our podpoint"""
        return self.extra_state_attributes[ATTR_MODEL]

    @property
    def image(self):
        """Return the image url for this model"""
        return self.__pod_image(self.model)

    def compare_state(self, state, pod_state):
        """Given two states, which one is most important"""
        ranking = ATTR_STATE_RANKING

        # If pod state is None, but state is set, return the state
        if pod_state is None and state is not None:
            return state
        elif state is None and pod_state is not None:
            return pod_state

        try:
            state_rank = ranking.index(state)
        except ValueError:
            state_rank = 100

        try:
            pod_rank = ranking.index(pod_state)
        except ValueError:

            pod_rank = 100

        winner = state if state_rank >= pod_rank else pod_state

        _LOGGER.debug(f"Winning state: {winner} from {state} and {pod_state}")

        return winner

    def __populate_status_attr(
        self, status_prefix: str, status_object: Dict[str, Any]
    ) -> Dict[str, Any]:
        key = f"{status_prefix}_"

        attrs = {}
        attrs[status_prefix] = status_object.get("id", None)
        attrs[f"{key}{ATTR_STATUS_NAME}"] = status_object.get("name", None)
        attrs[f"{key}{ATTR_STATUS_KEY_NAME}"] = status_object.get("key_name", None)
        attrs[f"{key}{ATTR_STATUS_LABEL}"] = status_object.get("label", None)
        attrs[f"{key}{ATTR_STATUS_DOOR}"] = status_object.get("door", None)
        attrs[f"{key}{ATTR_STATUS_DOOR_ID}"] = status_object.get("door_id", None)

        return attrs

    def __populate_connector_attr(
        self, connector_prefix: str, connector_object: Dict[str, Any]
    ) -> Dict[str, Any]:
        key = f"{connector_prefix}_"

        attrs = {}
        attrs[connector_prefix] = connector_object.get("id", None)
        attrs[f"{key}{ATTR_CONNECTOR_ID}"] = connector_object.get("id", None)
        attrs[f"{key}{ATTR_CONNECTOR_DOOR}"] = connector_object.get("door", None)
        attrs[f"{key}{ATTR_CONNECTOR_DOOR_ID}"] = connector_object.get("door_id", None)
        attrs[f"{key}{ATTR_CONNECTOR_POWER}"] = connector_object.get("power", None)
        attrs[f"{key}{ATTR_CONNECTOR_CURRENT}"] = connector_object.get("current", None)
        attrs[f"{key}{ATTR_CONNECTOR_VOLTAGE}"] = connector_object.get("voltage", None)
        attrs[f"{key}{ATTR_CONNECTOR_CHARGE_METHOD}"] = connector_object.get(
            "charge_method", None
        )
        attrs[f"{key}{ATTR_CONNECTOR_HAS_CABLE}"] = connector_object.get(
            "has_cable", None
        )

        if connector_object.get("socket", False):
            socket_obj = connector_object.get("socket", {})
            attrs[f"{key}{ATTR_CONNECTOR_SOCKET}"] = socket_obj.get("description", None)
            attrs[
                f"{key}{ATTR_CONNECTOR_SOCKET}_{ATTR_CONNECTOR_SOCKET_TYPE}"
            ] = socket_obj.get("descripttypeion", None)
            attrs[
                f"{key}{ATTR_CONNECTOR_SOCKET}_{ATTR_CONNECTOR_SOCKET_OCPP_NAME}"
            ] = socket_obj.get("ocpp_name", None)
            attrs[
                f"{key}{ATTR_CONNECTOR_SOCKET}_{ATTR_CONNECTOR_SOCKET_OCPP_CODE}"
            ] = socket_obj.get("ocpp_code", None)

        return attrs

    def __pod_image(self, model):
        if model is None:
            return None

        model_slug = model.upper()[3:8].split("-")
        type = model_slug[0]
        model_id = model_slug[1]

        if type == "UP":
            type = "UC"

        img = type
        if model_id == "03":
            img = f"{type}-{model_id}"

        return f"{APP_IMAGE_URL_BASE}/{img.lower()}.png"
