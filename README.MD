# mqtt-watchdog

## Funktionsweise
Der Watchdog überwacht ein oder mehrere Topics eines MQTT-Brokers. Wenn eine bestimmte Zeit überschritten wird und kein Statusupdate des Topics erfolgt ist, wird per Telegram eine Meldung ausgegeben.

## Konfiguration
Die Konfiguration erfolgt in der ```config.yaml``` 

## Programmteil
Das eigentliche Programm ist in der ```mqtt_watchdog.py```