# Setup Instructions: RegLoop AI

This guide walks you through setting up and running the RegLoop AI prototype on your local machine. You can run it either in a local development environment (using SQLite) or in a containerized environment (using Docker Compose and PostgreSQL).

---

## Option 1: Local Development (SQLite)

This setup runs the frontend and backend as separate processes and stores data in a local SQLite file.

### Prerequisites
- **Node.js**: Version 20 or higher
- **Python**: Version 3.11 or higher
- **npm**: Version 10 or higher

### 1. Backend Setup
1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   * **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   * **macOS/Linux**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment configuration and run migrations:
   ```bash
   copy .env.example .env
   # Or on macOS/Linux: cp .env.example .env
   ```
5. Start the FastAPI server:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   The backend API will be available at `http://127.0.0.1:8000`. You can browse the OpenAPI documentation at `http://127.0.0.1:8000/docs`.

### 2. Frontend Setup
1. Open a second terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Copy the environment configuration:
   ```bash
   copy ..\.env.example .env.local
   # Or on macOS/Linux: cp ../.env.example .env.local
   ```
   *Note: Ensure `NEXT_PUBLIC_API_URL` is set to `http://localhost:8000/api`.*
3. Install node packages:
   ```bash
   npm install
   ```
4. Start the Next.js development server:
   ```bash
   npm run dev
   ```
   The application will be running at `http://localhost:3000`.

---

## Option 2: Containerized Setup (Docker Compose + PostgreSQL)

This setup packages the frontend, backend, and a PostgreSQL database into Docker containers.

### Prerequisites
- **Docker Desktop** installed and running.

### Setup and Launch
1. From the project root, configure your environment variables:
   ```bash
   copy .env.example .env
   # Or on macOS/Linux: cp .env.example .env
   ```
2. Start all services using Docker Compose:
   ```bash
   docker compose up --build
   ```
3. The services will start at the following addresses:
   * **Frontend Application**: `http://localhost:3000`
   * **Backend API**: `http://localhost:8000`
   * **Database Management (Adminer)**: `http://localhost:8080` (Run with `docker compose --profile tools up` to activate Adminer)

---

## Verifying the Installation

To verify that your installation is working correctly:
1. Navigate to `http://localhost:3000` in your web browser.
2. Click **Create New Workspace**.
3. Under the **Upload Files** section, upload the sample documents from the `/samples` folder in the project root:
   * **Regulatory Update**: `samples/regulation.pdf`
   * **Internal Policies**: `samples/compliance_monitoring_policy.pdf`, `samples/incident_reporting_policy.pdf`, `samples/records_and_audit_policy.pdf`
   * **Responsibility Matrix**: `samples/responsibility_matrix.csv`
4. Click **Run Ingestion & Analysis** and check that the obligations are successfully extracted, mapped, and audited.
5. Run the test suite:
   ```bash
   cd backend
   .venv\Scripts\pytest
   ```
