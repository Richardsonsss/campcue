import { useState } from "react";

export default function PhotoGallery({ photos = [], name }) {
  const [activeIndex, setActiveIndex] = useState(0);

  if (photos.length === 0) {
    return (
      <div className="photo-gallery placeholder">
        <span aria-hidden="true">🏕️</span>
        <p>No photos available for this campground yet.</p>
      </div>
    );
  }

  return (
    <div className="photo-gallery">
      <img className="gallery-main" src={photos[activeIndex]} alt={name} />
      {photos.length > 1 && (
        <div className="gallery-thumbs">
          {photos.map((url, i) => (
            <button
              key={url}
              type="button"
              className={i === activeIndex ? "active" : ""}
              onClick={() => setActiveIndex(i)}
            >
              <img src={url} alt={`${name} photo ${i + 1}`} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
