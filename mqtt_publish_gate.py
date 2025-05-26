import logging
import logging.config
from typing import Optional

import redis

from redis_db_indexes import (
    redis_db_idx_last_notification_to_badge,
    redis_db_idx_last_source_uuid_badge,
)

logger = logging.getLogger("console")


def should_publish_to_mqtt(redis_client: redis.Redis, badge_id: str, source_event_uuid: str = None, force_mqtt_publish: bool = False) -> bool:
    """Determines whether a message should be published to MQTT for a badge.

    Parameters
    ----------
    redis_client: redis.Redis
    badge_id: str
    source_event_uuid: Optional[str]
    force_mqtt_publish: Optional[bool]

    Returns
    -------
    bool
    """
    if force_mqtt_publish:
        return True

    if source_event_uuid and _is_badge_initiated_event(redis_client, badge_id, source_event_uuid):
        return True

    return _is_first_publish_or_cooldown_elapsed(redis_client, badge_id)


def _is_badge_initiated_event(redis_client: redis.Redis, badge_id: str, source_event_uuid: str) -> bool:
    """Check if the event was initiated by the badge itself.

    Parameters
    ----------
    redis_client: redis.Redis
    badge_id: str
    source_event_uuid: str

    Returns
    -------
    bool
    """
    redis_client.select(redis_db_idx_last_source_uuid_badge)
    last_known_badge_source_event = redis_client.get(badge_id)

    logger.info(f"Last known badge source event: {last_known_badge_source_event} | {badge_id} | {source_event_uuid}")

    if last_known_badge_source_event == source_event_uuid:
        logger.info("Source event was initiated by badge. Publishing.")
        return True
    return False


def _is_first_publish_or_cooldown_elapsed(redis_client: redis.Redis, badge_id: str) -> bool:
    """Check if this is the first publish for this badge or if cooldown period has elapsed.

    Parameters
    ----------
    redis_client: redis.Redis
    badge_id: str

    Returns
    -------
    bool
    """
    ttl_seconds = 60

    # Get last publish time from Redis
    redis_client.select(redis_db_idx_last_notification_to_badge)
    last_publish_time = redis_client.get(badge_id)
    logger.info(f"last_publish_time: {last_publish_time} | {badge_id}")

    if last_publish_time is None:
        redis_client.setex(badge_id, ttl_seconds, 1)
        return True

    return False
