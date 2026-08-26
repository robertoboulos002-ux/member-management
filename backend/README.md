# Member Management API

A lightweight FastAPI REST API skeleton for a learning-focused member management application. This initial version exposes only a health-check endpoint, with the full member CRUD functionality to be added incrementally.

## Setup

### 1. Create a virtual environment

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and adjust values if needed:

```bash
cp .env.example .env        # Linux/macOS
copy .env.example .env      # Windows
```

## Running the server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`. Interactive docs are at `http://127.0.0.1:8000/docs`.

## Testing the health endpoint

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status": "ok", "timestamp": "2026-08-09T12:34:56.789012+00:00"}
```


## Admin access

Member records are personal data — names, parents, and dates and places of birth
and baptism — so the API does not serve them to anonymous callers. Every
`/members` route requires an admin session; `/`, `/health` and `/health/database`
stay open, because they carry no member data and are what you need when login
itself is what is broken.

### How it works

1. The dashboard sends the password once to `POST /auth/login`.
2. The server compares it in constant time against `ADMIN_PASSWORD` and returns
   an HMAC-signed token carrying nothing but its own expiry.
3. The browser keeps that token in `sessionStorage` and sends it as
   `Authorization: Bearer <token>` on every request. The password is never
   stored, and neither is any member data.
4. Anything else — a missing, malformed, expired or forged token — is answered
   `401`, and the frontend returns to the login page.

Repeated failed logins from one address are throttled: after
`MAX_FAILED_ATTEMPTS` within 15 minutes, further attempts are answered `429`
without the password being checked at all. The counter lives in process memory,
so each worker throttles separately.

### Configuration

Set `ADMIN_PASSWORD` in the environment (`backend/.env` locally, the service's
environment variables on Render). **It has no default.** Without it, `/auth/login`
answers `503` and no member endpoint will serve anyone — deliberately: an
unconfigured deployment locks up rather than opening.

`ADMIN_SESSION_SECRET` and `ADMIN_SESSION_HOURS` are optional; see
`.env.example`. By default the signing key is derived from the password, so
changing the password ends every existing session.

### What this does not do

The token is a bearer token in browser storage, so **serve both the API and the
frontend over HTTPS** — over plain HTTP the token, like the password, travels in
clear. There is one shared password and no user accounts, so there is nothing to
attribute a change to and no way to revoke one person's access without changing
the password for everyone. Both are reasonable for a single administrator; a
second one would be the point to add real accounts.


## Database migrations

Tables are created on startup with `Base.metadata.create_all()`, which only
creates *missing tables* — it never adds columns to a table that already
exists. When a field is added to the model, an already-populated database
needs the matching script in `migrations/` run once before the new code is
served:

```bash
python migrations/001_add_birthplace_and_godparents.py
```

Point `DATABASE_URL` at the target database first (unset, it migrates the
local SQLite file). The scripts are idempotent — re-running one is a no-op.

`001_add_birthplace_and_godparents.py` adds every column listed in
`app/migrate.py` as a late addition — `place_of_birth`, `baptism_number`, the
godparent names and the baptism fields. They are nullable in the database, so
members created before the change come back with `null` for them; the API
still requires them when creating or updating a member.

`baptism_number` is the parish register number and is **entered by the
admin** — it is deliberately not `id`, which the database assigns and which no
one chooses.


## Frontend

The frontend is a separate static app that talks to this API over HTTP/JSON — no build step or web server required: `admin.html`/`admin.js` are the login page, `index.html`/`app.js` the dashboard, `auth.js` the session handling shared by both, and `styles.css` the styling for all of it.

### Running the frontend

1. Make sure the backend is running (see steps above) — it listens on `http://127.0.0.1:8000`.
2. Confirm CORS is enabled in `app/main.py` (required so the frontend, opened as a local file, can call the API).
3. Make sure `ADMIN_PASSWORD` is set in `backend/.env` — without it, login is impossible and the member endpoints reject every request.
4. Open `frontend/admin.html` in your browser — double-click it, or right-click → **Open with** → your browser — and log in. Opening `index.html` first also works: it redirects to the login page.

### Using the app

- **Log in**: `index.html` redirects to `admin.html` until you have logged in. Enter the admin password there and you land on the dashboard.
- **Log out**: the **Log out** button in the header. The session also ends on its own when the browser tab closes, or when it expires.
- **Add a member**: fill in the form at the top and click **Add member**.
- **Search**: in the Search section, fill in any combination of first name, last name and intercessor name, then click **Search**. Multiple fields narrow the results together (AND); each one is a partial, case-insensitive match. Click **Clear** to return to the full list.
- **Edit a member**: click **Edit** in a row — the form switches to edit mode. Click **Save changes** to update, or **Cancel** to discard.
- **Delete a member**: click **Delete** in a row and confirm in the dialog.

The frontend calls the following endpoints:

| Action        | Method | Endpoint                          | Session required |
|---------------|--------|------------------------------------|---|
| Log in        | POST   | `/auth/login`                     | no |
| Check session | GET    | `/auth/session`                   | yes |
| List/search   | GET    | `/members?firstname=&lastname=&intercessor_name=` | yes |
| Get one       | GET    | `/members/{id}`                   | yes |
| Create        | POST   | `/members`                        | yes |
| Update        | PUT    | `/members/{id}`                   | yes |
| Delete        | DELETE | `/members/{id}`                   | yes |