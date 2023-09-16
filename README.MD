# mqtt-watchdog

## Funktionsweise
Der Watchdog überwacht ein oder mehrere Topics eines MQTT-Brokers. Wenn eine bestimmte Zeit überschritten wird und kein Statusupdate des Topics erfolgt ist, wird per Telegram eine Meldung ausgegeben.

## Konfiguration
Die Konfiguration erfolgt in der ```config.yaml``` 
#### Parameter
Bereich `global`
* `loglevel` Derzeit nicht implementiert

Bereich `broker`
* `ip` Die IP des MQTT-Brokers, z.B. 10.0.0.12
* `port` Der Port des MQTT-Brokers, normalerweise 1883
* `topic` Der Topic unter dem mqtt-watchdog Meldungen an den Broker sendet
* `username` und `password` Zugangsdaten für den Zugriff auf den MQTT-Broker, alternativ leer lassen
* `protocol` MQTT-Protocol
* `keepalive` 

Bereich `telegram`
* `TOKEN` Token für den Zugriff auf Telegram
* `chat_id` ID des Chats auf dem die Meldungen ausgegeben werden

Bereich `topics`
Für jeden zu überwachenden Topic werden folgende Angaben benötigt
* `topic` Der Name des zu überwachenden Topics wie er im Broker dargestellt wird
* `name` Ein Alias bzw. die Kurzschreibweise 
* `expiry` Zeitraum innerhalb dessen spätestens eine Statusänderung des Topics erfolgen muss

## Programmteil
Das eigentliche Programm ist in der ```mqtt_watchdog.py```