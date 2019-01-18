""" Suport for Circutor Energy consumption analyzer http://wibeee.circutor.com/

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.circutor_wibeee/ (ToDO)
"""

import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME, CONF_HOST, CONF_SCAN_INTERVAL)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv

import requests
from xml.etree import ElementTree
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

_LOGGER = logging.getLogger(__name__)
_RESOURCE = 'http://{}/en/status.xml'
url = ""


DEFAULT_METHOD = 'GET'
DEFAULT_NAME = 'Wibeee Energy Consumption Sensor'

#	Vrms</td>
#	"vrms"></td>
#	Irms</td>
#	"irms"></td>
#	Frequency</td>
#	"frecuencia"></td>
#	Active Power</td>
#	"p_activa"></td>
#	Inductive Reactive Power</td>
#	"p_reactiva_ind"></td>
#	Capacitive Reactive Power</td>
#	"p_reactiva_cap"></td>
#	Apparent Power</td>
#	"p_aparent"></td>
#	Power Factor</td>
#	"factor_potencia"></td>
#	Active Energy</td>
#	"energia_activa"></td>
#	Inductive Reactive Energy</td>
#	"energia_reactiva_ind"></td>
#	Capacitive Reactive Energy</td>
#	"energia_reactiva_cap"></td>
#
# <fase1_vrms>239.63</fase1_vrms>
#<fase1_irms>0.86</fase1_irms>
#<fase1_p_aparent>205.10</fase1_p_aparent>
#<fase1_p_activa>19.45</fase1_p_activa>
#<ease1_p_reactiva_ine>197.52</fase1_p_reactiva_ind>
#<fase1_p_reactiva_cap>0.00</fase1_p_reactiva_cap>
#<fase1_frecuencia>50.02</fase1_frecuencia>
#<fase1_factor_potencia>-0.095</fase1_factor_potencia>
#<fase1_energia_activa>30264.84</fase1_energia_activa>
#<fase1_energia_reactiva_ind>87130.35</fase1_energia_reactiva_ind>
#<fase1_energia_reactiva_cap>8066.87</fase1_energia_reactiva_cap>

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=10)   # Default value

SENSOR_TYPES = {
    'vrms': ['Vrms', 'V'],
    'irms': ['Irms', 'A'],
    'frecuencia': ['Frequency', 'Hz'],
    'p_activa': ['Active Power', 'W'],
    'p_reactiva_ind': ['Inductive Reactive Power', 'VArL'],
    'p_reactiva_cap': ['Capacitive Reactive Power', 'VArC'],
    'p_aparent': ['Apparent Power', 'VA'],
    'factor_potencia': ['Power Factor', ' '],
    'energia_activa': ['Active Energy', 'Wh'],
    'energia_reactiva_ind': ['Inductive Reactive Energy', 'VArLh'],
    'energia_reactiva_cap': ['Capacitive Reactive Energy', 'VArCh']
}


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the RESTful sensor."""
    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    scan_interval = config.get(CONF_SCAN_INTERVAL)


    # Create a data fetcher. Then make first call
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

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data"""

        try:
            response = requests.get(self._url, timeout=10)
            self.data = response.content
        except ValueError as error:
            raise ValueError("Unable to obtain any response from %s, %s", self._url, error)
