# Dividend Tracker

A simple dividend income tracker built with:

- Backend: FastAPI + yfinance + Supabase
- Frontend: React + Vite + Tailwind CSS + Recharts
- Deploy: Render (backend) + Vercel (frontend)

## Project Structure

```text
backend/   FastAPI API + Supabase schema
frontend/  React dashboard
```

## Local Setup

### Backend

1. Copy `backend/.env.example` to `backend/.env`
2. Fill in your Supabase project values
3. Run:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will run on `http://localhost:8000`.

### Frontend

1. Copy `frontend/.env.example` to `frontend/.env`
2. Run:

```bash
cd frontend
npm install
npm run dev
```

The app will run on `http://localhost:5173`.

## Supabase Setup

Run the SQL in [backend/supabase/schema.sql](/Users/santipapmay/Desktop/Dividend%20Tracker/backend/supabase/schema.sql) inside the Supabase SQL editor.

## Deploy

### Render

Recommended for automatic deploys: create a GitHub repo and connect Render to it.

Render web service settings:

- Root directory: `backend`
- Python version: handled by [backend/.python-version](/Users/santipapmay/Desktop/Dividend%20Tracker/backend/.python-version#L1)
- Blueprint config: [render.yaml](/Users/santipapmay/Desktop/Dividend%20Tracker/render.yaml#L1)
- If configuring manually:
  - Runtime: `Python`
  - Root directory: `backend`
  - Build command: `pip install -r requirements.txt`
  - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  - Health check path: `/health`

Render environment variables:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `FRONTEND_ORIGIN`

`FRONTEND_ORIGIN` should be your Vercel URL, for example `https://dividend-tracker.vercel.app`.

### Vercel

Recommended for automatic preview + production deploys: use the same GitHub repo.

Vercel project settings:

- Root directory: `frontend`
- Framework preset: `Vite`
- Build command: `npm run build`
- Output directory: `dist`
- SPA rewrites: handled by [frontend/vercel.json](/Users/santipapmay/Desktop/Dividend%20Tracker/frontend/vercel.json#L1)

Vercel environment variables:

- `VITE_API_BASE_URL`

`VITE_API_BASE_URL` should be your Render backend URL, for example `https://dividend-tracker-api.onrender.com`.

## GitHub Setup

Create one GitHub repository for this whole project. That gives you:

- Render autodeploys for the backend from `backend/`
- Vercel autodeploys for the frontend from `frontend/`
- Preview deploys on every push
- A clean path to share or keep iterating

Once the repo exists, the normal flow is:

1. Push this project to GitHub.
2. Import the repo into Render and set the service root directory to `backend`, or use the included `render.yaml`.
3. Import the same repo into Vercel and set the root directory to `frontend`.
4. Add env vars in both platforms.
5. Update `FRONTEND_ORIGIN` in Render after Vercel gives you the real frontend URL.
