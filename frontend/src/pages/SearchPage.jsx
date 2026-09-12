import { useEffect, useState } from "react";

import { getFacets, getNearbyCampgrounds, searchCampgrounds } from "../api/client.js";
import CampgroundList from "../components/CampgroundList.jsx";
import SearchBar from "../components/SearchBar.jsx";

const PAGE_SIZE = 20;

export default function SearchPage() {
  const [filters, setFilters] = useState({});
  const [campgrounds, setCampgrounds] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [geoStatus, setGeoStatus] = useState("idle");
  const [facets, setFacets] = useState(null);

  useEffect(() => {
    getFacets().then(setFacets).catch(() => setFacets({ states: [], amenities: [] }));
  }, []);

  const runSearch = (activeFilters) => {
    setLoading(true);
    setError(null);
    const params = Object.fromEntries(
      Object.entries(activeFilters).filter(([, v]) => v !== "" && v != null)
    );
    searchCampgrounds({ ...params, limit: PAGE_SIZE, offset: 0 })
      .then((data) => {
        setCampgrounds(data.results);
        setTotalCount(data.count);
      })
      .catch(() => setError("Couldn't load campgrounds. Is the backend running?"))
      .finally(() => setLoading(false));
  };

  const loadMore = () => {
    setLoadingMore(true);
    const params = Object.fromEntries(
      Object.entries(filters).filter(([, v]) => v !== "" && v != null)
    );
    searchCampgrounds({ ...params, limit: PAGE_SIZE, offset: campgrounds.length })
      .then((data) => setCampgrounds((prev) => [...prev, ...data.results]))
      .catch(() => setError("Couldn't load more campgrounds."))
      .finally(() => setLoadingMore(false));
  };

  useEffect(() => {
    runSearch(filters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFilterChange = (nextFilters) => {
    setFilters(nextFilters);
    runSearch(nextFilters);
  };

  const handleFindNearMe = () => {
    if (!navigator.geolocation) {
      setError("Geolocation isn't supported in this browser.");
      return;
    }
    setGeoStatus("loading");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setGeoStatus("idle");
        setLoading(true);
        getNearbyCampgrounds({ lat: coords.latitude, lng: coords.longitude, radiusKm: 100 })
          .then((data) => {
            setCampgrounds(data.results);
            setTotalCount(data.results.length);
          })
          .catch(() => setError("Couldn't load nearby campgrounds."))
          .finally(() => setLoading(false));
      },
      () => {
        setGeoStatus("idle");
        setError("Location permission denied.");
      }
    );
  };

  return (
    <div className="search-page">
      <SearchBar
        filters={filters}
        onChange={handleFilterChange}
        onFindNearMe={handleFindNearMe}
        geoStatus={geoStatus}
        facets={facets}
      />

      {!loading && !error && (
        <p className="result-count">
          Showing {campgrounds.length} of {totalCount} campground{totalCount === 1 ? "" : "s"}
        </p>
      )}

      <CampgroundList campgrounds={campgrounds} loading={loading} error={error} />

      {!loading && campgrounds.length < totalCount && (
        <div className="load-more-row">
          <button type="button" className="secondary" onClick={loadMore} disabled={loadingMore}>
            {loadingMore ? "Loading..." : `Load more (${totalCount - campgrounds.length} remaining)`}
          </button>
        </div>
      )}
    </div>
  );
}
