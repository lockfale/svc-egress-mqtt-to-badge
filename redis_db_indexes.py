import os

redis_db_idx_cp_data = int(os.getenv("REDIS_DB_IDX_CP_DATA", 0))
redis_db_idx_last_notification_to_badge = int(os.getenv("REDIS_DB_IDX_LAST_PUB_TO_BADGE", 1))
redis_db_idx_cp_events = int(os.getenv("REDIS_DB_IDX_CP_EVENTS", 2))
redis_db_idx_last_source_uuid_badge = int(os.getenv("REDIS_DB_IDX_LAST_SOURCE_UUID_BADGE", 3))
redis_db_idx_cp_inventory = int(os.getenv("REDIS_DB_IDX_CP_INVENTORY", 5))
redis_db_idx_game_store = int(os.getenv("REDIS_DB_IDX_GAME_STORE", 6))
