# Deploying to Google Cloud Platform + Firebase Hosting

The actual commands used for the live deployment
(https://campcue.web.app), including the gotchas that broke the first
attempt. Backend runs on **Cloud Run**, data lives in **MongoDB Atlas**,
and the frontend is on **Firebase Hosting** (not Cloud Run - see
"Why Firebase Hosting for the frontend" below).

## 0. One-time setup

- A GCP project with billing enabled (Cloud Run's free tier covers a
  hobby app; billing must still be linked to enable the APIs)
- `gcloud auth login` **and** `gcloud auth application-default login` -
  these are two separate credential stores; commands that fail with a
  vague `403 PERMISSION_DENIED` despite correct IAM roles are usually
  missing the second one, or it was done with the wrong Google account
  if you have several signed into your browser (check with
  `gcloud auth application-default print-access-token` piped through
  Google's tokeninfo endpoint if unsure which account is active)
- A [MongoDB Atlas](https://www.mongodb.com/atlas) free M0 cluster - a
  DB user under **Database Access**, and **Network Access** allowing
  `0.0.0.0/0`

## 1. MongoDB Atlas - use the non-SRV connection string

Atlas's default connection string uses `mongodb+srv://`, which requires a
DNS SRV/TXT record lookup at connect time. **Cloud Run's default resolver
can't complete this lookup reliably** - the symptom is a gunicorn
`WORKER TIMEOUT` (misreported as "Perhaps out of memory?") on every
request that touches the database, even though the exact same URI works
fine from a normal machine.

Fix: resolve the actual shard hostnames once, and build a standard
`mongodb://` URI instead:

```bash
nslookup -type=SRV _mongodb._tcp.<cluster>.mongodb.net
nslookup -type=TXT <cluster>.mongodb.net
```

This gives you 3 shard hostnames and a `replicaSet` name. Build:

```
mongodb://<user>:<password>@<shard0>:27017,<shard1>:27017,<shard2>:27017/?ssl=true&replicaSet=<name>&authSource=admin&retryWrites=true&w=majority
```

Switching `--execution-environment=gen2` on the Cloud Run service does
**not** fix this on its own - the non-SRV URI is what actually works.

## 2. Backend (Cloud Run)

Env vars with commas and `&` in them (any Mongo URI with multiple hosts)
break both `--set-env-vars` (comma is its own list delimiter) and Windows'
`gcloud.cmd` batch-file argument parsing (unescaped `&` gets interpreted
as a shell command separator). Use an env-vars YAML file instead of
inline flags:

```yaml
# backend_env_vars.yaml (gitignored - contains the DB password)
DJANGO_DEBUG: "False"
DJANGO_ALLOWED_HOSTS: ".run.app"
MONGO_DB_NAME: "campground_reviews"
CORS_ALLOWED_ORIGINS: "https://campcue.web.app,https://campcue.firebaseapp.com"
MONGO_URI: "mongodb://user:password@shard0:27017,shard1:27017,shard2:27017/?ssl=true&replicaSet=...&authSource=admin&retryWrites=true&w=majority"
```

```bash
gcloud run deploy campground-backend \
  --source ./backend \
  --region us-central1 \
  --allow-unauthenticated \
  --env-vars-file=backend_env_vars.yaml
```

Load real data once, pointed at the same Atlas cluster:

```bash
cd data_pipeline
python fetch_ridb_data.py --load-mongo   # or point MONGO_URI at Atlas and rerun
```

Whenever the frontend's origin changes (e.g. after setting up Firebase
Hosting), update `CORS_ALLOWED_ORIGINS` in the yaml and re-run:

```bash
gcloud run services update campground-backend --region us-central1 --env-vars-file=backend_env_vars.yaml
```

## 3. Frontend - Firebase Hosting, not Cloud Run

Two reasons this project ended up on Firebase Hosting instead of a second
Cloud Run service:

1. **Free custom-looking subdomain.** Cloud Run's `*.run.app` URLs always
   include an auto-generated project number
   (`campground-frontend-793519184426.us-central1.run.app`) with no way
   to shorten it. Firebase Hosting lets you create an additional
   **site** with any available name, giving a clean
   `https://campcue.web.app` for free, no domain purchase, no Cloud Run
   project-number suffix.
2. **`--set-build-env-vars` doesn't inject Docker build args.** For a
   Dockerfile-based `gcloud run deploy --source`, that flag is a
   buildpacks-era option and silently does nothing for a Docker build -
   the frontend shipped still pointed at `localhost:8000`. The fix (if
   you do want Cloud Run for the frontend) is an explicit
   `cloudbuild.yaml` that passes real `--build-arg`s to `docker build`.
   Firebase Hosting sidesteps this entirely since it just serves the
   already-built `dist/` folder - no Docker involved.

### Setup (one-time)

```bash
npm install -g firebase-tools
firebase login                              # your own browser login
firebase projects:addfirebase <gcp-project-id>
```

If `addFirebase` fails with an opaque `403 PERMISSION_DENIED` even though
your account is Owner on the project: Firebase requires accepting its
Terms of Service through the **web console** at least once
(console.firebase.google.com → Add project → select your existing GCP
project) before the API allows it via CLI. If that produces a
differently-named project than expected (Firebase sometimes creates a
new project like `<name>-a1b2c` instead of attaching to the existing
one), that's fine - Hosting doesn't need to be in the same GCP project as
Cloud Run. Just create a custom-named **site** inside whatever project
you got:

```bash
firebase hosting:sites:create campcue --project <firebase-project-id>
```

### `.firebaserc` and `firebase.json` (in `frontend/`)

```json
// .firebaserc
{
  "projects": { "default": "<firebase-project-id>" },
  "targets": { "<firebase-project-id>": { "hosting": { "campcue": ["campcue"] } } }
}
```

```json
// firebase.json
{
  "hosting": {
    "target": "campcue",
    "public": "dist",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [{ "source": "**", "destination": "/index.html" }]
  }
}
```

### Build and deploy

Build with the production API URL and Maps key baked in (Vite inlines
env vars at build time - `.env.production` is picked up automatically by
`vite build`):

```bash
# frontend/.env.production (gitignored)
VITE_API_BASE_URL=https://campground-backend-793519184426.us-central1.run.app/api
VITE_GOOGLE_MAPS_API_KEY=your-key-here
```

```bash
cd frontend
npm run build
firebase deploy --only hosting:campcue --project <firebase-project-id>
```

## 4. Google Maps API key

Enable **Maps JavaScript API** in the GCP project, create a key. An HTTP
referrer restriction (limiting it to `campcue.web.app` and `localhost`)
is good practice but not required for the key to work - Maps keys with no
restriction still function everywhere, they're just less locked-down.
