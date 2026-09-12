from django.urls import path

from .views import (
    CampgroundDetailView,
    CampgroundFacetsView,
    CampgroundListView,
    CampgroundNearbyView,
    ReviewListCreateView,
)

urlpatterns = [
    path("campgrounds/", CampgroundListView.as_view(), name="campground-list"),
    path("campgrounds/nearby/", CampgroundNearbyView.as_view(), name="campground-nearby"),
    path("campgrounds/facets/", CampgroundFacetsView.as_view(), name="campground-facets"),
    path("campgrounds/<str:campground_id>/", CampgroundDetailView.as_view(), name="campground-detail"),
    path("campgrounds/<str:campground_id>/reviews/", ReviewListCreateView.as_view(), name="campground-reviews"),
]
