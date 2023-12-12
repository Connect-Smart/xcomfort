### Version 1.3.6
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    SUPPORT_BRIGHTNESS,
    LightEntity,
)
import logging

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN]
    i = 0
    entities = []
    for device in coordinator.data:
        _LOGGER.debug("xcLight.init() Device: %s", device)
        if "DimAct" in device["type"] or "LightAct" in device["type"]:
            entities.append(
                xcLight(coordinator, i, device["id"], device["name"], device["type"])
            )
            i += 1
    async_add_entities(entities)


class xcLight(LightEntity):
    def __init__(self, coordinator, id, unique_name, name, type):
        self.id = id
        self._name = name
        self.type = type
        self._unique_id = unique_name
        self.coordinator = coordinator
        self.last_message_time = ""
        self.messages_per_day = ""
        self._previous_brightness = 10
        _LOGGER.debug("xcLight.init() done %s", self.name)

    @property
    def icon(self):
        if self.available:
            return "mdi:lightbulb-on" if self.is_on else "mdi:lightbulb-outline"
        else:
            return "mdi:exclamation-thick"

    @property
    def name(self):
        return self._name

    @property
    def should_poll(self):
        return True

    def update(self):
        self.async_write_ha_state()

    @property
    def is_on(self):
        if self.type == "DimActuator":
            return bool(self.coordinator.data[self.id]["value"] != "0")
        else:
            return bool(self.coordinator.data[self.id]["value"] == "ON")

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def extra_state_attributes(self):
        stats_id = str(self._unique_id).replace("xCo", "hdm:xComfort Adapter")
        try:
            self.last_message_time = self.coordinator.xc.log_stats[stats_id][
                "lastMsgTimeStamp"
            ]
        except:
            self.last_message_time = ""
            self.messages_per_day = ""
        else:
            self.messages_per_day = self.coordinator.xc.log_stats[stats_id][
                "msgsPerDay"
            ]
        return {"Messages per day": self.messages_per_day, "Last message": self.last_message_time}

    @property
    def brightness(self):
        return int(255 * float(self.coordinator.data[self.id]["value"]) / 100)

    @property
    def supported_features(self):
        return SUPPORT_BRIGHTNESS if self.type == "DimActuator" else 0

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug("xcLight.turn_on kwargs %s", kwargs)
        if self.type == "DimActuator" and ATTR_BRIGHTNESS in kwargs:
            brightness = int(100 * kwargs.get(ATTR_BRIGHTNESS, 255) / 255)
            _LOGGER.debug("xcLight.turn_on brightness %s", brightness)

            if await self.coordinator.xc.switch(self._unique_id, str(brightness)):
                self._previous_brightness = brightness  # Store the current brightness
                self.async_update_ha_state()
                _LOGGER.debug("xcLight.turn_on dimm %s success", self.name)
            else:
                _LOGGER.debug("xcLight.turn_on dimm %s unsuccessful", self.name)
        else:
            if await self.coordinator.xc.switch(self._unique_id, "on"):
                _LOGGER.debug("xcLight.turn_on %s success", self.name)
                self.async_update_ha_state()
            else:
                _LOGGER.debug("xcLight.turn_on %s unsuccessful", self.name)

    async def async_turn_off(self, **kwargs):
        # Save the previous brightness before turning off
        self._previous_brightness = self.brightness
        if await self.coordinator.xc.switch(self._unique_id, "off"):
            self.async_update_ha_state()
            _LOGGER.debug("xcLight.turn_off dimm %s success", self.name)
        else:
            _LOGGER.debug("xcLight.turn_on dimm %s unsuccessful", self.name)

    def previous_brightness(self):
        return self._previous_brightness
