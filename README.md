# Autonomous Legal Workflow Agent (Integrated Console)

Welcome to the unified repository for the **Autonomous Legal Workflow Agent**. The individual components (Django Backend, LangGraph AI Engine, and Angular Frontend) have been integrated into a cohesive single-project workspace.

---

## 🛠️ Tech Stack & Services
* **Frontend:** Angular v21.2 & Tailwind CSS v4.0
* **Backend:** Django REST Framework, PostgreSQL, and SimpleJWT
* **RAG Vector Database:** ChromaDB & HuggingFace Embeddings (`all-MiniLM-L6-v2`)
* **Multi-Agent Orchestrator:** LangGraph & LangChain Ollama (`llama3`)

---

## ⚙️ Prerequisites & Setup

### 1. Local AI Environment (Ollama)
Ensure Ollama is installed and running on your local workstation with the `llama3` model downloaded:
```bash
# Check if Ollama is running and has llama3:
ollama list

# If llama3 is not list, pull it:
ollama pull llama3
```

### 2. Relational Database (PostgreSQL)
Ensure your local PostgreSQL database is running, and a database named `legal_workflow_db` exists:
```bash
# Log in to PostgreSQL and create the database if it doesn't exist
createdb legal_workflow_db -U postgres
```
Verify your credentials inside the `.env` file at the root of the project.

### 3. Python Virtual Environment & Migrations
We have consolidated the virtual environments. Use the root `.venv` directory for backend execution:
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations to set up cases, clients, documents, and calendar tables:
python manage.py makemigrations
python manage.py migrate
```

---

## 🚀 Running the Application

To run the full integrated suite, you will need three open terminal tabs:

### Terminal 1: Django Backend REST API & AI Service
```bash
source .venv/bin/activate
python manage.py runserver
```
The API server will boot on `http://localhost:8000/`.

### Terminal 2: Angular Frontend Web Client
```bash
cd frontend
npm start
```
The frontend portal will compile and open at `http://localhost:4200/`.

---

## 📂 Core Folder Architecture
* `/legal_backend/` - Global Django project settings and CORS configs.
* `/accounts/` - User registration, authentication, roles (`lawyer`/`admin`), and JWT tokens.
* `/cases/` - Case matter CRUD, Client intake profiles, calendar scheduling, and AI endpoint connections.
* `/ai_engine/` - Multi-agent graph nodes (Researcher, Drafter, Critic) and ChromaDB ingestion pipeline.
* `/frontend/` - Angular standalone components for Case Dashboard, Document Vault, Hearing Calendar, and AI Drafting Studio.
