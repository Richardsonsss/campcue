import { useState } from "react";

export default function ReviewForm({ onSubmit, submitting }) {
  const [author, setAuthor] = useState("");
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [validationError, setValidationError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!author.trim()) {
      setValidationError("Please enter your name.");
      return;
    }
    setValidationError("");
    await onSubmit({ author: author.trim(), rating: Number(rating), comment: comment.trim() });
    setAuthor("");
    setRating(5);
    setComment("");
  };

  return (
    <form className="review-form" onSubmit={handleSubmit}>
      <h4>Comments</h4>
      {validationError && <p className="status-message error">{validationError}</p>}
      <div className="form-row">
        <label>
          Name
          <input value={author} onChange={(e) => setAuthor(e.target.value)} maxLength={100} />
        </label>
        <label>
          Rating
          <select value={rating} onChange={(e) => setRating(e.target.value)}>
            {[5, 4, 3, 2, 1].map((n) => (
              <option key={n} value={n}>{n} star{n > 1 ? "s" : ""}</option>
            ))}
          </select>
        </label>
      </div>
      <label>
        Comment
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          maxLength={2000}
          rows={3}
        />
      </label>
      <button type="submit" disabled={submitting}>
        {submitting ? "Submitting..." : "Submit"}
      </button>
    </form>
  );
}
