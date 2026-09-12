import CampgroundCard from "./CampgroundCard.jsx";

export default function CampgroundList({ campgrounds, loading, error }) {
  if (loading) return <p className="status-message">Loading campgrounds...</p>;
  if (error) return <p className="status-message error">{error}</p>;
  if (campgrounds.length === 0) {
    return <p className="status-message">No campgrounds matched your search.</p>;
  }

  return (
    <div className="campground-grid">
      {campgrounds.map((c) => (
        <CampgroundCard key={c.id} campground={c} />
      ))}
    </div>
  );
}
