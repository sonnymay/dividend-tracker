from functools import lru_cache

from app.config import get_settings
from supabase import Client, create_client


@lru_cache
def get_supabase() -> Client:
    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be configured.")

    return create_client(settings.supabase_url, settings.supabase_key)
