import json
import logging
import logging.config
import os
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Optional

import redis
from lockfale_connectors.lf_kafka.kafka_consumer import KafkaConsumer
from lockfale_connectors.lf_kafka.kafka_producer import KafkaProducer
from lockfale_connectors.mqtt.mqtt_publisher import MQTTPublisher

from mqtt_to_kafka.datatypes import transform_cyberpartner_dict

logging.config.fileConfig("log.ini")
logger = logging.getLogger("console")
logger.setLevel(logging.INFO)

redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
REDIS_CLIENT_DB0: Optional[redis.Redis] = None
REDIS_CLIENT_DB1: Optional[redis.Redis] = None
REDIS_CLIENT_DB_INVENTORY: Optional[redis.Redis] = None
redis_db_idx_cp_inventory = int(os.getenv("REDIS_DB_IDX_CP_INVENTORY", 5))

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"

SERVICES_TO_UPDATE_INVENTORY = [
    "svc-cp-inventory",
    "svc-game-store"
]

def setup_redis():
    """Setup redis connections"""
    global REDIS_CLIENT_DB0
    global REDIS_CLIENT_DB1
    global REDIS_CLIENT_DB_INVENTORY
    REDIS_CLIENT_DB0 = redis.Redis(
        host=redis_host,
        port=redis_port,
        decode_responses=True,  # optional, strings not bytes
    )
    REDIS_CLIENT_DB1 = redis.Redis(
        host=redis_host, port=redis_port, decode_responses=True, db=int(os.getenv("REDIS_DB_IDX_LAST_PUB_TO_BADGE", 1))  # optional, strings not bytes
    )

    REDIS_CLIENT_DB_INVENTORY = redis.Redis(
        host=redis_host, port=redis_port, decode_responses=True, db=redis_db_idx_cp_inventory
    )


def shutdown_redis():
    global REDIS_CLIENT_DB0
    global REDIS_CLIENT_DB1
    global REDIS_CLIENT_DB_INVENTORY
    if REDIS_CLIENT_DB0:
        REDIS_CLIENT_DB0.close()

    if REDIS_CLIENT_DB1:
        REDIS_CLIENT_DB1.close()

    if REDIS_CLIENT_DB_INVENTORY:
        REDIS_CLIENT_DB_INVENTORY.close()


def should_publish_to_mqtt(badge_id: str, source_event_uuid: str = None, force_mqtt_publish: bool = False) -> bool:
    if force_mqtt_publish:
        return True

    if source_event_uuid:
        REDIS_CLIENT_DB1.select(int(os.getenv("REDIS_DB_IDX_LAST_SOURCE_UUID_BADGE", 3)))
        last_known_badge_source_event = REDIS_CLIENT_DB1.get(badge_id)
        logger.info(f"Last known badge source event: {last_known_badge_source_event} | {badge_id} | {source_event_uuid}")
        if last_known_badge_source_event == source_event_uuid:
            logger.info(f"Source event was initiated by badge. Publishing.")
            return True

    ttl_seconds = 60

    # Get last publish time from Redis
    REDIS_CLIENT_DB1.select(int(os.getenv("REDIS_DB_IDX_LAST_SOURCE_UUID_BADGE", 1)))
    last_publish_time = REDIS_CLIENT_DB1.get(badge_id)
    logger.info(f"last_publish_time: {last_publish_time} | {badge_id}")
    if last_publish_time is None:
        # First publish for this badge_id
        REDIS_CLIENT_DB1.setex(badge_id, ttl_seconds, 1)
        return True
    return False


def build_mqtt_topic(badge_id: str, from_service: str) -> str:
    _topic = f"cackalacky/badge/ingress/{badge_id}/cp/state/update"
    if from_service in SERVICES_TO_UPDATE_INVENTORY:
        _topic = f"cackalacky/badge/ingress/{badge_id}/cp/inventory/update"
    return _topic


def build_mqtt_payload(badge_id: str, msg: Dict) -> Optional[Dict]:
    from_service = msg.get("event_source", "")
    event_type = msg.get("event_type", "")
    event_subtype = msg.get("event_subtype", "")

    if event_type == "store.sync":
        _obj = msg.get("store")
        if isinstance(_obj, str):
            _obj = json.loads(_obj)
        return _obj

    if event_subtype == "get.state":
        cp_obj = msg.get("cp_obj")
        if not cp_obj:
            logger.error(f"Did not pass cyberpartner object.")
            return None

        if isinstance(cp_obj, str):
            cp_obj = json.loads(cp_obj)

        try:
            cp = transform_cyberpartner_dict(cp_obj)
            return cp.mqtt_payload()
        except AttributeError as ae:
            logger.error(f"Error transforming cyberpartner: {str(ae)}")
            logger.error(f"CP obj: {cp_obj}")
            return None

    if from_service in SERVICES_TO_UPDATE_INVENTORY:
        inventory = REDIS_CLIENT_DB_INVENTORY.get(badge_id)
        if not inventory:
            logger.error(f"Could not find CP inventory with badge id: {badge_id}")
            return None
        if isinstance(inventory, str):
            inventory = json.loads(inventory)
        return inventory
    else:
        cp_obj = msg.get("cp_obj")
        if not cp_obj:
            cp_obj = REDIS_CLIENT_DB0.get(badge_id)
            if not cp_obj:
                logger.error(f"Could not find CP with badge id: {badge_id}")
                return None

        if isinstance(cp_obj, str):
            cp_obj = json.loads(cp_obj)

        try:
            cp = transform_cyberpartner_dict(cp_obj)
            return cp.mqtt_payload()
        except AttributeError as ae:
            logger.error(f"Error transforming cyberpartner: {str(ae)}")
            logger.error(f"CP obj: {cp_obj}")
            return None


def _send_state_to_badge(mqtt_pub: MQTTPublisher, msg: Dict) -> bool:
    badge_id = msg.get("badge_id")
    if not badge_id:
        # TODO => otel metric failure
        return False

    sp = should_publish_to_mqtt(badge_id, msg.get("source_event_uuid"), bool(msg.get("force_mqtt_publish", False)))
    if not sp:
        return False

    _topic = build_mqtt_topic(badge_id, msg.get("event_source", ""))
    mqtt_payload = build_mqtt_payload(badge_id, msg)
    logger.info(mqtt_payload)
    if not mqtt_payload:
        return False

    mqtt_payload["ts"] = datetime.now(timezone.utc).timestamp()
    try:
        logger.info(mqtt_payload)
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
        consumer = KafkaConsumer(topics=[topic],
            kafka_broker=os.getenv("KAFKA_BROKERS_SVC"), group_id="kafka-mqtt-consumer-group")
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
                producer.send_message(
                    source_topic=topic,
                    destination_topic="pgsql-transactions",
                    message=message.value
                )
    except KeyboardInterrupt:
        logger.info("\nExiting consumer")
    finally:
        mqtt_pub.disconnect()
        consumer.disconnect()


if __name__ == "__main__":
    """force"""
    main()
