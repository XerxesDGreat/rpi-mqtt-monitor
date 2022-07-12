# -*- coding: utf-8 -*-
# Python script (runs on 2 and 3) to check cpu load, cpu temperature and free space etc.
# on a Raspberry Pi or Ubuntu computer and publish the data to a MQTT server.
# RUN pip install paho-mqtt
# RUN sudo apt-get install python-pip

from __future__ import division
from collections import namedtuple
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


# get device host and model names as these are constant
hostname = socket.gethostname()
modelname = m.check_model_name()

# named tuple for the metrics configuration details
MetricConfig = namedtuple("MetricConfig", ["icon", "name", "unit_of_measurement", "should_measure", "measure_func"])

# list of all the metrics and their configurations
metrics = {
    "cpu_load": MetricConfig("mdi:speedometer", "CPU Usage", "%", config.cpu_load, m.check_cpu_load),
    "cpu_temp": MetricConfig("hass:thermometer", "CPU Temperature", "°C", config.cpu_temp, m.check_cpu_temp),
    "used_space": MetricConfig("mdi:harddisk", "Disk Usage", "%", config.used_space, m.check_used_space),
    "voltage": MetricConfig("mdi:sine-wave", "CPU Voltage", "V", config.voltage, m.check_voltage),
    "sys_clock_speed": MetricConfig("mdi:speedometer", "CPU Clock Speed", "MHz", config.sys_clock_speed, m.check_sys_clock_speed),
    "swap": MetricConfig("mdi:harddisk", "Disk Swap", "%", config.swap, m.check_swap),
    "memory": MetricConfig("mdi:memory", "Memory Usage", "%", config.memory, m.check_memory),
    "uptime": MetricConfig("mdi:timer", "Uptime", "days", config.uptime, m.check_uptime),
}

def build_discovery_payload(metric_name):
    metric_config = metrics.get(metric_name)
    if metric_config is None:
        return ""

    data = {
        "state_topic": f'{config.mqtt_topic_prefix}/{hostname}/{metric_name}',
        "icon": metric_config.icon,
        "name": f'{hostname} {metric_config.name}',
        "unique_id": f'{hostname}_{metric_name}',
        "unit_of_measurement": metric_config.unit_of_measurement,
        "device": {
            "identifiers": [hostname],
            "manufacturer": "Raspberry Pi",
            "model": modelname,
            "name": hostname
        }
    }

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
                           build_discovery_payload('cpuload'), qos=0)
            time.sleep(config.sleep_time)
        client.publish(config.mqtt_topic_prefix + "/" + hostname + "/cpuload", cpu_load, qos=1)
        time.sleep(config.sleep_time)
    if config.cpu_temp:
        if config.discovery_messages:
            client.publish("homeassistant/sensor/" + config.mqtt_topic_prefix + "/" + hostname + "_cputemp/config",
                           build_discovery_payload('cputemp'), qos=0)
            time.sleep(config.sleep_time)
        client.publish(config.mqtt_topic_prefix + "/" + hostname + "/cputemp", cpu_temp, qos=1)
        time.sleep(config.sleep_time)
    if config.used_space:
        if config.discovery_messages:
            client.publish("homeassistant/sensor/" + config.mqtt_topic_prefix + "/" + hostname + "_diskusage/config",
                           build_discovery_payload('diskusage'), qos=0)
            time.sleep(config.sleep_time)
        client.publish(config.mqtt_topic_prefix + "/" + hostname + "/diskusage", used_space, qos=1)
        time.sleep(config.sleep_time)
    if config.voltage:
        if config.discovery_messages:
            client.publish("homeassistant/sensor/" + config.mqtt_topic_prefix + "/" + hostname + "_voltage/config",
                           build_discovery_payload('voltage'), qos=0)
            time.sleep(config.sleep_time)
        client.publish(config.mqtt_topic_prefix + "/" + hostname + "/voltage", voltage, qos=1)
        time.sleep(config.sleep_time)
    if config.swap:
        if config.discovery_messages:
            client.publish("homeassistant/sensor/" + config.mqtt_topic_prefix + "/" + hostname + "_swap/config",
                           build_discovery_payload('swap'), qos=0)
            time.sleep(config.sleep_time)
        client.publish(config.mqtt_topic_prefix + "/" + hostname + "/swap", swap, qos=1)
        time.sleep(config.sleep_time)
    if config.memory:
        if config.discovery_messages:
            client.publish("homeassistant/sensor/" + config.mqtt_topic_prefix + "/" + hostname + "_memory/config",
                           build_discovery_payload('memory'), qos=0)
            time.sleep(config.sleep_time)
        client.publish(config.mqtt_topic_prefix + "/" + hostname + "/memory", memory, qos=1)
        time.sleep(config.sleep_time)
    if config.sys_clock_speed:
        if config.discovery_messages:
            client.publish(
                "homeassistant/sensor/" + config.mqtt_topic_prefix + "/" + hostname + "_sys_clock_speed/config",
                build_discovery_payload('sys_clock_speed'), qos=0)
            time.sleep(config.sleep_time)
        client.publish(config.mqtt_topic_prefix + "/" + hostname + "/sys_clock_speed", sys_clock_speed, qos=1)
        time.sleep(config.sleep_time)
    if config.uptime:
        if config.discovery_messages:
            client.publish("homeassistant/sensor/" + config.mqtt_topic_prefix + "/" + hostname + "_uptime_days/config",
                           build_discovery_payload('uptime_days'), qos=0)
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
