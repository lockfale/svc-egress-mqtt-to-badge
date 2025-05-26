import json
import logging.config
from typing import Any, Dict

import redis

from datatypes import transform_cyberpartner_dict

logger = logging.getLogger("console")

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"

SERVICES_TO_UPDATE_INVENTORY = ["svc-cp-inventory", "svc-game-store"]


def build_mqtt_payload(redis_client_cp_data: redis.Redis, redis_client_inventory: redis.Redis, badge_id: str, msg: Dict) -> dict | None:
    """Build the MQTT payload based on message type and source service.

    Parameters
    ----------
    redis_client_cp_data: redis.Redis
    redis_client_inventory: redis.Redis
    badge_id: str
    msg: Dict

    Returns
    -------
    dict | None
    """
    from_service = msg.get("event_source", "")
    event_type = msg.get("event_type", "")
    event_subtype = msg.get("event_subtype", "")

    # Handle store sync events
    if event_type == "store.sync":
        return _handle_store_sync(msg)

    # Handle state request events
    if event_subtype == "get.state":
        return _handle_get_state(msg)

    # Handle inventory update events
    if from_service in SERVICES_TO_UPDATE_INVENTORY:
        return _handle_inventory_update(redis_client_inventory, badge_id)

    # Handle default case - cyberpartner state update
    return _handle_cyberpartner_update(redis_client_cp_data, badge_id, msg)


def _handle_store_sync(msg: Dict) -> dict:
    """Process store sync event payload.

    Parameters
    ----------
    msg: Dict

    Returns
    -------
    Dict
    """
    _obj = msg.get("store")
    if isinstance(_obj, str):
        _obj = json.loads(_obj)
    return _obj


def _handle_get_state(msg: Dict) -> dict | None:
    """Process get.state event payload.

    Parameters
    ----------
    msg: Dict

    Returns
    -------
    dict | None
    """
    cp_obj = msg.get("cp_obj")
    if not cp_obj:
        logger.error("Did not pass cyberpartner object.")
        return None

    return _transform_cyberpartner_object(cp_obj)


def _handle_inventory_update(redis_client: redis.Redis, badge_id: str) -> dict | None:
    """Process inventory update event payload.

    Parameters
    ----------
    badge_id: str

    Returns
    -------
    dict | None
    """
    inventory = redis_client.get(badge_id)
    if not inventory:
        logger.error(f"Could not find CP inventory with badge id: {badge_id}")
        return None

    if isinstance(inventory, str):
        inventory = json.loads(inventory)
    return inventory


def _handle_cyberpartner_update(redis_client: redis.Redis, badge_id: str, msg: Dict[str, Any]) -> dict | None:
    """Process cyberpartner update event payload.

    Parameters
    ----------
    badge_id: str
    msg: Dict

    Returns
    -------
    dict
    """
    cp_obj = msg.get("cp_obj")
    if not cp_obj:
        cp_obj = redis_client.get(badge_id)
        if not cp_obj:
            logger.error(f"Could not find CP with badge id: {badge_id}")
            return {}

    return _transform_cyberpartner_object(cp_obj)


def _transform_cyberpartner_object(cp_obj: Dict[str, Any]) -> dict | None:
    """Transform cyberpartner object to MQTT payload format.

    Parameters
    ----------
    cp_obj: Union[Dict, str]

    Returns
    -------
    dict | None
    """
    if isinstance(cp_obj, str):
        cp_obj = json.loads(cp_obj)

    try:
        cp = transform_cyberpartner_dict(cp_obj)
        return cp.mqtt_payload()
    except AttributeError as ae:
        logger.error(f"Error transforming cyberpartner: {str(ae)}")
        logger.error(f"CP obj: {cp_obj}")
        return None
