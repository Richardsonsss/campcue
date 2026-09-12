import { useState } from "react";

export default function SearchBar({ filters, onChange, onFindNearMe, geoStatus, facets }) {
  const [q, setQ] = useState(filters.q || "");

  const submit = (e) => {
    e.preventDefault();
    onChange({ ...filters, q });
  };

  return (
    <form className="search-bar" onSubmit={submit}>
      <input
        type="text"
        placeholder="Search by campground name or city..."
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />

      <select
        value={filters.state || ""}
        onChange={(e) => onChange({ ...filters, state: e.target.value })}
      >
        <option value="">All states</option>
        {(facets?.states || []).map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>

      <select
        value={filters.min_rating || ""}
        onChange={(e) => onChange({ ...filters, min_rating: e.target.value })}
      >
        <option value="">Any rating</option>
        <option value="4">4+ stars</option>
        <option value="3">3+ stars</option>
        <option value="2">2+ stars</option>
      </select>

      <select
        value={filters.amenity || ""}
        onChange={(e) => onChange({ ...filters, amenity: e.target.value })}
      >
        <option value="">Any activity</option>
        {(facets?.amenities || []).map((a) => (
          <option key={a} value={a}>{a}</option>
        ))}
      </select>

      <button type="submit">Search</button>
      <button type="button" className="secondary" onClick={onFindNearMe}>
        {geoStatus === "loading" ? "Locating..." : "📍 Near Me"}
      </button>
    </form>
  );
}
