# Raspberry Pi MQTT monitor
Python script to check the cpu load, cpu temperature, free space, used memory, swap usage, voltage and system clock speed
on a Raspberry Pi or any computer running Ubuntu and publish this data to a MQTT broker.

This fork of [the original script](https://github.com/hjelev/rpi-mqtt-monitor) adds a looping code structure which allows for
long-running processes, albeit simplistically. The original script relied on CRON which only allows for granularity no lower than
one minute. This modification allows for more frequent updates of the sensors, but is still using a blocking interface so actual
update frequency is limited by real-world restrictions e.g. duration of time to publish messages, duration of time to gather sensor
information, etc. Ideal frequency in this case is 6 times per minute, or gathering sensor data every 10 seconds.

# Configuration
Basic configuration from the original is unchanged. This fork adds the following configuration values:
| config name | purpose |
| ----------- | ------- | 
| dry_run     | when set to True, metrics collection methods return a pre-determined value. Good for development |
| loop_time_seconds | how long in seconds to delay before starting the next loop iteration |
| discovery_message_interval_seconds | how long in seconds to delay before sending another batch of discovery messages | 

# Notes about Discovery
Home Assistant has a mechanism for automatically creating new sensors based on a strictly-formatted set of MQTT topics; this is
called [MQTT Discovery](https://www.home-assistant.io/docs/mqtt/discovery/). By design, discovery messages are read once and the
sensors are built up; there is no need for updating discovery messages. However, if the discovery topics are cleared, the sensors
are removed from Home Assistant automatically. Thus, this script will send discovery messages on an interval in case the MQTT broker
is reset or the topics are cleared; this way, it is unnecessary to restart the individual services.

# Installation

## Automatic
```bash
bash <(curl -s https://raw.githubusercontent.com/hjelev/rpi-mqtt-monitor/master/remote_install.sh)
```

## Manual

Install pip if you don't have it:
```bash
# install pip
$ sudo apt install python-pip

# install the requirements
$ pip install -r requirements.txt

# clone the repo
$ git clone https://github.com/xerxesdgreat/rpi-mqtt-monitor.git

# copy files
$ cd rpi-mqtt-monitor
$ cp src/rpi-cpu2mqtt.py /dir/of/choice/rpi-cpu2mqtt.py
$ cp src/config.py.example /dir/of/choice/config.py
```

# Todo
* retry connection
* failed connection backoff
