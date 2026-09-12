"""
Campground/review documents come from MongoDB as plain dicts, not Django ORM
model instances, so reads use small serialize_* helpers and writes use
plain DRF Serializers purely for input validation.
"""
from rest_framework import serializers


def serialize_campground(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name", ""),
        "city": doc.get("city", ""),
        "state": doc.get("state", ""),
        "lat": doc.get("lat"),
        "lng": doc.get("lng"),
        "amenities": doc.get("amenities", []),
        "photos": doc.get("photos", []),
        "sites": doc.get("sites", 0),
        "open": doc.get("open", True),
        "avg_rating": round(doc.get("avg_rating", 0.0), 2),
        "review_count": doc.get("review_count", 0),
        "source_facility": doc.get("source_facility", ""),
    }


def serialize_review(doc: dict) -> dict:
    created_at = doc.get("created_at")
    return {
        "id": str(doc["_id"]),
        "campground_id": str(doc["campground_id"]),
        "author": doc.get("author", ""),
        "rating": doc.get("rating"),
        "comment": doc.get("comment", ""),
        "created_at": created_at.isoformat() if created_at else None,
    }


class ReviewInputSerializer(serializers.Serializer):
    author = serializers.CharField(max_length=100)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=2000, allow_blank=True, required=False, default="")
