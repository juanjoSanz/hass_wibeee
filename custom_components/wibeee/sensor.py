"""
Support for Energy consumption Sensors from Circutor

Device's website: http://wibeee.circutor.com/
Documentation: https://github.com/juanjoSanz/hass_wibeee/

"""

import asyncio
import logging
import voluptuous as vol
from datetime import timedelta

import aiohttp
import async_timeout
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

import xmltodict
from xml.etree import ElementTree
from requests.auth import HTTPBasicAuth, HTTPDigestAuth


import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    POWER_WATT,
    ENERGY_KILO_WATT_HOUR,
    ENERGY_WATT_HOUR,
    CONF_HOST,
    CONF_SCAN_INTERVAL,
    CONF_RESOURCE,
    CONF_METHOD
) #, CONF_PHASES)

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_utc_time_change, async_call_later
from homeassistant.util import dt as dt_util


__version__ = '0.0.1'

_LOGGER = logging.getLogger(__name__)

_RESOURCE = 'http://{}/en/status.xml'

BASE_URL = 'http://{0}{1}'
API_PATH = '/en/status.xml'


DOMAIN = 'wibeee_energy'
DEFAULT_NAME = 'Wibeee Energy Consumption Sensor'
DEFAULT_HOST = ''
DEFAULT_RESOURCE = 'http://{}/en/status.xml'
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_METHOD = "GET"
DEFAULT_PHASES = 3


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
    vol.Optional(CONF_RESOURCE, default=DEFAULT_RESOURCE): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.positive_int,
    vol.Optional(CONF_METHOD, default=DEFAULT_METHOD): vol.In(['GET']),
#    vol.Optional(CONF_PHASES, default=DEFAULT_PHASES): vol.In([1, 3]),
})

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=1)   # Default value
SCAN_INTERVAL = 1 # seconds
RETRY_INTERVAL = 0.2 # seconds


SENSOR_TYPES = {
    'vrms': ['Vrms', 'V'],
    'irms': ['Irms', 'A'],
    'frecuencia': ['Frequency', 'Hz'],
    'p_activa': ['Active Power', POWER_WATT],
    'p_reactiva_ind': ['Inductive Reactive Power', 'VArL'],
    'p_reactiva_cap': ['Capacitive Reactive Power', 'VArC'],
    'p_aparent': ['Apparent Power', 'VA'],
    'factor_potencia': ['Power Factor', ''],
    'energia_activa': ['Active Energy', ENERGY_WATT_HOUR],
    'energia_reactiva_ind': ['Inductive Reactive Energy', 'VArLh'],
    'energia_reactiva_cap': ['Capacitive Reactive Energy', 'VArCh']
}

@asyncio.coroutine
#def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the RESTful sensor."""
    _LOGGER.info("Setting up Wibeee Sensors...")

    name = "wibeee"
    host = config.get(CONF_HOST)

    # Create a DATA fetcher.
    try:
        wibeee_data = WibeeeData(hass, host)
    except ValueError as error:
        _LOGGER.error(error)
        return False

    # Then make first call to get sensors
    first_data = wibeee_data.get_sensor_names()
    if first_data == None:
        _LOGGER.error("No info fetched, unable to setup component")
        return(False)



    devices = []

    for key,value in first_data.items():
      try:
        sensor_id = key
        sensor_phase,sensor_name = key.split("_",1)
        #sensor_phase = sensor_phase.replace("fase4","total")
        #sensor_phase = sensor_phase.replace("fase","phase")
        sensor_phase = sensor_phase.replace("fase","")
        sensor_value = value
        _LOGGER.debug("Adding entity [phase:%s][sensor:%s][value:%s]", sensor_phase, sensor_id, sensor_value)
        devices.append(WibeeeSensor(name, sensor_id, sensor_phase, sensor_name,sensor_value))
      except:
        pass

    wibeee_data.add_devices(devices)
    async_add_entities(devices, True)
    #async_add_devices(devices, True)
    #await wibeee_data.fetching_data()
    async_call_later(hass, SCAN_INTERVAL, wibeee_data.fetching_data)
    _LOGGER.info("Setup completed!")
    return(True)



