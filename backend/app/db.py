from functools import lru_cache

from supabase import Client, create_client

from app import config


@lru_cache
def get_db() -> Client:
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in backend/.env")
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
