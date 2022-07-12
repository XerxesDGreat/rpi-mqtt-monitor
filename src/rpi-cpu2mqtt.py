# -*- coding: utf-8 -*-
# Python script (runs on 2 and 3) to check cpu load, cpu temperature and free space etc.
# on a Raspberry Pi or Ubuntu computer and publish the data to a MQTT server.
# RUN pip install paho-mqtt
# RUN sudo apt-get install python-pip

from __future__ import division
from logging.config import dictConfig
import config

# configure logging before bringing in other modules
dictConfig(config.log_config)

import json
import logging
import metrics as m
import os
import paho.mqtt.client as paho
import socket
import subprocess
import time


# get device host name - used in mqtt topic
hostname = socket.gethostname()

def config_json(what_config):
    model_name = m.check_model_name()
    data = {
        "state_topic": "",
        "icon": "",
        "name": "",
        "unique_id": "",
        "unit_of_measurement": "",
	"device": {
	    "identifiers": [hostname],
	    "manufacturer": "Raspberry Pi",
	    "model": model_name,
	    "name": hostname
	}
    }

    data["state_topic"] = config.mqtt_topic_prefix + "/" + hostname + "/" + what_config
    data["unique_id"] = hostname + "_" + what_config
    if what_config == "cpuload":
        data["icon"] = "mdi:speedometer"
        data["name"] = hostname + " CPU Usage"
        data["unit_of_measurement"] = "%"
    elif what_config == "cputemp":
        data["icon"] = "hass:thermometer"
        data["name"] = hostname + " CPU Temperature"
        data["unit_of_measurement"] = "°C"
    elif what_config == "diskusage":
        data["icon"] = "mdi:harddisk"
        data["name"] = hostname + " Disk Usage"
        data["unit_of_measurement"] = "%"
    elif what_config == "voltage":
        data["icon"] = "mdi:speedometer"
        data["name"] = hostname + " CPU Voltage"
        data["unit_of_measurement"] = "V"
    elif what_config == "swap":
        data["icon"] = "mdi:harddisk"
        data["name"] = hostname + " Disk Swap"
        data["unit_of_measurement"] = "%"
    elif what_config == "memory":
        data["icon"] = "mdi:memory"
        data["name"] = hostname + " Memory Usage"
        data["unit_of_measurement"] = "%"
    elif what_config == "sys_clock_speed":
        data["icon"] = "mdi:speedometer"
        data["name"] = hostname + " CPU Clock Speed"
        data["unit_of_measurement"] = "MHz"
    elif what_config == "uptime_days":
        data["icon"] = "mdi:timer"
        data["name"] = hostname + " Uptime"
        data["unit_of_measurement"] = "days"
    else:
        return ""
    # Return our built discovery config
    return json.dumps(data)


