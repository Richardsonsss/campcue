import { useJsApiLoader } from "@react-google-maps/api";

const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || "";

// useJsApiLoader dedupes internally by `id`, so calling it from every
// MapView instance (rather than once at the app root) is safe against the
// double-script-injection bug <LoadScript> had under StrictMode - and it
// means the Maps script only starts downloading when a page that actually
// shows a map mounts (the campground detail page), not on every visit to
// the map-less search page.
export function useGoogleMapsLoader() {
  return useJsApiLoader({
    id: "google-map-script",
    googleMapsApiKey: GOOGLE_MAPS_API_KEY,
  });
}

export { GOOGLE_MAPS_API_KEY };
