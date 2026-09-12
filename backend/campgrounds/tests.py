"""
Exercises the campgrounds API against mongomock instead of a live MongoDB
instance, so the suite runs with no external services.

Note: mongomock does not implement `$geoNear`, so CampgroundNearbyView isn't
covered here - it uses MongoDB's native geospatial aggregation, which needs
a real instance (see README's "Running against a live MongoDB" section for
a manual verification recipe via docker compose).
"""
from unittest.mock import patch

import mongomock
from rest_framework.test import APITestCase

from campgrounds import db as db_module


class CampgroundAPITestCase(APITestCase):
    def setUp(self):
        self.mongo_client = mongomock.MongoClient()
        patcher = patch.object(db_module, "get_client", return_value=self.mongo_client)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.db = self.mongo_client["campground_reviews"]
        self.campgrounds = self.db["campgrounds"]
        self.reviews = self.db["reviews"]

        self.campground_id = self.campgrounds.insert_one({
            "name": "Pine Ridge Campground",
            "city": "Lake Placid",
            "state": "NY",
            "lat": 44.28,
            "lng": -73.98,
            "amenities": ["wifi", "showers"],
            "photos": ["https://example.com/pine-ridge-1.jpg"],
            "sites": 80,
            "open": True,
            "avg_rating": 0.0,
            "review_count": 0,
            "source_facility": "northeast",
        }).inserted_id

        self.campgrounds.insert_one({
            "name": "Cedar Woods RV Resort",
            "city": "Bend",
            "state": "OR",
            "lat": 44.06,
            "lng": -121.31,
            "amenities": ["pet friendly"],
            "sites": 40,
            "open": True,
            "avg_rating": 0.0,
            "review_count": 0,
            "source_facility": "west",
        })


class CampgroundListViewTests(CampgroundAPITestCase):
    def test_lists_all_campgrounds_by_default(self):
        response = self.client.get("/api/campgrounds/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_search_by_name(self):
        response = self.client.get("/api/campgrounds/", {"q": "pine"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Pine Ridge Campground")

    def test_filter_by_state(self):
        response = self.client.get("/api/campgrounds/", {"state": "or"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["city"], "Bend")

    def test_filter_by_amenity(self):
        response = self.client.get("/api/campgrounds/", {"amenity": "wifi"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Pine Ridge Campground")


class CampgroundFacetsViewTests(CampgroundAPITestCase):
    def test_returns_distinct_states_and_amenities(self):
        response = self.client.get("/api/campgrounds/facets/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["states"], ["NY", "OR"])
        self.assertEqual(
            response.data["amenities"], ["pet friendly", "showers", "wifi"]
        )


class CampgroundDetailViewTests(CampgroundAPITestCase):
    def test_returns_campground_by_id(self):
        response = self.client.get(f"/api/campgrounds/{self.campground_id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Pine Ridge Campground")
        self.assertEqual(response.data["photos"], ["https://example.com/pine-ridge-1.jpg"])

    def test_404_for_missing_campground(self):
        response = self.client.get("/api/campgrounds/000000000000000000000000/")
        self.assertEqual(response.status_code, 404)

    def test_404_for_malformed_id(self):
        response = self.client.get("/api/campgrounds/not-an-id/")
        self.assertEqual(response.status_code, 404)


class ReviewListCreateViewTests(CampgroundAPITestCase):
    def test_create_review_and_recompute_rating(self):
        response = self.client.post(
            f"/api/campgrounds/{self.campground_id}/reviews/",
            {"author": "Alex", "rating": 4, "comment": "Great spot"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.post(
            f"/api/campgrounds/{self.campground_id}/reviews/",
            {"author": "Sam", "rating": 2, "comment": "Bathrooms were rough"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        campground = self.campgrounds.find_one({"_id": self.campground_id})
        self.assertEqual(campground["review_count"], 2)
        self.assertEqual(campground["avg_rating"], 3.0)

        listing = self.client.get(f"/api/campgrounds/{self.campground_id}/reviews/")
        self.assertEqual(listing.data["count"], 2)

    def test_rejects_invalid_rating(self):
        response = self.client.post(
            f"/api/campgrounds/{self.campground_id}/reviews/",
            {"author": "Alex", "rating": 9, "comment": "too high"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_404_when_campground_missing(self):
        response = self.client.post(
            "/api/campgrounds/000000000000000000000000/reviews/",
            {"author": "Alex", "rating": 5, "comment": ""},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_rate_limits_review_posting_per_ip(self):
        from campgrounds.views import REVIEW_POST_LIMIT_PER_HOUR

        for i in range(REVIEW_POST_LIMIT_PER_HOUR):
            response = self.client.post(
                f"/api/campgrounds/{self.campground_id}/reviews/",
                {"author": f"User{i}", "rating": 5, "comment": ""},
                format="json",
            )
            self.assertEqual(response.status_code, 201)

        response = self.client.post(
            f"/api/campgrounds/{self.campground_id}/reviews/",
            {"author": "OneTooMany", "rating": 5, "comment": ""},
            format="json",
        )
        self.assertEqual(response.status_code, 429)
