# Service Broker Translation

Broker translation from MQTT -> Kafka and vice versa

## Build

### Pre-req windows

py3.12
poetry
```bash
pipx install poetry
poetry --version
```

https://scoop.sh/
https://pipx.pypa.io/stable/installation/

### Local Run - Docker

Docker compose w/doppler to inject secrets / os vars

```bash
# First get the token
export CODEARTIFACT_TOKEN=$(aws codeartifact get-authorization-token --domain ... --domain-owner ... --query authorizationToken --output text)

# Build the image
doppler run -- docker compose -f docker-compose.services.yaml build --build-arg CODEARTIFACT_TOKEN=$env:CODEARTIFACT_TOKEN

# Run with infrastructure (Kafka, Redis, etc.)
doppler run -- docker compose -f docker-compose.infrastructure.yaml -f docker-compose.services.yaml up -d
doppler run -- docker compose -f docker-compose.services.yaml up -d
```

# Maintenance

```bash
poetry run isort .
poetry run black .
```

# TODO
 - taskfile
 - docker commands for local
