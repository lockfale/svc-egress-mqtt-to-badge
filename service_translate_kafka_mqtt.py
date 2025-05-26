import json
import logging
import logging.config
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

import redis
from lockfale_connectors.lf_kafka.kafka_consumer import KafkaConsumer
from lockfale_connectors.lf_kafka.kafka_producer import KafkaProducer
from lockfale_connectors.mqtt.mqtt_publisher import MQTTPublisher

from mqtt_publish_gate import should_publish_to_mqtt
from mqtt_publish_payload import build_mqtt_payload
from redis_db_indexes import (
    redis_db_idx_cp_data,
    redis_db_idx_cp_inventory,
    redis_db_idx_last_notification_to_badge,
)

logging.config.fileConfig("log.ini")
logger = logging.getLogger("console")
logger.setLevel(logging.INFO)

redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
REDIS_CLIENT_CP_DATA: Optional[redis.Redis] = None
REDIS_CLIENT_GENERAL: Optional[redis.Redis] = None
REDIS_CLIENT_DB_INVENTORY: Optional[redis.Redis] = None

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"

SERVICES_TO_UPDATE_INVENTORY = ["svc-cp-inventory", "svc-game-store"]


def setup_redis():
    """Setup redis connections"""
    global REDIS_CLIENT_CP_DATA
    global REDIS_CLIENT_DB_INVENTORY
    global REDIS_CLIENT_GENERAL
    REDIS_CLIENT_CP_DATA = redis.Redis(host=redis_host, port=redis_port, decode_responses=True, db=redis_db_idx_cp_data)
    REDIS_CLIENT_GENERAL = redis.Redis(host=redis_host, port=redis_port, decode_responses=True, db=redis_db_idx_last_notification_to_badge)

    REDIS_CLIENT_DB_INVENTORY = redis.Redis(host=redis_host, port=redis_port, decode_responses=True, db=redis_db_idx_cp_inventory)


def shutdown_redis():
    global REDIS_CLIENT_CP_DATA
    global REDIS_CLIENT_GENERAL
    global REDIS_CLIENT_DB_INVENTORY
    if REDIS_CLIENT_CP_DATA:
        REDIS_CLIENT_CP_DATA.close()

    if REDIS_CLIENT_GENERAL:
        REDIS_CLIENT_GENERAL.close()

    if REDIS_CLIENT_DB_INVENTORY:
        REDIS_CLIENT_DB_INVENTORY.close()


def build_mqtt_topic(badge_id: str, from_service: str) -> str:
    _topic = f"cackalacky/badge/ingress/{badge_id}/cp/state/update"
    if from_service in SERVICES_TO_UPDATE_INVENTORY:
        _topic = f"cackalacky/badge/ingress/{badge_id}/cp/inventory/update"
    return _topic


def _send_state_to_badge(mqtt_pub: MQTTPublisher, msg: Dict) -> bool:
    badge_id = msg.get("badge_id")
    if not badge_id:
        # TODO => otel metric failure
        return False

    sp = should_publish_to_mqtt(REDIS_CLIENT_GENERAL, badge_id, msg.get("source_event_uuid"), bool(msg.get("force_mqtt_publish", False)))
    if not sp:
        return False

    _topic = build_mqtt_topic(badge_id, msg.get("event_source", ""))
    mqtt_payload = build_mqtt_payload(REDIS_CLIENT_CP_DATA, REDIS_CLIENT_DB_INVENTORY, badge_id, msg)
    if not mqtt_payload:
        return False

    mqtt_payload["ts"] = datetime.now(timezone.utc).timestamp()
    try:
        _ = mqtt_pub.publish(_topic, json.dumps(mqtt_payload))
    except Exception as e:
        logger.error(f"Error publishing message: {str(e)}")
        logger.error(f"Topic: {_topic}")
        logger.error(f"Raw message: {mqtt_payload}")
        logger.error(e)
        return False

    return True


def main():
    logger.info(f"Connecting to Kafka broker at {os.getenv('KAFKA_BROKERS_SVC')}")

    mqtt_host = os.getenv("MQTT_HOST")
    mqtt_port = int(os.getenv("MQTT_PORT"))
    if mqtt_host is None or mqtt_port is None:
        logger.error("MQTT_HOST or MQTT_PORT is not set")
        return

    logger.info("Waiting for messages... (Press Ctrl+C to exit)")
    topic = "egress-mqtt-to-badge"
    try:
        logger.info([topic])
        consumer = KafkaConsumer(topics=[topic], kafka_broker=os.getenv("KAFKA_BROKERS_SVC"), group_id="kafka-mqtt-consumer-group")
    except Exception as e:
        logger.error(f"Error connecting to resources: {str(e)}")
        exit(1)

    try:
        producer = KafkaProducer(kafka_broker=os.getenv("KAFKA_BROKERS_SVC"))
    except Exception as e:
        logger.error(f"Error connecting to resources: {str(e)}")
        exit(1)

    try:
        setup_redis()
    except Exception as e:
        logger.error(f"Error connecting to resources: {str(e)}")
        exit(1)

    mqtt_pub = MQTTPublisher(f"publisher-badge-ingress-{datetime.now().strftime("%Y%d%mT%H%M%SZ")}-{str(uuid.uuid4())}")
    mqtt_pub.connect(keep_alive=20)
    mqtt_pub.client.loop_start()

    try:
        for message in consumer.consumer:
            start_ts = datetime.now(timezone.utc)
            result = _send_state_to_badge(mqtt_pub, message.value)
            end_ts = datetime.now(timezone.utc)
            duration_ms = (end_ts - start_ts).total_seconds() * 1000
            logger.info(f"Processed message in {duration_ms} ms")
            if result:
                producer.send_message(source_topic=topic, destination_topic="pgsql-transactions", message=message.value)
    except KeyboardInterrupt:
        logger.info("\nExiting consumer")
    finally:
        mqtt_pub.disconnect()
        consumer.disconnect()


if __name__ == "__main__":
    main()
