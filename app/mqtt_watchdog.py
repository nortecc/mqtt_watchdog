#!/usr/bin/env python3

# Version 1.1 14.07.2023 15:45 -> update
#
#
# todos:
# statusabfrage in Telegram

import json
import paho.mqtt.client as mqtt 
from datetime import datetime
import time
import requests                 
import logging
from threading import Thread

VERSION = "1.1 14.07.2023 15:45"

# main dictionary
# example:
# list[1]["topic"] = "vzlogger/chn0/agg"
# list[1]["name"] = "Stromzaehler Einspeisung"
# list[1]["expiry"] = 300
# list[1]["last"] = "1345654789"
# list[1]["status"] = "OK"
list = []

logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d.%m.%Y %H:%M:%S')

# read config.json
with open('config.json','r') as file:
    aList = json.load(file)
BROKER_IP =         aList['broker']['ip']
BROKER_PORT =       aList['broker']['port']
BROKER_TOPIC =      aList['broker']['topic']
TELEGRAM_TOKEN =    aList['telegram']['TOKEN']
TELEGRAM_CHAT_ID =  aList['telegram']['chat_id']

# prefill timestamp-field in dictionary 
t = datetime.now()
timestamp = int(round(t.timestamp()))
for i in range(len(aList['topics'])):
  list.append(aList['topics'][i])
  list[i]["last"] = timestamp
  list[i]["status"] = "OK"

client = mqtt.Client()

############################################################################ TELEGRAM
# send telegram message
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={message}"
    requests.get(url).json()

############################################################################ MQTT
# initialize mqtt
def mqtt_main():
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.connect(BROKER_IP, BROKER_PORT, 60)
    client.loop_start()
    time.sleep(10)

# callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    result_code = {0:"Connection successful", 
               1:"Connection refused - incorrect protocol version", 
               2:"Connection refused - invalid client identifier",
               3:"Connection refused - server unavailable",
               4:"Connection refused - bad username or password",
               5:"Connection refused - not authorised"}

    logging.info("Connected with result: "+result_code[rc])
    send_telegram("✅ Connected with result: "+result_code[rc]+" and version "+VERSION)
    client.subscribe("$SYS/broker/uptime") # checks whether the broker is online
    logging.info("Subscribed topic: $SYS/broker/uptime")
    client.subscribe("watchdog")
    for i in range(len(list)):
        client.subscribe(list[i]["topic"])
        logging.info("Subscribed topic: " + (list[i]["topic"]))

# if topic receives an update, the corresponding value in the dictonary should be updated to the current time
def on_message(client, userdata, msg):
    t = datetime.now()
    timestamp = int(round(t.timestamp()))
    for i in range(len(list)):
        if list[i]["topic"] == msg.topic :
           list[i].update(last=timestamp)

# if broker goes offline
def on_disconnect(client, userdata, rc):
    logging.info("Disconnected from broker!")
    send_telegram("⚠️ Disconnected from broker!")

############################################################################ PROG
# send status table to Telegram -> not yet implemented
def status_table(client, userdata, message):
    now=datetime.now()
    tstamp = now.strftime("%d.%m.%Y, %H:%M:%S")
    message = "Statusmeldung von " + tstamp + ": \n"
    for i in range(len(aList['topics'])):
        message += list[i]["name"] + " -> " + list[i]["status"] + "\n"
    send_telegram(message)

# update topic-state in dictionary
def set_state(topic_id,state):
    list[topic_id].update(status=state)
    logging.info("Updated Status of " + list[topic_id]["name"] + " to " + str(state))

# publish states to mqtt-broker
def publish_state():
    now=datetime.now()
    tstamp = now.strftime("%d.%m.%Y, %H:%M:%S")
    client.publish(BROKER_TOPIC + "/timestamp", tstamp, qos=0, retain=False)
    for i in range(len(list)):
        topic = BROKER_TOPIC + "/topics/" + list[i]["name"]
        payload = list[i]["status"]
        client.publish(topic, payload, qos=0, retain=False)

############################################################################

# initializing threads
# telegram_thread = Thread(target=telegram_main) -> not yet implemented
# telegram_thread.start()
mqtt_thread = Thread(target=mqtt_main)
mqtt_thread.start()

while True:
    t = datetime.now()
    timestamp = int(round(t.timestamp()))
    for i in range(len(list)):
        expiry = list[i]["expiry"] 
        last = list[i]["last"]
        status = list[i]["status"]
        if timestamp > int(last) + int(expiry) :
            match status:
                case "OK":
                    set_state(i,"warning")
                case "warning":
                    set_state(i,"critical")
                    send_telegram("⚠️ Updated Status of topic " + list[i]["name"] + " to CRITICAL")
                case "critical":
                    set_state(i,"critical")
                case _:
                    set_state(i,"warning")
        else:
            match status:
                case "OK":
                    set_state(i,"OK")
                case "warning":
                    set_state(i,"OK")
                case "critical":
                    set_state(i,"OK")
                    send_telegram("✅ Reset Status of topic " + list[i]["name"] + " from critical back to OK")
                case _:
                    set_state(i,"warning")
    
    publish_state()
    time.sleep(30)