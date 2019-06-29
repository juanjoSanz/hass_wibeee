""" Suport for Circutor Energy consumption analyzer http://wibeee.circutor.com/

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.circutor_wibeee/ (ToDO)
"""

# ToDO: https://raw.githubusercontent.com/home-assistant/home-assistant/cfd8d708904208ef6f1afafd214704b2095f7b10/homeassistant/components/pi_hole/sensor.py
# https://www.home-assistant.io/components/pi_hole/
# And  https://github.com/home-assistant/home-assistant/blob/cfd8d708904208ef6f1afafd214704b2095f7b10/homeassistant/components/tautulli/sensor.py#L133
# Use xmltodict ??? xml to json or other parser to have wibeee data in a readable format
# ???


from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_HOST, CONF_MONITORED_CONDITIONS, CONF_NAME, CONF_SSL, CONF_VERIFY_SSL)
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

ATTR_BLOCKED_DOMAINS = 'domains_blocked'
ATTR_PERCENTAGE_TODAY = 'percentage_today'
ATTR_QUERIES_TODAY = 'queries_today'

CONF_LOCATION = 'location'
DEFAULT_HOST = 'localhost'

DEFAULT_LOCATION = 'admin'
DEFAULT_METHOD = 'GET'
DEFAULT_NAME = 'Pi-Hole'
DEFAULT_SSL = False
DEFAULT_VERIFY_SSL = True

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=10)

MONITORED_CONDITIONS = {
    'ads_blocked_today':
        ['Ads Blocked Today', 'ads', 'mdi:close-octagon-outline'],
    'ads_percentage_today':
        ['Ads Percentage Blocked Today', '%', 'mdi:close-octagon-outline'],
    'clients_ever_seen':
        ['Seen Clients', 'clients', 'mdi:account-outline'],
    'dns_queries_today':
        ['DNS Queries Today', 'queries', 'mdi:comment-question-outline'],
    'domains_being_blocked':
        ['Domains Blocked', 'domains', 'mdi:block-helper'],
    'queries_cached':
        ['DNS Queries Cached', 'queries', 'mdi:comment-question-outline'],
    'queries_forwarded':
        ['DNS Queries Forwarded', 'queries', 'mdi:comment-question-outline'],
    'unique_clients':
        ['DNS Unique Clients', 'clients', 'mdi:account-outline'],
    'unique_domains':
        ['DNS Unique Domains', 'domains', 'mdi:domain'],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_SSL, default=DEFAULT_SSL): cv.boolean,
    vol.Optional(CONF_LOCATION, default=DEFAULT_LOCATION): cv.string,
    vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean,
    vol.Optional(CONF_MONITORED_CONDITIONS,
                 default=['ads_blocked_today']):
    vol.All(cv.ensure_list, [vol.In(MONITORED_CONDITIONS)]),
})


async def async_setup_platform(
        hass, config, async_add_entities, discovery_info=None):
    """Set up the Pi-hole sensor."""
    from hole import Hole

    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    use_tls = config.get(CONF_SSL)
    location = config.get(CONF_LOCATION)
    verify_tls = config.get(CONF_VERIFY_SSL)

    session = async_get_clientsession(hass, verify_tls)
    pi_hole = PiHoleData(Hole(
        host, hass.loop, session, location=location, tls=use_tls))

    await pi_hole.async_update()

    if pi_hole.api.data is None:
        raise PlatformNotReady

    sensors = [PiHoleSensor(pi_hole, name, condition)
               for condition in config[CONF_MONITORED_CONDITIONS]]

    async_add_entities(sensors, True)


