import { GoogleMap, InfoWindow, Marker } from "@react-google-maps/api";
import { useCallback, useEffect, useRef, useState } from "react";

import { GOOGLE_MAPS_API_KEY, useGoogleMapsLoader } from "../mapsLoader.jsx";

const containerStyle = { width: "100%", height: "100%" };

export default function MapView({ center, zoom = 10, markers = [] }) {
  const { isLoaded, loadError } = useGoogleMapsLoader();
  const [activeMarkerId, setActiveMarkerId] = useState(null);
  const mapRef = useRef(null);

  // Belt-and-suspenders: force a resize/recenter after mount in case the
  // surrounding CSS grid/sticky layout hasn't finished settling when the
  // map first measures its container.
  const resizeMap = useCallback(() => {
    if (mapRef.current && window.google) {
      window.google.maps.event.trigger(mapRef.current, "resize");
      mapRef.current.setCenter(center);
    }
  }, [center]);

  const handleLoad = useCallback((map) => {
    mapRef.current = map;
    resizeMap();
  }, [resizeMap]);

  useEffect(() => {
    resizeMap();
    window.addEventListener("resize", resizeMap);
    return () => window.removeEventListener("resize", resizeMap);
  }, [resizeMap]);

  if (!GOOGLE_MAPS_API_KEY) {
    return (
      <div className="map-placeholder">
        <p>Map preview unavailable.</p>
        <p className="hint">
          Set VITE_GOOGLE_MAPS_API_KEY in frontend/.env to enable the live Google Map
          (see frontend/.env.example).
        </p>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="map-placeholder">
        <p>Couldn't load Google Maps.</p>
        <p className="hint">Check that VITE_GOOGLE_MAPS_API_KEY is valid and the Maps JavaScript API is enabled.</p>
      </div>
    );
  }

  if (!isLoaded) {
    return <div className="map-placeholder"><p>Loading map...</p></div>;
  }

  return (
    <GoogleMap mapContainerStyle={containerStyle} center={center} zoom={zoom} onLoad={handleLoad}>
      {markers.map((m) => (
        <Marker
          key={m.id}
          position={{ lat: m.lat, lng: m.lng }}
          onClick={() => setActiveMarkerId(m.id)}
        >
          {activeMarkerId === m.id && (
            <InfoWindow onCloseClick={() => setActiveMarkerId(null)}>
              <div>
                <strong>{m.name}</strong>
                {m.city && <div>{m.city}</div>}
              </div>
            </InfoWindow>
          )}
        </Marker>
      ))}
    </GoogleMap>
  );
}
