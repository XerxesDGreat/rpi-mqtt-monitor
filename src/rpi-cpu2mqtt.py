# -*- coding: utf-8 -*-
# Python script (runs on 2 and 3) to check cpu load, cpu temperature and free space etc.
# on a Raspberry Pi or Ubuntu computer and publish the data to a MQTT server.
# RUN pip install paho-mqtt
# RUN sudo apt-get install python-pip

from __future__ import division
from audioop import mul
from collections import namedtuple
from logging.config import dictConfig
from tkinter.tix import MAX
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

# mqtt client-related stuff
_mqtt_client = paho.Client()
_is_mqtt_connected = False
_num_connect_attempts = 0
MAX_CONNECT_ATTEMPTS = 6
STARTING_DELAY_TIME = 1
_current_delay_time = STARTING_DELAY_TIME

# loop controls
_should_run = True
_last_discovery_publish = 0

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


def publish_then_sleep(topic, payload, qos):
    _mqtt_client.publish(topic, payload, qos=qos, retain=True)
    time.sleep(config.sleep_time)


def publish_discovery_for_metric(metric_name):
    if not config.discovery_messages:
        return
    publish_then_sleep(build_discovery_topic(metric_name), build_discovery_payload(metric_name), 0)


def publish_discovery():
    global _last_discovery_publish
    if not config.discovery_messages:
        return
    curtime = int(time.time())
    if curtime <= (_last_discovery_publish + config.discovery_message_interval_seconds):
        return
    for metric_name, metric_config in metrics.items():
        if not metric_config.should_measure:
            continue
        publish_discovery_for_metric(metric_name)
    _last_discovery_publish = curtime


def publish_metric_value(metric_name, value):
    publish_then_sleep(build_value_topic(metric_name), value, 1)


def publish_to_mqtt(metric_values_dict):
    for metric_name, value in metric_values_dict.items():
        config = metrics.get(metric_name)
        if config is not None and config.should_measure:
            publish_metric_value(metric_name, value)


def bulk_publish_to_mqtt(metric_values_dict):
    # compose the CSV message containing the measured values
    values = ','.join([str(val) for val in metric_values_dict.values()])

    # publish monitored values to MQTT
    _mqtt_client.publish(config.mqtt_topic_prefix + "/" + hostname, values, qos=1)


def gather_metric_values():
    # collect the monitored values
    metric_values = {
        metric_name: config.measure_func() if config.should_measure else False
        for metric_name, config in metrics.items()
    }
    return metric_values


def loop():
    publish_discovery()
    metric_values = gather_metric_values()
    publish_func = bulk_publish_to_mqtt if config.group_messages else publish_to_mqtt
    publish_func(metric_values)


def on_connect(client, userdata, flags, rc):
    global _is_mqtt_connected, _num_connect_attempts, _current_delay_time
    logging.info("client is connected with rc [%s]", rc)
    _is_mqtt_connected = True
    _num_connect_attempts = 0
    _current_delay_time = STARTING_DELAY_TIME


def on_disconnect(client, userdata, rc):
    global _is_mqtt_connected
    logging.info("client is disconnected with rc [%s]",  rc)
    _is_mqtt_connected = False
    disconnect()


def connect():
    global _mqtt_client
    _mqtt_client.username_pw_set(config.mqtt_user, config.mqtt_password)
    _mqtt_client.on_connect = on_connect
    _mqtt_client.on_disconnect = on_disconnect
    _mqtt_client.connect(config.mqtt_host, int(config.mqtt_port))
    logging.info("waiting for a connection")
    wait_for_connection()
    _mqtt_client.loop_start


def wait_for_connection():
    global _num_connect_attempts, _current_delay_time
    while not _is_mqtt_connected:
        if _num_connect_attempts >= config.max_connect_attempts:
            raise Exception("unable to connect after %s attempts" % _num_connect_attempts)
        multiplier = 1
        if _num_connect_attempts >= config.connect_attempt_backoff_threshold:
            multiplier = 2
        _current_delay_time = _current_delay_time * multiplier
        logging.info("waiting %s seconds to try again...", _current_delay_time)
        time.sleep(_current_delay_time)


def disconnect():
    global _mqtt_client
    _mqtt_client.disconnect()
    _mqtt_client.loop_stop()


def start_loop():
    connect()
    time.sleep(config.random_delay) # this will help stagger updates from multiple devices
    while _should_run:
        loop()
        time.sleep(config.loop_time_seconds)
    disconnect()


if __name__ == '__main__':
    start_loop()
