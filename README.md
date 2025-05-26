# Service: Egress Kafka to MQTT to Badge

A service that handles message translation and routing from Kafka to MQTT to badges.

## Service Overview

This service acts as a broker between Kafka and MQTT messaging systems, specifically:

- **Kafka to MQTT**: Consumes messages from Kafka topic `egress-mqtt-to-badge` and publishes them to MQTT topics for badge communication
- **Main Functions**:
  - Translates Kafka messages to MQTT format
  - Handles rate limiting for badge communications
  - Processes different event types (state updates, inventory updates, store syncs)
  - Maintains state in Redis for tracking message history and cooldowns

## Build

### Pre-requisites (Windows)

- Python 3.12
- Poetry for dependency management
```bash
pipx install poetry
poetry --version
```

Installation tools:
- https://scoop.sh/ - Windows package manager
- https://pipx.pypa.io/stable/installation/ - Tool to install Python applications

### Local Run - Docker

Docker compose with Doppler to inject secrets and environment variables:

```bash
# Build the image
doppler run -- docker compose -f docker-compose.services.yaml build

# Run with infrastructure (Kafka, Redis, etc.)
doppler run -- docker compose -f docker-compose.infrastructure.yaml -f docker-compose.services.yaml up -d

# Run just the service (if infrastructure is already running)
doppler run -- docker compose -f docker-compose.services.yaml up -d
```

## Deployment

The service is deployed to Kubernetes using ArgoCD and CircleCI. The deployment process:
1. CircleCI builds the Docker image and pushes it to ECR
2. CircleCI updates the Kubernetes manifests with the new image tag
3. ArgoCD detects the changes and deploys the new version

## Maintenance

Code formatting:
```bash
poetry run isort .
poetry run black .
```

## TODO
- Add Taskfile for common operations
- Improve local development Docker commands
- Add monitoring and alerting
- Add unit tests
