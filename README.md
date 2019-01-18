# Home Assistant: Wibeee Component

This is a custom component developed original for its integration with Circuitor Wibeee (3 Phases)

This concept has been proved on similar devices that are listed below:

| Device        | Model           | Link  |
| ------------- |:-------------:| -----:|
|Circuitor Wibeee| 3 phases | http://wibeee.circutor.com/index_en.html |
|Circuitor Wibeee| 1 phase |  http://wibeee.circutor.com/index_en.html  |
|Mirubee| Unkownn models |  https://mirubee.com/es/3-productos |


# How it works

Once the devices are installed and connected to local wireless network, current energy consumption values are exposed in xml format, the URL of the exposed web service is:

http://<wibeee_ip>/en/status.xml

Example XML are listed in hithub repository

# Home Assistant configuration

1.- Copy custom comonent into 
```
<hass_folder>/custom_components/sensor/wibeee.py
```

2.- Add device to home assistant configuration file configuration.yaml

```
- platform: wibeee
  name: "Wibeee"
  host: 192.168.xx.xx
  scan_interval: 5
```

# Useful links

Home Assistant community
https://community.home-assistant.io/t/new-integration-energy-monitoring-device-circutor-wibeee/45276
