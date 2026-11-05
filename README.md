# Autonomous Legal Workflow Agent

An on-premise web platform for Indian advocates that combines case management, an evidence vault, hearing-clash detection, multi-agent AI drafting of legal documents, and a source-citing legal assistant. All AI runs locally through Ollama, so client data never leaves the machine.

Built as the TY CSE Mini Project 1 at Walchand College of Engineering, Sangli (Department of Computer Science and Engineering).

---

## Table of Contents

1. [Features](#features)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Prerequisites](#prerequisites)
5. [Setup](#setup)
6. [Configuration](#configuration)
7. [Running the Application](#running-the-application)
8. [API Overview](#api-overview)
9. [Testing](#testing)
10. [After Pulling New Changes](#after-pulling-new-changes)
11. [Troubleshooting](#troubleshooting)
12. [Known Limitations](#known-limitations)
13. [Team](#team)

---

## Features

**Accounts and security**
- Registration and login with JWT (SimpleJWT). New users always get the `lawyer` role; `admin` exists for oversight.
- Every record is filtered by the logged-in lawyer; admins can see all records.

**Case management**
- Clients, case files (open / closed / pending), citation tags and descriptions.
- Hearing calendar. A background task flags hearings of the same lawyer that fall at the same date and time with a collision warning.

**Document Vault**
- PDF upload per case, with OCR support for scanned documents (`pytesseract` + `pdf2image`).
- Whole-file SHA-256 hashing: the same file uploaded twice to one case is rejected (HTTP 409); the same file in two cases shares stored bytes but is indexed separately. Deleting a document purges its vectors and removes the file only when no other record uses it.
- Document replacement: an updated version of a document can be uploaded against the existing record (`replace_doc_id`, "Update" button in the vault). The record id is kept, and chunks are stored under content-addressed ids (`doc_<id>_chunk_<sha256-prefix>`), so only changed paragraphs are re-embedded and stale chunks are removed.

**AI Drafting Studio**
- LangGraph pipeline of three agents: Researcher, Drafter and Critic (up to three automatic revisions).
- Dual-drawer retrieval: statutes (Drawer A) and the selected case's own evidence (Drawer B) are searched separately.
- Document archetypes: legal notice, reply to notice, bail application, petition, consumer complaint, affidavit and contract, plus a custom fallback.
- Human-in-the-loop revision with a word-level diff view, a Previous Drafts panel, and export to court-formatted DOCX.
- Aadhaar and PAN numbers in generated drafts are redacted by regular expressions, not left to the model.

**AI Assistant (chat)**
- Sidebar assistant for logged-in lawyers with saved, resumable conversations and streamed answers.
- Answers are grounded in the vector database and cite their sources. If nothing relevant is found, the answer starts with a fixed notice ("I didn't find this in your database, so I'm answering based on general knowledge.") and is badged as not grounded.
- Retrieval is limited to the user's own cases (plus statutes), so one lawyer can never retrieve another's documents.
- A separate public chat widget on the login page answers from statutes only, with per-IP rate limiting.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Angular 21 (standalone components, signals), Tailwind CSS 4 |
| Backend | Django 5, Django REST Framework, SimpleJWT |
| Database | PostgreSQL |
| Background tasks | Celery (runs eagerly in development), Redis client |
| Vector database | ChromaDB (persistent, local disk) |
| Embeddings | `all-MiniLM-L6-v2` (ChromaDB default embedding function) |
| AI orchestration | LangGraph, LangChain, `langchain-ollama` |
| LLM | `llama3` served locally by Ollama |
| Documents | pypdf, pdfplumber, PyMuPDF, pytesseract, pdf2image, tiktoken, python-docx |

---

## Project Structure

```
legal-workflow-agent/
├── accounts/        User model, roles, registration/login, JWT
├── cases/           Clients, cases, hearings, documents, drafting endpoints, DOCX export
├── chat/            Conversations, messages, authenticated and public chat endpoints
├── ai_engine/       LangGraph agents, ChromaDB ingestion/retrieval, chat engine, statute seeding
├── legal_backend/   Django settings, URLs, Celery config
├── frontend/        Angular client (dashboard, vault, drafting studio, calendar, AI assistant)
├── media/           Uploaded PDFs (not committed)
├── requirements.txt Python dependencies
└── manage.py
```

`ai_engine/chroma_db/` (the vector store) and `media/` are created locally and are not part of the repository.

---

## Prerequisites

- Python 3.12
- Node.js and npm
- PostgreSQL (running locally)
- [Ollama](https://ollama.com) with the `llama3` model
- Tesseract OCR and Poppler (only for OCR of scanned PDFs):

```bash
sudo apt install tesseract-ocr poppler-utils      # Ubuntu / Debian
```

---

## Setup

### 1. Clone and create the environment

```bash
git clone https://github.com/Itssonia7/legal-workflow-agent.git
cd legal-workflow-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Local AI model

```bash
ollama list                 # check Ollama is running and llama3 is present
ollama pull llama3          # if llama3 is not listed
```

### 3. Database

Create the database, then configure `.env` (next section):

```bash
createdb legal_workflow_db -U postgres
```

### 4. Environment file

```bash
cp .env.example .env
```

Edit `.env` so `DB_PASSWORD` matches your PostgreSQL password for the `postgres` user.

### 5. Migrations

```bash
python manage.py migrate
```

### 6. Seed data

Demo lawyer, clients, cases and hearings (development only; the login is `demo_lawyer` / `demo12345`):

```bash
python manage.py seed_demo_data
```

Statute vector store (needs internet the first time, because it downloads the dataset from Hugging Face). Run it once per machine; it uses upsert, so running it again does not create duplicates:

```bash
python ai_engine/seed_statutes.py
```

> The vector store is not in git. Without this step the public chat widget cannot find any statute and will always answer from general knowledge.

### 7. Frontend

```bash
cd frontend
npm install
```

---

## Configuration

All settings are read from `.env` (copy `.env.example` as a starting point).

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | set your own |
| `DEBUG` | Django debug mode | `True` for development |
| `ALLOWED_HOSTS` | Allowed hostnames | `localhost,127.0.0.1` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL connection | `legal_workflow_db`, `postgres`, (yours), `localhost`, `5432` |
| `DISTANCE_THRESHOLD` | Relevance cut-off for retrieval (squared-L2 distance) | `1.15` |
| `PUBLIC_CHAT_THROTTLE_RATE` | Rate limit for the public chat endpoint | `20/hour` |
| `USE_SQLITE` | Use SQLite instead of PostgreSQL (for running tests only) | `False` |

The API base URLs for the frontend (`http://localhost:8000/api/...`) and the CORS origin (`http://localhost:4200`) are currently hardcoded for local development.

---

## Running the Application

Open three terminals.

**Terminal 1: Ollama** (skip if it already runs as a service)

```bash
ollama serve
```

**Terminal 2: Django backend** (http://localhost:8000)

```bash
source .venv/bin/activate
python manage.py runserver
```

**Terminal 3: Angular frontend** (http://localhost:4200)

```bash
cd frontend
npm start
```

Open http://localhost:4200, register or log in as the demo lawyer, and use the sidebar.

---

## API Overview

| Area | Endpoint | Method | Purpose |
|---|---|---|---|
| Auth | `/api/auth/register/` | POST | Register (role forced to lawyer) |
| Auth | `/api/auth/login/` | POST | Login, returns JWT and profile |
| Auth | `/api/auth/refresh/` | POST | Refresh access token |
| Cases | `/api/cases/clients/`, `/cases/`, `/schedules/` | GET, POST (+ detail routes) | Clients, case files, hearings |
| Cases | `/api/cases/documents/` | GET, DELETE | List and delete documents |
| Cases | `/api/cases/documents/upload/` | POST | Upload (or replace with `replace_doc_id`) and index a PDF |
| Cases | `/api/cases/draft/` | POST | Run the multi-agent drafting pipeline |
| Cases | `/api/cases/draft/export-docx/` | POST | Export a draft as formatted DOCX |
| Chat | `/api/chat/conversations/` | GET, POST | List and create conversations |
| Chat | `/api/chat/conversations/{id}/` | GET, PATCH, DELETE | Read, rename, delete |
| Chat | `/api/chat/conversations/{id}/send/` | POST | Send a message, streamed reply (SSE) |
| Chat | `/api/chat/public/` | POST | Public, stateless, statute-only chat |

Everything except register, login, refresh and the public chat endpoint requires a `Bearer` token.

---

## Testing

```bash
USE_SQLITE=True python manage.py test chat accounts cases
```

The suite covers login, document upload, de-duplication and cleanup, document replacement, vector isolation between two users, the statute-only public endpoint, rate limiting, owner-only access to conversations, and the exact fallback wording.

Frontend build check:

```bash
cd frontend && npm run build
```

---

## After Pulling New Changes

```bash
git checkout main
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
cd frontend && npm install
```

Run `python ai_engine/seed_statutes.py` again only if the statute data has changed.

---

## Troubleshooting

| Problem | Cause and fix |
|---|---|
| `password authentication failed for user "postgres"` | `DB_PASSWORD` in `.env` differs from the PostgreSQL password. Set it with `sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'yourpassword';"` and use the same value in `.env`. |
| `That port is already in use` (8000) | An earlier `runserver` or container is still running. Find it with `sudo ss -ltnp \| grep 8000` and stop it, or run on another port (`python manage.py runserver 8001`, which also needs the frontend base URL updated). |
| AI Assistant tab shows errors | Migrations are missing. Run `python manage.py migrate`. |
| Public chat always says it did not find anything | The statute store is empty. Run `python ai_engine/seed_statutes.py`. |
| Drafting or chat fails with a connection error | Ollama is not running, or `llama3` is not pulled. Check `ollama list`. |
| Scanned PDFs are not indexed | Install Tesseract and Poppler (see Prerequisites). |

---

## Known Limitations

- The statute store is seeded from an open Hugging Face dataset. Our audit found that several acts in it are truncated, outdated or mislabelled, and that it does not contain the Bharatiya Nyaya Sanhita, Bharatiya Nagarik Suraksha Sanhita or Bharatiya Sakshya Adhiniyam (in force since 1 July 2024). A rebuilt corpus from the enacted Acts is in progress. Until then, treat statute citations as aids and verify them against official text.
- Answers from the local `llama3` model, especially general-knowledge answers outside the database, can be wrong and must be checked by a lawyer.
- A small retrieval distance means a similar section was found, not that it answers the question.
- Celery runs in eager (synchronous) mode in development; base URLs and CORS origin are hardcoded for localhost.
- Drafting through three agents on a local model takes noticeable time, and concurrent use by many users has not been tested.

---

## Team

- Sonia Nanwani
- Sanjana Yedulwar
- Shruti Patil

Guide: Dr. B. F. Momin, Department of Computer Science and Engineering, Walchand College of Engineering, Sangli.