def publish_to_mqtt(cpu_load=0, cpu_temp=0, used_space=0, voltage=0, sys_clock_speed=0, swap=0, memory=0,
                    uptime_days=0):
    # connect to mqtt server
    client = paho.Client()
    client.username_pw_set(config.mqtt_user, config.mqtt_password)
    client.connect(config.mqtt_host, int(config.mqtt_port))

    # publish monitored values to MQTT
    if config.cpu_load:
        if config.discovery_messages:
            client.publish("homeassistant/sensor/" + config.mqtt_topic_prefix + "/" + hostname + "_cpuload/config",
                           config_json('cpuload'), qos=0)
            time.sleep(config.sleep_time)
        client.publish(config.mqtt_topic_prefix + "/" + hostname + "/cpuload", cpu_load, qos=1)
        time.sleep(config.sleep_time)
    if config.cpu_temp:
        if config.discovery_messages:
            client.publish("homeassistant/sensor/" + config.mqtt_topic_prefix + "/" + hostname + "_cputemp/config",
                           config_json('cputemp'), qos=0)
            time.sleep(config.sleep_time)
        client.publish(config.mqtt_topic_prefix + "/" + hostname + "/cputemp", cpu_temp, qos=1)
        time.sleep(config.sleep_time)
    if config.used_space:
        if config.discovery_messages:
            client.publish("homeassistant/sensor/" + config.mqtt_topic_prefix + "/" + hostname + "_diskusage/config",
                           config_json('diskusage'), qos=0)
            time.sleep(config.sleep_time)
        client.publish(config.mqtt_topic_prefix + "/" + hostname + "/diskusage", used_space, qos=1)
        time.sleep(config.sleep_time)
    if config.voltage:
        if config.discovery_messages:
            client.publish("homeassistant/sensor/" + config.mqtt_topic_prefix + "/" + hostname + "_voltage/config",
                           config_json('voltage'), qos=0)
            time.sleep(config.sleep_time)
        client.publish(config.mqtt_topic_prefix + "/" + hostname + "/voltage", voltage, qos=1)
        time.sleep(config.sleep_time)
    if config.swap:
        if config.discovery_messages:
            client.publish("homeassistant/sensor/" + config.mqtt_topic_prefix + "/" + hostname + "_swap/config",
                           config_json('swap'), qos=0)
            time.sleep(config.sleep_time)
        client.publish(config.mqtt_topic_prefix + "/" + hostname + "/swap", swap, qos=1)
        time.sleep(config.sleep_time)
    if config.memory:
        if config.discovery_messages:
            client.publish("homeassistant/sensor/" + config.mqtt_topic_prefix + "/" + hostname + "_memory/config",
                           config_json('memory'), qos=0)
            time.sleep(config.sleep_time)
        client.publish(config.mqtt_topic_prefix + "/" + hostname + "/memory", memory, qos=1)
        time.sleep(config.sleep_time)
    if config.sys_clock_speed:
        if config.discovery_messages:
            client.publish(
                "homeassistant/sensor/" + config.mqtt_topic_prefix + "/" + hostname + "_sys_clock_speed/config",
                config_json('sys_clock_speed'), qos=0)
            time.sleep(config.sleep_time)
        client.publish(config.mqtt_topic_prefix + "/" + hostname + "/sys_clock_speed", sys_clock_speed, qos=1)
        time.sleep(config.sleep_time)
    if config.uptime:
        if config.discovery_messages:
            client.publish("homeassistant/sensor/" + config.mqtt_topic_prefix + "/" + hostname + "_uptime_days/config",
                           config_json('uptime_days'), qos=0)
            time.sleep(config.sleep_time)
        client.publish(config.mqtt_topic_prefix + "/" + hostname + "/uptime_days", uptime_days, qos=1)
        time.sleep(config.sleep_time)
    # disconnect from mqtt server
    client.disconnect()


def bulk_publish_to_mqtt(cpu_load=0, cpu_temp=0, used_space=0, voltage=0, sys_clock_speed=0, swap=0, memory=0,
                         uptime_days=0):
    # compose the CSV message containing the measured values

    values = cpu_load, float(cpu_temp), used_space, float(voltage), int(sys_clock_speed), swap, memory, uptime_days
    values = str(values)[1:-1]

    # connect to mqtt server
    client = paho.Client()
    client.username_pw_set(config.mqtt_user, config.mqtt_password)
    client.connect(config.mqtt_host, int(config.mqtt_port))

    # publish monitored values to MQTT
    client.publish(config.mqtt_topic_prefix + "/" + hostname, values, qos=1)

    # disconnect from mqtt server
    client.disconnect()


if __name__ == '__main__':
    # set all monitored values to False in case they are turned off in the config
    cpu_load = cpu_temp = used_space = voltage = sys_clock_speed = swap = memory = uptime_days = False

    # delay the execution of the script
    time.sleep(config.random_delay)

    # collect the monitored values
    if config.cpu_load:
        cpu_load = m.check_cpu_load()
    if config.cpu_temp:
        cpu_temp = m.check_cpu_temp()
    if config.used_space:
        used_space = m.check_used_space('/')
    if config.voltage:
        voltage = m.check_voltage()
    if config.sys_clock_speed:
        sys_clock_speed = m.check_sys_clock_speed()
    if config.swap:
        swap = m.check_swap()
    if config.memory:
        memory = m.check_memory()
    if config.uptime:
        uptime_days = m.check_uptime()
    # Publish messages to MQTT
    if config.group_messages:
        bulk_publish_to_mqtt(cpu_load, cpu_temp, used_space, voltage, sys_clock_speed, swap, memory, uptime_days)
    else:
        publish_to_mqtt(cpu_load, cpu_temp, used_space, voltage, sys_clock_speed, swap, memory, uptime_days)
