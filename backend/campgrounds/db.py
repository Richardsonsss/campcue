"""
Single shared pymongo connection for the app. Django settings hold the URI
and DB name so the same code works locally, in Docker Compose, and against
a managed Mongo instance in production.
"""
from functools import lru_cache

from django.conf import settings
from pymongo import MongoClient


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    return MongoClient(settings.MONGO_URI)


def get_db():
    return get_client()[settings.MONGO_DB_NAME]


def campgrounds_collection():
    return get_db()["campgrounds"]


def reviews_collection():
    return get_db()["reviews"]
