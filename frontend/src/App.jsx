import { Link, Route, Routes } from "react-router-dom";

import { GoogleMapsProvider } from "./mapsLoader.jsx";
import CampgroundDetailPage from "./pages/CampgroundDetailPage.jsx";
import SearchPage from "./pages/SearchPage.jsx";

export default function App() {
  return (
    <GoogleMapsProvider>
      <div className="app">
        <header className="app-header">
          <Link to="/" className="app-title">
            🏕️ CampCue
          </Link>
        </header>
        <main className="app-main">
          <Routes>
            <Route path="/" element={<SearchPage />} />
            <Route path="/campgrounds/:id" element={<CampgroundDetailPage />} />
          </Routes>
        </main>
      </div>
    </GoogleMapsProvider>
  );
}
