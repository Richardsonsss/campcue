"""
Per-IP rate limiting backed by MongoDB rather than Django's cache
framework. This API runs on Cloud Run with scale-to-zero, which spins up
a fresh container (and a fresh in-memory cache) on every cold start -
DRF's default AnonRateThrottle would silently reset every time the
service idles out, making it useless here. MongoDB is already part of
the stack and persists across cold starts, so counters live there
instead, with a TTL index to auto-expire old windows for free.

Fixed-window counter (not sliding), bucketed by the hour: good enough for
anti-abuse purposes without needing a more precise algorithm.
"""
from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument
from rest_framework.exceptions import Throttled

from .db import rate_limits_collection

_TTL_INDEX_READY = False


def _ensure_ttl_index():
    """Create the auto-expiry index once per process (idempotent - cheap
    to call repeatedly, but avoid doing it on every single request)."""
    global _TTL_INDEX_READY
    if _TTL_INDEX_READY:
        return
    rate_limits_collection().create_index("expires_at", expireAfterSeconds=0)
    _TTL_INDEX_READY = True


def get_client_ip(request):
    # Cloud Run terminates TLS at a proxy, so the real client IP arrives
    # via X-Forwarded-For rather than REMOTE_ADDR.
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def enforce_rate_limit(request, action, limit, window_seconds=3600):
    """Raises DRF's Throttled (-> HTTP 429) if this IP has made more than
    `limit` calls to `action` in the current hour-bucketed window."""
    _ensure_ttl_index()

    ip = get_client_ip(request)
    now = datetime.now(timezone.utc)
    bucket = now.strftime("%Y-%m-%dT%H")
    key = f"{action}:{ip}:{bucket}"

    doc = rate_limits_collection().find_one_and_update(
        {"_id": key},
        {
            "$inc": {"count": 1},
            "$setOnInsert": {"expires_at": now + timedelta(seconds=window_seconds)},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    if doc["count"] > limit:
        raise Throttled(detail=f"Too many requests - limit is {limit} per hour. Try again later.")