class WibeeeSensor(Entity):
    """Implementation of Wibeee sensor."""

    def __init__(self, name, sensor_id, sensor_phase, sensor_name, sensor_value):
        """Initialize the sensor."""
        self._sensor_id = sensor_id
        self._type = name
        self._sensor_phase = "Phase" + sensor_phase
        self._sensor_name = SENSOR_TYPES[sensor_name][0].replace(" ", "_")
        self._state = sensor_value
        self._unit_of_measurement = SENSOR_TYPES[sensor_name][1]

    @property
    def name(self):
        """Return the name of the sensor."""
        return(self._type + "_" + self._sensor_phase + "_" + self._sensor_name)


    @property
    def state(self):
        """Retrieve latest state."""
        return(self._state)

    @property
    def should_poll(self):
        """No polling needed."""
        return(False)

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return(self._unit_of_measurement)

    @asyncio.coroutine
    def async_update(self):
        """Get the latest data and updates the states."""
        _LOGGER.info("async_update for sensor " + self._sensor_id)
        pass



class WibeeeData(object):
    """Gets the latest data from Wibeee sensors."""
    def __init__(self, hass, host):
        """Initialize the data object."""
        self.timeout = 0.5
        self.api_url = BASE_URL.format(host, API_PATH)
        #self.sensor_names = ""
        self.data = None
        self.devices = None
        #self.devices_keys = None
        self.hass = hass

    def get_sensor_names(self):
        """Make first Get call to Initialize sensor names"""
        try:
            xml_data = requests.get(self.api_url, timeout=10).content
            _LOGGER.debug("First item retrieved from %s - %s", self.api_url, xml_data)
            dict_data = xmltodict.parse(xml_data)
            _LOGGER.debug("Dict data: " + str(dict_data["response"]))
            self.data = dict_data["response"]
            #self.devices_keys = dict_data["response"].keys()
            return(self.data)
        except ValueError as error:
            raise ValueError("Unable to obtain any response from %s, %s", self.api_url, error)

    def add_devices(self, _devices):
        """Set devices list"""
        self.devices = _devices

    async def fetching_data(self, *_):
        """Get the latest data and update the states"""

        def try_again(err: str):
            """Retry in RETRY_INTERVAL seconds."""
            _LOGGER.error("Retrying in %i seconds: %s", RETRY_INTERVAL, err)
            async_call_later(self.hass, RETRY_INTERVAL, self.fetching_data)

        try:
            websession = async_get_clientsession(self.hass)
            with async_timeout.timeout(self.timeout, loop=self.hass.loop):
                resp = await websession.get(self.api_url)
            if resp.status != 200:
                try_again("{} returned {}".format(resp.api_url, resp.status))
                return
            _LOGGER.debug("Data = %s", self.data)
            xml_data = await resp.text()
            dict_data = xmltodict.parse(xml_data)
            self.data = dict_data["response"]
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.info("Retrying after error: %s", err)
            try_again(err)
            return
        except ValueError as err:
            raise ValueError("Unable to obtain any response from %s, %s", self.api_url, err)
            self.data = None
            try_again(err)
            return

        await self.updating_devices()
        async_call_later(self.hass, SCAN_INTERVAL, self.fetching_data)


    async def updating_devices(self, *_):
        """Find the current data from self.data."""
        if not self.data:
            return

        # Update all devices
        _LOGGER.debug("Wibeee updating_devices()")

        tasks = []
        for dev in self.devices:
            new_state = None
            if self.data[dev._sensor_id]:
                new_state = self.data[dev._sensor_id]

            # pylint: disable=protected-access
            if new_state != dev._state:
                dev._state = new_state
                tasks.append(dev.async_update_ha_state())

        if tasks:
             await asyncio.wait(tasks)
