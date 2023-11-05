#!/usr/bin/env python3

# Version 1.3c 04.11.2023
#
#

import json
import sys
import paho.mqtt.client as mqtt 
from datetime import datetime
import time
import requests                 
import logging
from threading import Thread
#import telebot


VERSION = "1.3c 04.11.2023"
client = mqtt.Client()

# main dictionary
# example:
# list[1]["topic"] = "vzlogger/chn0/agg"        -> aus config
# list[1]["name"] = "Stromzaehler Einspeisung"  -> aus config
# list[1]["expiry"] = 300                       -> aus config
# list[1]["range"]["min"] = 10                  -> aus config
# list[1]["range"]["max"] = 80                  -> aus config

# list[1]["value"] = 13.5                       -> aus on_message nur wenn key range existiert
# list[1]["last"] = "1345654789"                -> aus on_message
# list[1]["status_expiry"] = "OK"            -> aus while-Schleife
# list[1]["status_range"] = "critical"       -> aus while-Schleife

#############################################################################

# Load Configuration file and set Parameters
#
try:
    file = open('config.json','r')
except IOError:
    print("Can't open config file!")
    sys.exit(1)
else:
    with file:
        cfg = json.load(file)

LOGLEVEL =          cfg["global"]["loglevel"]
BROKER_IP =         cfg['broker']['ip']
BROKER_PORT =       cfg['broker']['port']
BROKER_TOPIC =      cfg['broker']['topic']
BROKER_USERNAME =   cfg['broker']['username']
BROKER_PASSWORD =   cfg['broker']['password']
BROKER_PROTOCOL =   cfg['broker']['protocol']
BROKER_KEEPALIVE =  cfg['broker']['keepalive']
TELEGRAM_TOKEN =    cfg['telegram']['TOKEN']
TELEGRAM_CHAT_ID =  cfg['telegram']['chat_id']
TELEGRAM_PREFIX =   cfg['telegram']['prefix']

# prefill timestamp- and status-field in dictionary 
#
list = []
t = datetime.now()
timestamp = int(round(t.timestamp()))
for i in range(len(cfg['topics'])):
    list.append(cfg['topics'][i])
    list[i]["last"] = timestamp
    if "expiry" in list[i]: 
        list[i]["status_expiry"] = "OK"
    if "range" in list[i]: 
        list[i]["status_range"] = "OK"
        list[i]["value"] = -100

############################################################################ LOGGING
# Set LOGLEVEL
def set_loglevel(LOGLEVEL):
    log_level = logging.INFO  # Deault logging level
    if LOGLEVEL == 1:
        log_level = logging.ERROR
    elif LOGLEVEL == 2:
        log_level = logging.WARN
    elif LOGLEVEL == 3:
        log_level = logging.INFO
    elif LOGLEVEL >= 4:
        log_level = logging.DEBUG
    root = logging.getLogger()
    root.setLevel(log_level)
    logging.basicConfig(level=log_level,format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d.%m.%Y %H:%M:%S')

############################################################################ TELEGRAM
# send telegram message
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={TELEGRAM_PREFIX} | {message}"
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
    # client.subscribe("watchdog") # Not yet implemented
    for i in range(len(list)):
        client.subscribe(list[i]["topic"])
        logging.info("Subscribed topic: " + (list[i]["topic"]))
    LAST_WILL = "Verbindung beendet!"
    client.publish(BROKER_TOPIC + "/status", "Online", qos=0, retain=False)
    client.will_set(BROKER_TOPIC + "/status", "OFFLINE", qos=1, retain=False)
    client.publish(BROKER_TOPIC + "/version", VERSION, qos=0, retain=False)


# if topic receives an update, the corresponding value in the dictonary should be updated to the current time and value
def on_message(client, userdata, msg):
    t = datetime.now()
    timestamp = int(round(t.timestamp()))
    for i in range(len(list)):
        if list[i]["topic"] == msg.topic :
            list[i].update(last=timestamp)
            if "range" in list[i]:
                list[i].update(value=(msg.payload))

# if broker goes offline
def on_disconnect(client, userdata, rc):
    logging.info("Disconnected from broker!")
    send_telegram("⚠️ Disconnected from broker!")


############################################################################ PROG
# update topic-state in dictionary
def set_state(topic_id,type,state):
    list[topic_id].update(type=state)
    logging.info("Updated Status of " + list[topic_id]["name"] + " to " + str(state))

# publish states to mqtt-broker
def publish_state():
    now=datetime.now()
    tstamp = now.strftime("%d.%m.%Y, %H:%M:%S")
    client.publish(BROKER_TOPIC + "/timestamp", tstamp, qos=0, retain=False)
    for i in range(len(list)):
        topic = BROKER_TOPIC + "/topics/" + list[i]["name"]
        payload = ""
        if "expiry" in list[i]:
            payload += " expiry: " + list[i]["status_expiry"]
        if "range" in list[i]:
            payload += " range: " + list[i]["status_range"] 
        client.publish(topic, payload, qos=0, retain=False)
        # OK | "Warning out of range" | "Critical out of range" | "Warning time expired" | "Critical time expired"

############################################################################ MAIN

def main():
    set_loglevel(LOGLEVEL)
    
    mqtt_thread = Thread(target=mqtt_main)
    mqtt_thread.start()
    logging.info("Starting thread ...")
    time.sleep(10)
    while True:
        t = datetime.now()
        timestamp = int(round(t.timestamp()))
        for i in range(len(list)):
            
            # Prüfung auf Zeitablauf
            if "expiry" in list[i]:
                status_expiry = list[i]["status_expiry"]
                if timestamp > int(list[i]["last"]) + int(list[i]["expiry"]):
                    match status_expiry:
                        case "OK":
                            set_state(i,"status_expiry","warning")
                        case "warning":
                            set_state(i,"status_expiry","critical")
                            send_telegram("⚠️ Updated Status of topic " + list[i]["name"] + " to expiry:CRITICAL")
                        case "critical":
                            set_state(i,"status_expiry","critical")
                        case _:
                            set_state(i,"status_expiry","warning")  
                else:
                    pass

            # Prüfung auf Zeitablauf
            if "range" in list[i]:
                status_range = list[i]["status_range"]
                value = list[i]["value"]
                min = list[i]["range"]["min"]
                max = list[i]["range"]["max"]
                if (float(value) < float(min) or float(value) > float(max)) and not float(value) == -100 :
                    match status_range:
                        case "OK":
                            set_state(i,"status_range","warning")
                        case "warning":
                            set_state(i,"status_range","critical")
                            send_telegram("⚠️ Updated Status of topic " + list[i]["name"] + " to range:CRITICAL")
                        case "critical":
                            set_state(i,"status_range","critical")
                        case _:
                            set_state(i,"status_range","warning")  
            
        publish_state() # alle Topics werden mit Ihrem Status gepublished
        time.sleep(30)


#####################################################################
# start 
if __name__ == '__main__':
    main()