# CareerPilot AI - Software Architecture

> Version: 1.0  
> Status: Draft  
> Last Updated: July 9, 2026  
> Owner: Selcan Aktürk

---

# Overview

CareerPilot AI is built as a modern AI-powered SaaS application using a decoupled frontend and backend architecture.

The frontend communicates with a FastAPI backend through REST APIs. Authentication, database, and file storage are managed by Supabase. AI-powered analysis is generated using the OpenAI API.

This architecture keeps the application modular, scalable, and easy to maintain.

---

# High-Level Architecture

```text
                +----------------------+
                |      React App       |
                | (TypeScript + Vite)  |
                +----------+-----------+
                           |
                           | HTTPS / REST API
                           |
                           ▼
                +----------------------+
                |       FastAPI        |
                |   Business Logic     |
                +----------+-----------+
                           |
        +------------------+------------------+
        |                  |                  |
        ▼                  ▼                  ▼
+----------------+  +----------------+  +----------------+
| Supabase Auth  |  | Supabase DB    |  | OpenAI API     |
+----------------+  +----------------+  +----------------+
                           |
                           ▼
                 +----------------------+
                 | Supabase Storage     |
                 | (Resume PDFs)        |
                 +----------------------+
```

---

# Technology Stack

## Frontend

- React
- TypeScript
- Vite
- TailwindCSS
- React Router

---

## Backend

- Python
- FastAPI
- Pydantic
- Uvicorn

---

## Database

- Supabase PostgreSQL

---

## Authentication

- Supabase Auth

---

## Storage

- Supabase Storage

Stores:

- Resume PDFs
- Future exported reports

---

## AI

- OpenAI API

Responsible for:

- Resume analysis
- Skill gap detection
- Career readiness score
- CV suggestions
- Personalized roadmap
- Interview question generation

---

# System Components

## Frontend

Responsible for:

- Authentication UI
- Dashboard
- CV Upload
- Analysis Results
- History
- Profile

The frontend never communicates directly with OpenAI.

---

## Backend

Responsible for:

- Business logic
- Resume processing
- Prompt generation
- AI communication
- Database operations
- Authorization
- File validation

---

## Database

Stores:

- User profiles
- Uploaded resumes
- Analysis history
- Roadmaps
- Interview questions

---

## Storage

Stores uploaded PDF resumes.

The database only stores metadata and file URLs.

---

## AI Layer

The backend sends structured prompts to OpenAI.

OpenAI never communicates directly with the frontend.

---

# Request Flow

## User uploads a resume

```text
User

↓

React

↓

FastAPI

↓

Supabase Storage

↓

Database

↓

OpenAI Analysis

↓

Database

↓

React

↓

Analysis Result
```

---

# Security

Authentication

- Supabase Auth
- JWT-based authentication

Authorization

Every request requiring user data must validate the authenticated user.

Files

- Only authenticated users can upload resumes.
- PDF only.
- File size limits will be enforced.

---

# Scalability

The architecture is designed to support future features without major restructuring.

Potential future additions:

- LinkedIn integration
- Cover Letter Generator
- AI Chat Assistant
- Voice Interviews
- Company-specific interview preparation
- ATS Score Analysis

---

# Design Principles

The system follows these principles:

- Separation of Concerns
- Modular Architecture
- Reusable Components
- Secure by Default
- API-first Design
- AI as a Service
- Scalable Infrastructure

---

# Future Improvements

- Background job queue
- Resume versioning
- AI conversation history
- Multi-language support
- Real-time notifications
- Analytics dashboard
