export default function RatingStars({ rating = 0, reviewCount }) {
  if (reviewCount === 0) {
    return <span className="rating-stars no-reviews">No reviews yet</span>;
  }

  const rounded = Math.round(rating * 2) / 2;
  const stars = [1, 2, 3, 4, 5].map((n) => {
    if (n <= rounded) return "★";
    if (n - 0.5 === rounded) return "⯨";
    return "☆";
  });

  return (
    <span className="rating-stars" title={`${rating.toFixed(1)} / 5`}>
      <span className="stars">{stars.join("")}</span>
      {typeof reviewCount === "number" && (
        <span className="review-count"> ({reviewCount})</span>
      )}
    </span>
  );
}
