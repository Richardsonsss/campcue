# CampCue

CampCue is a full-stack campground review platform. Search and filter
real U.S. campgrounds pulled live from the National Park Service's
Recreation.gov API, browse each one's real photos and location on Google
Maps, and leave a rating and review. No fake data, no stock photos - the
listings are backed by the same public dataset recreation.gov itself
runs on (currently 65 real campgrounds across CA/WA/NY, each with a real
photo).

**Live app:** https://campcue.web.app

**Stack:** React (Vite) · Django REST Framework · MongoDB (geospatial
queries via a `2dsphere` index) · pandas ETL pipeline · Google Maps
JavaScript API · deployed on Cloud Run + Firebase Hosting + MongoDB Atlas,
entirely on free tiers.

## Origin

Rebuilt from this resume entry:

> **Campground Review System**
> Independent Full-Stack Developer

- Architected and deployed a full-stack review platform for 50+ campground
  locations, owning the system from data model design through production
  deployment.
- Built backend services with Django and MongoDB and a responsive React
  frontend, connected via REST APIs to support search, review, and rating
  functionality.
- Integrated the Google Maps API for geospatial search and deployed on
  Google Cloud Platform for scalable, reliable public access.
- Engineered Python and Pandas data-automation pipelines to clean,
  validate, and consolidate operational records across multiple
  facilities, replacing manual spreadsheet processes and improving
  downstream data reliability.
- Built a digital data-processing workflow that cut processing time by 67%
  for 200+ records, deploying it to a centralized server to improve
  reporting accuracy and cross-team coordination.

## Architecture

```
data_pipeline/fetch_ridb_data.py --> real_campgrounds.json --> MongoDB Atlas ("campgrounds" collection)
                                                                        |
                                                                        v
                          backend/ (Django + DRF, pymongo) --- REST API --- frontend/ (React + Vite)
                          Cloud Run                                   |            Firebase Hosting
                                                                2dsphere index            |
                                                            (geospatial "nearby" search)   Google Maps JS API
                                                                                    (map view, pins, photos)
```

- **`data_pipeline/`** - two independent pieces:
  - `fetch_ridb_data.py` pulls **real** campground listings (names,
    coordinates, activities, photos) from Recreation.gov's public RIDB
    API. This is the app's actual data source - currently 65 campgrounds
    across CA/WA/NY, each with a real photo.
  - `generate_sample_data.py` / `legacy_manual_merge.py` /
    `clean_and_load.py` / `benchmark.py` are a **synthetic** demo,
    unrelated to the live app's data, that models the messy
    multi-facility-spreadsheet problem the pipeline bullet describes and
    measures the pandas pipeline's speedup over a naive one (~65% faster,
    consistent with the resume's 67% claim). See
    [`data_pipeline/README.md`](data_pipeline/README.md) for both.
- **`backend/`** - Django + Django REST Framework. Reads/writes MongoDB
  directly via `pymongo` (no ORM) so the data layer matches what the
  pipeline produces. Endpoints: search/filter, facets (distinct
  states/amenities for the UI's filter dropdowns), campground detail,
  geospatial nearby search, and review list/create with automatic rating
  recomputation.
- **`frontend/`** - React (Vite). Search/filter UI with pagination
  ("Load more"), campground cards with photo thumbnails and star ratings
  ("No reviews yet" instead of a misleading 0★ when unreviewed), a detail
  page with a photo gallery, review form, and Google Maps view.
- **`deploy/`** - the actual commands used for the live deployment
  (Cloud Run + MongoDB Atlas + Firebase Hosting) - see
  [`deploy/README.md`](deploy/README.md).

## Live deployment

| Piece | Where | URL |
|---|---|---|
| Frontend | Firebase Hosting | https://campcue.web.app |
| Backend API | Cloud Run | https://campground-backend-793519184426.us-central1.run.app/api |
| Database | MongoDB Atlas | (private connection string) |

All on free tiers - should run at $0/month for light hobby traffic. See
[`deploy/README.md`](deploy/README.md) for the exact commands and the
gotchas hit along the way (Cloud Run's DNS can't resolve `mongodb+srv://`
SRV records; Docker build-arg injection needs an explicit `cloudbuild.yaml`
rather than `--set-build-env-vars`).

## Running it locally

### Windows, no Docker: `run.ps1`

Starts MongoDB, the Django backend, and the frontend each in their own
window (assumes one-time setup is already done - see "Running services
individually" below for the first-time `pip install`/`npm install`):

```bash
powershell -ExecutionPolicy Bypass -File run.ps1
```

### Fastest path: Docker Compose

```bash
docker compose up --build
```

Then seed the database once with real campground data (see
[`data_pipeline/README.md`](data_pipeline/README.md) for one-time
credential setup):

```bash
cd data_pipeline
pip install -r requirements.txt
python fetch_ridb_data.py --load-mongo
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api/campgrounds/

### Running services individually

**MongoDB** - any local instance or `mongod --dbpath <dir>`.

**Backend**
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # edit MONGO_URI etc. if not using localhost defaults
python manage.py migrate --run-syncdb
python manage.py runserver 8000
```

**Data pipeline** (populate MongoDB with real campground data - see
[`data_pipeline/README.md`](data_pipeline/README.md) for credential setup)
```bash
cd data_pipeline
pip install -r requirements.txt
cp .env.example .env
python fetch_ridb_data.py --load-mongo
```

**Frontend** (see `.env.example` for optional configuration)
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Map panels show a placeholder rather than failing if not fully
configured - search, filtering, ratings, and reviews all work regardless.

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
python manage.py test campgrounds
```

The suite runs against [`mongomock`](https://github.com/mongomock/mongomock)
so it needs no live database. It doesn't cover `/campgrounds/nearby/`,
since mongomock doesn't implement MongoDB's `$geoNear` aggregation stage -
that endpoint is exercised manually against a real MongoDB instance
instead (see `data_pipeline/README.md` for how the sample data is loaded).

## API

| Endpoint | Description |
|---|---|
| `GET /api/campgrounds/` | Search/filter/paginate (`q`, `state`, `min_rating`, `amenity`, `sort`, `limit`, `offset`) |
| `GET /api/campgrounds/facets/` | Distinct states and amenities present in the data, for the frontend's filter dropdowns |
| `GET /api/campgrounds/<id>/` | Campground detail |
| `GET /api/campgrounds/nearby/` | Geospatial search (`lat`, `lng`, `radius_km`) |
| `GET /api/campgrounds/<id>/reviews/` | List reviews for a campground |
| `POST /api/campgrounds/<id>/reviews/` | Add a review (`author`, `rating` 1-5, `comment`); recomputes the campground's average rating |
