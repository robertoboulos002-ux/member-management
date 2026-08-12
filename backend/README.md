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


## Frontend

The frontend is a separate static app (`frontend/index.html`, `styles.css`, `app.js`) that talks to this API over HTTP/JSON — no build step or web server required.

### Running the frontend

1. Make sure the backend is running (see steps above) — it listens on `http://127.0.0.1:8000`.
2. Confirm CORS is enabled in `app/main.py` (required so the frontend, opened as a local file, can call the API).
3. Open `frontend/index.html` directly in your browser — double-click it, or right-click → **Open with** → your browser.

### Using the app

- **Add a member**: fill in the form at the top and click **Add member**.
- **Search**: enter an intercessor name in the Search section and click **Search**. Click **Clear** to return to the full list.
- **Edit a member**: click **Edit** in a row — the form switches to edit mode. Click **Save changes** to update, or **Cancel** to discard.
- **Delete a member**: click **Delete** in a row and confirm in the dialog.

The frontend calls the following endpoints:

| Action        | Method | Endpoint                          |
|---------------|--------|------------------------------------|
| List/search   | GET    | `/members?intercessor_name=`      |
| Get one       | GET    | `/members/{id}`                   |
| Create        | POST   | `/members`                        |
| Update        | PUT    | `/members/{id}`                   |
| Delete        | DELETE | `/members/{id}`                   |