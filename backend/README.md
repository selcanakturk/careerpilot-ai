# CareerPilot AI API

FastAPI backend starter for CareerPilot AI.

## Create a Virtual Environment

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Configure Environment Variables

```bash
cp .env.example .env
```

Fill in real secret values only in `.env`. Do not commit `.env`.

## Run the Backend

```bash
uvicorn app.main:app --reload
```

The API will run at:

```text
http://127.0.0.1:8000
```

## Test the Health Endpoint

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "CareerPilot AI API",
  "version": "0.1.0"
}
```

## Test an Authenticated Upload Lookup

Use a Supabase access token from an authenticated user session and a CV upload id that belongs to
that user.

```bash
curl -H "Authorization: Bearer ACCESS_TOKEN" \
  http://localhost:8000/api/uploads/UPLOAD_ID
```

The endpoint returns metadata from `public.cv_uploads` only when the authenticated user owns the
upload record.

## Run Tests

```bash
pytest
```
