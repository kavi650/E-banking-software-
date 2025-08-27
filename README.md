# e-bank: Frontend + Python FastAPI + MySQL backend

Run locally (no Docker, SQLite for dev):

1) Start backend
   - cd backend
   - python3 -m venv .venv && source .venv/bin/activate
   - pip install -r requirements.txt
   - export DATABASE_URL=sqlite:///./dev.db
   - uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

2) Open frontend
   - Open index.html in your browser (double-click or serve statically)
   - It calls the backend at http://localhost:8000 by default
   - If your backend is on another host/port, set window.API_BASE in the console:
     window.API_BASE = 'http://YOUR_HOST:PORT'

Run with Docker + MySQL:

1) Requirements: Docker and Docker Compose v2
2) From project root: docker compose up -d --build
3) Backend: http://localhost:8000
4) Frontend: open index.html in your browser

Seed data (on first run):
 - Users created automatically:
   - kavi: mobile 1234567890, pin 1234, account 12345678
   - arun: mobile 9876543210, pin 5678, account 87654321
   - gokul: mobile 5551234567, pin 9876, account 45678912
 - Admin: id admin, password a123

Notes:
 - UI/UX unchanged; only JS now calls backend APIs
 - Endpoints documented at /docs when backend is running