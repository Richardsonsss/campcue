import { useJsApiLoader } from "@react-google-maps/api";
import { createContext, useContext } from "react";

const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || "";

const GoogleMapsContext = createContext({ isLoaded: false, loadError: undefined });

// Loads the Google Maps script exactly once for the app's lifetime. Mounting
// <LoadScript> separately inside every MapView instance (search page, detail
// page) causes the script tag to be injected more than once whenever a
// component remounts - React 18 StrictMode does this deliberately in dev -
// which corrupts the map's internal tile positioning (shows as a mostly
// blank map with tiles jammed in one corner).
export function GoogleMapsProvider({ children }) {
  const { isLoaded, loadError } = useJsApiLoader({
    id: "google-map-script",
    googleMapsApiKey: GOOGLE_MAPS_API_KEY,
  });

  return (
    <GoogleMapsContext.Provider value={{ isLoaded, loadError }}>
      {children}
    </GoogleMapsContext.Provider>
  );
}

export function useGoogleMaps() {
  return useContext(GoogleMapsContext);
}

export { GOOGLE_MAPS_API_KEY };
