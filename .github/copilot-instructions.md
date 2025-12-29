# Copilot / AI Agent Instructions for `rdv du dimanche`

## Overview
- Minimal Flask site that reads/writes a single JSON DB (`data.json`) and serves static files from `static/`.
- Admin UI is a simple dashboard at `/admin` -> `/dashboard` that manages `events` and `artists` stored in `data.json`.
- Assets (uploaded images) are saved under `static/uploads` and referenced in JSON as `uploads/<filename>`.

## Key files & areas to read first
- `app.py` — main app, routes and business logic (saving events/artists, image handling, session admin check).
- `data.json` — canonical storage format; follow its shape when editing programmatically.
- `templates/` — Jinja templates for front-end; `index.html` and `dashboard.html` show how data is consumed.
- `static/uploads` — user-uploaded images; ensure persistence when running in Docker.
- `requirements.txt` and `Dockerfile` — how the project is installed and run in containers.

## Data model (practical notes)
- `events` is a LIST of event objects. Each event: `id`, `date_str` (free-form string), `time_str`, `link`, `description`, `flyer` (path or `""`), `guests` (array).
- `artists` is a DICT keyed by artist id with `{ id, name, bio, main_photo, gallery[] }`.
- The app sometimes uses simple string matching (see `save_event`) to find existing artists by name (case-insensitive).
- Do NOT assume `date_str` is machine-parseable; it's free-form for display.

## Common workflows & commands
- Local dev (Windows):
  - python -m venv venv
  - .\venv\Scripts\activate
  - pip install -r requirements.txt
  - python app.py
- Production (container):
  - docker build -t rdv-dimanche .
  - docker run -p 5000:5000 -v "%cd%/data.json:/app/data.json" -v "%cd%/static/uploads:/app/static/uploads" rdv-dimanche
  - Alternatively use `gunicorn app:app -b 0.0.0.0:5000` for a WSGI server (gunicorn is in `requirements.txt`).
- Manual verification: Visit `/` (public) and `/admin` (login with the admin password, then `/dashboard`) to exercise forms and uploads.

## Security & deployment caveats
- Secrets are hard-coded in `app.py`:
  - `app.secret_key = "david_rescue_key_v2024"`
  - Admin password is the literal string `"pitikon"` in `admin()` POST flow.
  - If deploying, change both to use environment variables and rotate secrets.
- Data (JSON + uploads) are on local filesystem; **mount persistent volumes** in Docker to avoid data loss.
- Allowed image extensions: `jpg, jpeg, png, webp` and max upload size is 32MB (`MAX_CONTENT_LENGTH`).

## Coding patterns to follow (observed in repo)
- Use `load_data()` / `save_data()` helpers to read/write `data.json` (these also perform simple fallbacks).
- IDs generated with `uuid.uuid4().hex` and used as keys in `artists` and `events`.
- Image paths stored relative to `static/` (e.g. `uploads/abc.jpg`) — templates expect `/static/{{...}}`.
- Keep templates simple; front-end uses Tailwind via CDN and small Alpine.js helpers — favor minimal JS changes.

## When making changes
- If modifying storage schema, update `load_data()` to provide backward-compatible defaults (see current implementation).
- Prefer making UI changes in `templates/` and minimizing server-side changes unless necessary.
- For any change that touches uploads or `data.json`, run manual end-to-end checks: create/edit/delete events and artists via the dashboard and confirm images are saved and referenced correctly.

## Testing & CI
- No tests currently exist. For PRs touching logic that mutates `data.json`, include a simple script that exercises `save_event`/`update_artist_profile` behavior or provide step-by-step manual verification instructions in the PR.

## Examples (quick jump-to in code)
- Find event by id: next((e for e in data['events'] if e['id'] == event_id), None) — used in `save_event` and deletion routes.
- Upload validation in `save_image(file)` — accepts only `jpg,jpeg,png,webp`.

---
If anything here is unclear or you want more detail (deployment strategy, tests, or secret rotation guidance), tell me which area to expand and I will update this file. ✅