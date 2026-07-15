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

Required environment variables:

```env
APP_NAME=CareerPilot AI API
APP_VERSION=0.1.0
FRONTEND_URL=http://localhost:5173
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GEMINI_FALLBACK_MODEL=gemini-3.1-flash-lite
```

The active AI provider for CV analysis is Gemini. OpenAI environment variables are kept for the
existing OpenAI service code, but the `/api/uploads/{upload_id}/analyze` path now uses Gemini
through the provider-independent AI service.

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

## Test an Authenticated CV Download Check

This endpoint downloads the private Storage file into backend memory and returns metadata only. It
does not return the file body.

```bash
curl -H "Authorization: Bearer ACCESS_TOKEN" \
  http://localhost:8000/api/uploads/UPLOAD_ID/download
```

## Test an Authenticated PDF Text Preview

This endpoint downloads the private PDF into backend memory, extracts readable text, and returns
only a short preview. It does not store extracted text.

```bash
curl -H "Authorization: Bearer ACCESS_TOKEN" \
  http://localhost:8000/api/uploads/UPLOAD_ID/text
```

## Run an Authenticated CV Analysis

This endpoint processes an owned PDF upload, extracts text in backend memory, calls the AI analysis
service, and stores the completed analysis metadata.

```bash
curl -X POST \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  http://localhost:8000/api/uploads/UPLOAD_ID/analyze
```

## Delete an Authenticated CV Upload

This endpoint deletes the owned `public.cv_uploads` record, related `public.cv_analyses` records,
and the private Storage file.

```bash
curl -X DELETE \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  http://localhost:8000/api/uploads/UPLOAD_ID
```

## Generate an Authenticated Career Roadmap

This endpoint creates a personalized AI career roadmap from an owned completed analysis. If an
active roadmap already exists for the same analysis, the existing roadmap is returned.

```bash
curl -X POST \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  http://localhost:8000/api/roadmaps/generate/ANALYSIS_ID
```

## Run Tests

```bash
.venv/bin/python -m pytest
```
