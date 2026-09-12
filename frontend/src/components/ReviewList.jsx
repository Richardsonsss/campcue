import RatingStars from "./RatingStars.jsx";

export default function ReviewList({ reviews, loading }) {
  if (loading) return <p className="status-message">Loading reviews...</p>;
  if (reviews.length === 0) {
    return <p className="status-message">No reviews yet. Be the first to leave one!</p>;
  }

  return (
    <ul className="review-list">
      {reviews.map((r) => (
        <li key={r.id} className="review-item">
          <div className="review-header">
            <strong>{r.author}</strong>
            <RatingStars rating={r.rating} />
            <span className="review-date">
              {r.created_at ? new Date(r.created_at).toLocaleDateString() : ""}
            </span>
          </div>
          {r.comment && <p className="review-comment">{r.comment}</p>}
        </li>
      ))}
    </ul>
  );
}
