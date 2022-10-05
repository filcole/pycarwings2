#!/usr/bin/env python

import pycarwings2
import time
from configparser import ConfigParser
import logging
import sys
import time
import signal

import paho.mqtt.client as mqtt

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

parser = ConfigParser()
candidates = ['config.ini', 'my_config.ini']
found = parser.read(candidates)

username = parser.get('get-leaf-info', 'username')
password = parser.get('get-leaf-info', 'password')
mqttuser = parser.get('mqtt', 'user')
mqttpass = parser.get('mqtt', 'pass')
mqtthost = parser.get('mqtt', 'host')
region = parser.get('get-leaf-info', 'region')


def publish_info(info, client):
    client.publish("leaf/remaining_km", info.battery_remaining_amount, retain=True)
    client.publish("leaf/is_charging", info.is_charging, retain=True)
    client.publish("leaf/is_quick_charging", info.is_quick_charging, retain=True)
    client.publish("leaf/is_connected", info.is_connected, retain=True)
    client.publish("leaf/is_connected_to_quick_charger", info.is_connected_to_quick_charger, retain=True)
    client.publish("leaf/battery_percent", info.battery_percent, retain=True)


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

#     client.subscribe("")

def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))


run = True
def handler(signum, frame):
    global run
    print("Handler got", signum)
    run = False


# Main program
signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGABRT, handler)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(mqttuser, mqttpass)
client.connect(mqtthost, 1883, 60)
client.loop_start()

logging.debug("login = %s, password = %s, region = %s" % (username, password, region))

print("Prepare Session")
s = pycarwings2.Session(username, password, region)
print("Login...")
leaf = s.get_leaf()

dt = 3600
t =  time.time() + 1
key = None
tkey = None
retries = 6
errstr = ''
while run:
    if time.time() >= t:
        print("requesting ...", flush=True)
        s.connect()
        leaf = s.get_leaf()
        t = time.time() + dt
        leaf_info = leaf.get_latest_battery_status()
        publish_info(leaf_info, client)
        key = leaf.request_update()
        tkey = t + 30

    if tkey is not None and time.time() > tkey:
        status = leaf.get_status_from_update(key)
        if status is None:
            print("waiting ...", flush=True)
            tkey = time.time() + 15
            retries = retries - 1
            if retries == 0:
                errstr = 'Status could not be retrieved.'
                break
        else:
            key = None
            tkey = None
            retries = 6
            leaf_info = leaf.get_latest_battery_status()
            publish_info(leaf_info, client)
            del leaf

    if (not run):
        break

    time.sleep(1)

client.loop_stop()
sys.exit(errstr)
