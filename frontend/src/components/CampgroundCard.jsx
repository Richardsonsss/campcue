import { Link } from "react-router-dom";

import RatingStars from "./RatingStars.jsx";

export default function CampgroundCard({ campground }) {
  const thumbnail = campground.photos?.[0];

  return (
    <Link to={`/campgrounds/${campground.id}`} className="campground-card">
      {thumbnail ? (
        <img className="card-thumbnail" src={thumbnail} alt={campground.name} loading="lazy" />
      ) : (
        <div className="card-thumbnail placeholder" aria-hidden="true">🏕️</div>
      )}
      <h3>{campground.name}</h3>
      <p className="location">{campground.city}, {campground.state}</p>
      <RatingStars rating={campground.avg_rating} reviewCount={campground.review_count} />
      <p className="amenities">{campground.amenities.slice(0, 4).join(" · ")}</p>
      {typeof campground.distance_km === "number" && (
        <p className="distance">{campground.distance_km} km away</p>
      )}
      {!campground.open && <span className="badge closed">Closed</span>}
    </Link>
  );
}
