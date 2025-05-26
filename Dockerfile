FROM python:3.12-bullseye
RUN apt update && apt-get install vim -y && apt-get install lsof -y

ENV POETRY_VERSION=2.1.1
RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

COPY pyproject.toml poetry.lock log.ini /app/
RUN poetry install --no-root --no-interaction --no-ansi

COPY redis_db_indexes.py /app/
COPY metrics /app/metrics
COPY mqtt_to_kafka /app/mqtt_to_kafka
COPY service_translate_kafka_mqtt.py mqtt_publish_gate.py mqtt_publish_payload.py /app/
