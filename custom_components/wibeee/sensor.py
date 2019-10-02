"""
Support for Energy consumption Sensors from Circutor

Device's website: http://wibeee.circutor.com/
Documentation: https://github.com/juanjoSanz/hass_wibeee/
"""

import logging
from datetime import timedelta

import voluptuous as vol

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from xml.etree import ElementTree
from requests.auth import HTTPBasicAuth, HTTPDigestAuth


from homeassistant.const import (POWER_WATT, ENERGY_KILO_WATT_HOUR, ENERGY_WATT_HOUR,
				 CONF_HOST, CONF_SCAN_INTERVAL, CONF_RESOURCE, CONF_METHOD) #, CONF_PHASES)
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import config_validation as cv



_LOGGER = logging.getLogger(__name__)
_RESOURCE = 'http://{}/en/status.xml'
url = ""

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

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=10)   # Default value


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



def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the RESTful sensor."""
    name = "wibeee"
    host = config.get(CONF_HOST)
    scan_interval = config.get(CONF_SCAN_INTERVAL)

    # Create a dataº fetcher. Then make first call
    try:
        wibeee_data = WibeeeData(host, scan_interval)
    except ValueError as error:
        _LOGGER.error(error)
        return False

    _LOGGER.info("Response: %s", wibeee_data.data)
    tree = ElementTree.fromstring(wibeee_data.data)
    
    devices = []
    for item in tree:
      try:
        sensor_id = item.tag
        sensor_phase,sensor_name = item.tag.split("_",1)
        sensor_phase = sensor_phase.replace("fase","")
        sensor_value = item.text

        _LOGGER.info("Adding sensor %s with value %s", sensor_id, sensor_value)

        devices.append(WibeeeSensor(hass, wibeee_data, name, sensor_id, sensor_phase, sensor_name,sensor_value))
      except:
        pass

    add_devices(devices, True)



class WibeeeSensor(Entity):
    """Implementation of Wibeee sensor."""

    def __init__(self, hass, wibeee_data, name, sensor_id, sensor_phase, sensor_name, sensor_value):
        """Initialize the sensor."""
        self._hass = hass
        self.wibeee_data = wibeee_data
        self._sensor_id = sensor_id
        self._type = name
        self._sensor_phase = "Phase" + sensor_phase
        self._sensor_name = SENSOR_TYPES[sensor_name][0].replace(" ", "_")
        self._state = sensor_value
        self._unit_of_measurement = SENSOR_TYPES[sensor_name][1]

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._type + "_" + self._sensor_phase + "_" + self._sensor_name

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    def update(self):
        """Get the latest data from API and updates the states."""
        # Call the API for new data. Each sensor will re-trigger this
        # same exact call, but that's fine. Results should be cached for
        # a short period of time to prevent hitting API limits.
        self.wibeee_data.update()

        try:
            tree = ElementTree.fromstring(self.wibeee_data.data)

            for item in tree:

                sensor_id = item.tag
                sensor_value = item.text

                if sensor_id == self._sensor_id:
                   self._state = sensor_value

        except:
            _LOGGER.warning("Could not update status for %s", self._sensor_id)


class WibeeeData(object):
    """Gets the latest data from HP ILO."""

    def __init__(self, host, scan_interval):
        """Initialize the data object."""
        self._host = host
        self._url = _RESOURCE.format(host)
        self._scan_interval = scan_interval
        #MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=int(self._scan_interval))

        self.data = None

        self.update()

    #@Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data"""

        try:
            response = requests.get(self._url, timeout=10)
            self.data = response.content
        except ValueError as error:
            raise ValueError("Unable to obtain any response from %s, %s", self._url, error)

