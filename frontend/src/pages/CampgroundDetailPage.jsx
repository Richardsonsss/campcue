import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getCampground, getReviews, postReview } from "../api/client.js";
import MapView from "../components/MapView.jsx";
import PhotoGallery from "../components/PhotoGallery.jsx";
import RatingStars from "../components/RatingStars.jsx";
import ReviewForm from "../components/ReviewForm.jsx";
import ReviewList from "../components/ReviewList.jsx";

export default function CampgroundDetailPage() {
  const { id } = useParams();
  const [campground, setCampground] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reviewsLoading, setReviewsLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const loadReviews = () => {
    setReviewsLoading(true);
    return getReviews(id)
      .then((data) => setReviews(data.results))
      .finally(() => setReviewsLoading(false));
  };

  useEffect(() => {
    setLoading(true);
    getCampground(id)
      .then(setCampground)
      .catch(() => setError("Campground not found."))
      .finally(() => setLoading(false));
    loadReviews();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleSubmitReview = async (review) => {
    setSubmitting(true);
    try {
      await postReview(id, review);
      await Promise.all([loadReviews(), getCampground(id).then(setCampground)]);
    } catch {
      setError("Couldn't submit your review. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <p className="status-message">Loading...</p>;
  if (error || !campground) return <p className="status-message error">{error || "Not found."}</p>;

  return (
    <div className="detail-page">
      <Link to="/" className="back-link">&larr; Back to search</Link>

      <h2>{campground.name}</h2>
      <p className="location">{campground.city}, {campground.state}</p>
      <RatingStars rating={campground.avg_rating} reviewCount={campground.review_count} />
      {!campground.open && <span className="badge closed">Closed</span>}

      <PhotoGallery photos={campground.photos} name={campground.name} />

      <div className="detail-body">
        <div className="detail-info">
          <p><strong>Amenities:</strong> {campground.amenities.join(", ") || "None listed"}</p>

          <ReviewForm onSubmit={handleSubmitReview} submitting={submitting} />
          <h4>Reviews</h4>
          <ReviewList reviews={reviews} loading={reviewsLoading} />
        </div>
        <div className="detail-map">
          <MapView
            center={{ lat: campground.lat, lng: campground.lng }}
            zoom={12}
            markers={[{ id: campground.id, lat: campground.lat, lng: campground.lng, name: campground.name }]}
          />
        </div>
      </div>
    </div>
  );
}
