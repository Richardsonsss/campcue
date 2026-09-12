import re
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from rest_framework.response import Response
from rest_framework.views import APIView

from .db import campgrounds_collection, reviews_collection
from .serializers import ReviewInputSerializer, serialize_campground, serialize_review

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def _paginate(request):
    try:
        limit = min(int(request.query_params.get("limit", DEFAULT_LIMIT)), MAX_LIMIT)
        offset = max(int(request.query_params.get("offset", 0)), 0)
    except ValueError:
        limit, offset = DEFAULT_LIMIT, 0
    return limit, offset


def _object_id_or_none(raw_id):
    try:
        return ObjectId(raw_id)
    except (InvalidId, TypeError):
        return None


class CampgroundListView(APIView):
    """
    GET /api/campgrounds/?q=&state=&min_rating=&amenity=wifi&amenity=showers&sort=&limit=&offset=
    Supports free-text search on name/city plus filtering, backing the
    platform's search/browse experience.
    """

    def get(self, request):
        query = {}

        q = request.query_params.get("q", "").strip()
        if q:
            pattern = re.compile(re.escape(q), re.IGNORECASE)
            query["$or"] = [{"name": pattern}, {"city": pattern}]

        state = request.query_params.get("state", "").strip()
        if state:
            query["state"] = state.upper()

        min_rating = request.query_params.get("min_rating")
        if min_rating:
            try:
                query["avg_rating"] = {"$gte": float(min_rating)}
            except ValueError:
                pass

        amenities = request.query_params.getlist("amenity")
        if amenities:
            query["amenities"] = {"$all": [a.lower() for a in amenities]}

        sort_param = request.query_params.get("sort", "name")
        sort_map = {
            "name": [("name", 1)],
            "-name": [("name", -1)],
            "rating": [("avg_rating", -1)],
            "sites": [("sites", -1)],
        }
        sort = sort_map.get(sort_param, sort_map["name"])

        limit, offset = _paginate(request)
        collection = campgrounds_collection()
        total = collection.count_documents(query)
        docs = collection.find(query).sort(sort).skip(offset).limit(limit)

        return Response({
            "count": total,
            "limit": limit,
            "offset": offset,
            "results": [serialize_campground(doc) for doc in docs],
        })


class CampgroundFacetsView(APIView):
    """
    GET /api/campgrounds/facets/
    Distinct states and activity/amenity values actually present in the
    data, so the frontend's filter dropdowns reflect real data instead of
    a hardcoded guess.
    """

    def get(self, request):
        collection = campgrounds_collection()
        states = sorted(s for s in collection.distinct("state") if s)
        amenities = sorted(a for a in collection.distinct("amenities") if a)
        return Response({"states": states, "amenities": amenities})


class CampgroundDetailView(APIView):
    def get(self, request, campground_id):
        oid = _object_id_or_none(campground_id)
        if oid is None:
            return Response({"detail": "Invalid campground id."}, status=404)

        doc = campgrounds_collection().find_one({"_id": oid})
        if doc is None:
            return Response({"detail": "Campground not found."}, status=404)

        return Response(serialize_campground(doc))


class CampgroundNearbyView(APIView):
    """
    GET /api/campgrounds/nearby/?lat=&lng=&radius_km=
    Geospatial search backing the Google Maps "find campgrounds near me"
    view on the frontend. Requires the 2dsphere index created by the
    data pipeline / seed_db management command.
    """

    def get(self, request):
        try:
            lat = float(request.query_params["lat"])
            lng = float(request.query_params["lng"])
        except (KeyError, ValueError):
            return Response({"detail": "lat and lng query params are required."}, status=400)

        try:
            radius_km = float(request.query_params.get("radius_km", 50))
        except ValueError:
            radius_km = 50

        collection = campgrounds_collection()
        pipeline = [
            {
                "$geoNear": {
                    "near": {"type": "Point", "coordinates": [lng, lat]},
                    "distanceField": "distance_meters",
                    "maxDistance": radius_km * 1000,
                    "spherical": True,
                }
            },
            {"$limit": 100},
        ]
        docs = list(collection.aggregate(pipeline))

        results = []
        for doc in docs:
            entry = serialize_campground(doc)
            entry["distance_km"] = round(doc["distance_meters"] / 1000, 2)
            results.append(entry)

        return Response({"results": results})


class ReviewListCreateView(APIView):
    """
    GET /api/campgrounds/<id>/reviews/  - list reviews for a campground
    POST /api/campgrounds/<id>/reviews/ - add a review; recomputes the
                                           campground's avg_rating/review_count
    """

    def get(self, request, campground_id):
        oid = _object_id_or_none(campground_id)
        if oid is None:
            return Response({"detail": "Invalid campground id."}, status=404)

        limit, offset = _paginate(request)
        collection = reviews_collection()
        query = {"campground_id": oid}
        total = collection.count_documents(query)
        docs = collection.find(query).sort([("created_at", -1)]).skip(offset).limit(limit)

        return Response({
            "count": total,
            "limit": limit,
            "offset": offset,
            "results": [serialize_review(doc) for doc in docs],
        })

    def post(self, request, campground_id):
        oid = _object_id_or_none(campground_id)
        if oid is None:
            return Response({"detail": "Invalid campground id."}, status=404)

        if campgrounds_collection().find_one({"_id": oid}, {"_id": 1}) is None:
            return Response({"detail": "Campground not found."}, status=404)

        serializer = ReviewInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        review_doc = {
            **serializer.validated_data,
            "campground_id": oid,
            "created_at": datetime.now(timezone.utc),
        }
        result = reviews_collection().insert_one(review_doc)
        review_doc["_id"] = result.inserted_id

        self._recompute_rating(oid)

        return Response(serialize_review(review_doc), status=201)

    @staticmethod
    def _recompute_rating(campground_oid):
        pipeline = [
            {"$match": {"campground_id": campground_oid}},
            {"$group": {"_id": "$campground_id", "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}},
        ]
        agg = list(reviews_collection().aggregate(pipeline))
        avg_rating = agg[0]["avg_rating"] if agg else 0.0
        review_count = agg[0]["count"] if agg else 0

        campgrounds_collection().update_one(
            {"_id": campground_oid},
            {"$set": {"avg_rating": avg_rating, "review_count": review_count}},
        )