class PiHoleSensor(Entity):
    """Representation of a Pi-hole sensor."""

    def __init__(self, pi_hole, name, condition):
        """Initialize a Pi-hole sensor."""
        self.pi_hole = pi_hole
        self._name = name
        self._condition = condition

        variable_info = MONITORED_CONDITIONS[condition]
        self._condition_name = variable_info[0]
        self._unit_of_measurement = variable_info[1]
        self._icon = variable_info[2]
        self.data = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return "{} {}".format(self._name, self._condition_name)

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    @property
    def state(self):
        """Return the state of the device."""
        try:
            return round(self.data[self._condition], 2)
        except TypeError:
            return self.data[self._condition]

    @property
    def device_state_attributes(self):
        """Return the state attributes of the Pi-Hole."""
        return {
            ATTR_BLOCKED_DOMAINS: self.data['domains_being_blocked'],
        }

    @property
    def available(self):
        """Could the device be accessed during the last update call."""
        return self.pi_hole.available

    async def async_update(self):
        """Get the latest data from the Pi-hole API."""
        await self.pi_hole.async_update()
        self.data = self.pi_hole.api.data


class PiHoleData:
    """Get the latest data and update the states."""

    def __init__(self, api):
        """Initialize the data object."""
        self.api = api
        self.available = True

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Get the latest data from the Pi-hole."""
        from hole.exceptions import HoleError

        try:
            await self.api.get_data()
            self.available = True
        except HoleError:
            _LOGGER.error("Unable to fetch data from Pi-hole")
            self.available = False
            
            
            
            


# TODO
#
# ref: https://raw.githubusercontent.com/custom-components/sensor.versions/master/custom_components/sensor/versions.py


import logging
from datetime import timedelta

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_SCAN_INTERVAL, CONF_RESOURCE, CONF_METHOD
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
# Custom Imports
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from xml.etree import ElementTree
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

__version__ = '0.0.1'

REQUIREMENTS = ['pyhaversion==2.0.1']

_LOGGER = logging.getLogger(__name__)

CONF_HOST = ""
CONF_RESOURCE = 'http://{}/en/status.xml'
CONF_METHOD = "GET"


DEFAULT_NAME = 'Wibeee Energy Consumption Sensor'
DEFAULT_HOST = ""
DEFAULT_RESOURCE = 'http://{}/en/status.xml'
DEFAULT_METHOD = "GET"

ICON = 'mdi:package-up'


TIME_BETWEEN_UPDATES = timedelta(seconds=10)   # Default value


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_IMAGE, default=DEFAULT_IMAGE): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,    
    vol.Optional(CONF_RESOURCE, default=DEFAULT_RESOURCE): cv.string,        
    vol.Optional(CONF_METHOD, default=DEFAULT_METHOD): cv.string,         
})



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


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
     """Set up the RESTful sensor."""
    from pyhaversion import Version
    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    url = config.get(CONF_RESOURCE)
    scan_interval = config.get(CONF_SCAN_INTERVAL)

    session = async_get_clientsession(hass)
    haversion = VersionData(Version(hass.loop, session), source)
    
    
    # Create a data fetcher. Then make first call
    try:
        wibeee_data = WibeeeData(host, url, scan_interval)
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

    #add_devices(devices, True)
    async_add_entities([VersionSensor(haversion, devices)], True)

    
  


class WibeeeSensor(Entity):
    """Representation of a Home Assistant Wibeee sensor."""

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

    async def async_update(self):
        """Get the latest version information."""
        await self.haversion.async_update()

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
        #return self.haversion.api.version
        return self._state
    
    @property
    def device_state_attributes(self):
        """Return attributes for the sensor."""
        return self.haversion.api.version_data

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

    def __init__(self, host, url, scan_interval):
        """Initialize the data object."""
        self._host = host
        self._url = url.format(host)
        self._scan_interval = scan_interval
        #TIME_BETWEEN_UPDATES = timedelta(seconds=int(self._scan_interval))

        self.data = None

        self.update()

    @Throttle(TIME_BETWEEN_UPDATES)
    def async_update(self):
        """Get the latest data and update the states"""
        #if self.source == 'pypi':
        #    await self.api.get_pypi_version()
        #elif self.source == 'hassio':
        #    await self.api.get_hassio_version()
        #elif self.source == 'docker':
        #    await self.api.get_docker_version()
        #else:
        #    await self.api.get_local_version()
        try:
            response = requests.get(self._url, timeout=10)
            self.data = response.content
        except ValueError as error:
            raise ValueError("Unable to obtain any response from %s, %s", self._url, error)
            


