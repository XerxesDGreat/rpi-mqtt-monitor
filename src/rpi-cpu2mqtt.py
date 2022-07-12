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
import paho.mqtt.client as paho
import socket
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
    "disk_usage": MetricConfig("mdi:harddisk", "Disk Usage", "%", config.disk_usage, m.check_disk_usage),
    "voltage": MetricConfig("mdi:sine-wave", "CPU Voltage", "V", config.voltage, m.check_voltage),
    "sys_clock_speed": MetricConfig("mdi:speedometer", "CPU Clock Speed", "MHz", config.sys_clock_speed, m.check_sys_clock_speed),
    "swap": MetricConfig("mdi:harddisk", "Disk Swap", "%", config.swap, m.check_swap),
    "memory": MetricConfig("mdi:memory", "Memory Usage", "%", config.memory, m.check_memory),
    "uptime_days": MetricConfig("mdi:timer", "Uptime", "days", config.uptime_days, m.check_uptime),
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


def build_discovery_topic(metric_name):
    return f'homeassistant/sensor/{config.mqtt_topic_prefix}/{hostname}_{metric_name}/config'


def build_value_topic(metric_name):
    return f'{config.mqtt_topic_prefix}/{hostname}/{metric_name}'


def publish_then_sleep(client, topic, payload, qos):
    client.publish(topic, payload, qos=qos)
    time.sleep(config.sleep_time)


def publish_discovery_for_metric(client, metric_name):
    if not config.discovery_messages:
        return
    publish_then_sleep(client, build_discovery_topic(metric_name), build_discovery_payload(metric_name), 0)


def publish_metric_value(client, metric_name, value):
    publish_then_sleep(client, build_value_topic(metric_name), value, 1)


def publish_to_mqtt(client, metric_values_dict):
    for metric_name, value in metric_values_dict.items():
        config = metrics.get(metric_name)
        if config is not None and config.should_measure:
            publish_discovery_for_metric(client, metric_name)
            publish_metric_value(client, metric_name, value)
            

def bulk_publish_to_mqtt(client, metric_values_dict):
    # compose the CSV message containing the measured values
    values = ','.join([str(val) for val in metric_values_dict.values()])

    # publish monitored values to MQTT
    client.publish(config.mqtt_topic_prefix + "/" + hostname, values, qos=1)


def gather_metric_values():
    # collect the monitored values
    metric_values = {
        metric_name: config.measure_func() if config.should_measure else False
        for metric_name, config in metrics.items()
    }
    return metric_values


def report_metrics():
    # delay the execution of the script
    time.sleep(config.random_delay)

    client = paho.Client()
    client.username_pw_set(config.mqtt_user, config.mqtt_password)
    client.connect(config.mqtt_host, int(config.mqtt_port))

    metric_values = gather_metric_values()
    publish_func = bulk_publish_to_mqtt if config.group_messages else publish_to_mqtt
    publish_func(client, metric_values)

    client.disconnect()


if __name__ == '__main__':
    report_metrics()
