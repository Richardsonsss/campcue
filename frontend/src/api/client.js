import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

const client = axios.create({ baseURL: API_BASE_URL });

export function searchCampgrounds(params = {}) {
  return client.get("/campgrounds/", { params }).then((res) => res.data);
}

export function getCampground(id) {
  return client.get(`/campgrounds/${id}/`).then((res) => res.data);
}

export function getFacets() {
  return client.get("/campgrounds/facets/").then((res) => res.data);
}

export function getNearbyCampgrounds({ lat, lng, radiusKm = 50 }) {
  return client
    .get("/campgrounds/nearby/", { params: { lat, lng, radius_km: radiusKm } })
    .then((res) => res.data);
}

export function getReviews(campgroundId, params = {}) {
  return client.get(`/campgrounds/${campgroundId}/reviews/`, { params }).then((res) => res.data);
}

export function postReview(campgroundId, { author, rating, comment }) {
  return client
    .post(`/campgrounds/${campgroundId}/reviews/`, { author, rating, comment })
    .then((res) => res.data);
}

export default client;
