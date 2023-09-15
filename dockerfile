# docker build -t mqtt_watchdog .

FROM python:slim
LABEL Maintainer="nortecc@gmx.net"
WORKDIR /app
COPY app/mqtt_watchdog.py ./
COPY app/config.json ./
RUN pip install requests
RUN pip install paho-mqtt
CMD [ "python", "./mqtt_watchdog.py" ]
