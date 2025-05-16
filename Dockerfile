FROM python:3.12-bullseye
RUN apt update && apt-get install vim -y && apt-get install lsof -y

ENV POETRY_VERSION=2.1.1
RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="/root/.local/bin:$PATH"

ARG CODEARTIFACT_TOKEN
ARG AWS_REGION=us-east-1
RUN poetry config repositories.lockfale https://lockfale-059039070213.d.codeartifact.us-east-1.amazonaws.com/pypi/lockfale/simple/ \
    && poetry config http-basic.lockfale aws ${CODEARTIFACT_TOKEN}

WORKDIR /app

COPY pyproject.toml poetry.lock log.ini /app/
RUN poetry install --no-root --no-interaction --no-ansi

COPY mqtt_to_kafka /app/mqtt_to_kafka
COPY service_translate_kafka_mqtt.py service_translate_kafka_mqtt.py /app/

