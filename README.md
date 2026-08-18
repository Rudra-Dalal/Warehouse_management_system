# Whitfield Warehouse Management System (WMS)

A robust, enterprise-grade, multi-warehouse fulfillment and inventory management platform featuring live inventory control, atomic multi-item order reservation, barcode scanning, role-based access control (RBAC), an operational RAG Knowledge Center, and Voice AI operator assistance.

---

## 🏗️ Architecture Overview

The WMS follows a modern, decoupled production architecture:

```mermaid
graph TD
    Client[Web Browser / Barcode Scanner / Mobile] -->|HTTPS / WSS| VercelApp[Frontend: Vercel - TanStack Start / Vite]
    VercelApp -->|HTTPS REST API / Bearer JWT| FastApiBackend[Backend: FastAPI Python Service]
    FastApiBackend -->|PyMongo Async Driver / Replica Set| MongoAtlas[(MongoDB Atlas Database)]
    FastApiBackend -->|Gemini API / Function Calling| GeminiAI[Google GenAI / Embeddings]
```

- **Frontend (`frontend/`)**: TanStack Start + React 19 + Vite 8 deployed to **Vercel** with automatic SSR/SPA routing.
- **Backend (`backend/`)**: FastAPI + Python async runtime deployed to a container or cloud platform (Render, Railway, Fly.io, AWS App Runner).
- **Database**: **MongoDB Atlas** (M0 free tier or higher replica set) providing ACID multi-document transactions and atomic conditional updates.
- **AI & RAG**: Google Gemini (`gemini-2.5-flash` and `gemini-embedding-exp-03-07`) with deterministic fallback when AI keys are unconfigured.

---

## 💻 Local Development Setup

### Prerequisites
- Node.js 20+ and npm (or Bun / pnpm)
- Python 3.11+
- MongoDB 6.0+ (running locally or MongoDB Atlas connection string)

### 1. Backend Setup

```bash
cd backend

# Create and activate Python virtual environment
python -m venv venv
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Run FastAPI backend with hot-reload
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
Backend will be available at: `http://127.0.0.1:8000`  
API Swagger Docs: `http://127.0.0.1:8000/docs`  
Health check: `http://127.0.0.1:8000/health`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env

# Start development server
npm run dev
```
Frontend will be available at: `http://localhost:5173` (or configured dev port).

---

## ⚙️ Environment Variables Reference

### Frontend (`frontend/.env` / Vercel Environment Variables)

| Variable | Required | Description | Example |
| :--- | :---: | :--- | :--- |
| `VITE_API_BASE_URL` | **Yes** | Base URL of the deployed FastAPI backend service (no trailing slash). | `https://api.yourdomain.com` or `http://127.0.0.1:8000` |

### Backend (`backend/.env` / Cloud Backend Environment Variables)

| Variable | Required | Description | Default / Example |
| :--- | :---: | :--- | :--- |
| `MONGODB_URI` | **Yes** | MongoDB connection string (Atlas URI or local replica set). | `mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority` |
| `MONGODB_DATABASE` | **Yes** | Target database name. | `whitfield_wms` |
| `JWT_SECRET` | **Yes** | Secret key for signing and verifying JWT authentication tokens. | Secure 64-char random hex string |
| `JWT_ALGORITHM` | No | Cryptographic algorithm for JWT. | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Token lifetime in minutes. | `480` (8 hours) |
| `CORS_ORIGINS` | **Yes** | Comma-separated list of allowed frontend origins. | `http://localhost:5173,https://your-wms.vercel.app` |
| `GEMINI_API_KEY` | Optional | Google Gemini API key for live AI assistant & RAG embeddings. | Obtained from Google AI Studio |
| `ADMIN_EMAIL` | Optional | Email for initial admin user seed. | `admin@whitfield.com` |
| `ADMIN_PASSWORD` | Optional | Initial password for admin seed. | `StrongPassword123!` |
| `KNOWLEDGE_PDF_PATH` | Optional | Custom filesystem path to WMS Operations Handbook PDF. | `core/database/knowledge/wms_operations_and_knowledge_handbook.pdf` |

---

## 🍃 MongoDB Atlas Setup

Multi-item order reservations and transaction workflows in Whitfield WMS require a **transaction-capable MongoDB deployment (MongoDB Atlas or Replica Set)**.

### Step-by-Step Atlas Configuration:

1. **Create an Atlas Cluster**:
   - Log into [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
   - Create a new project (e.g., `Whitfield-WMS`).
   - Deploy a free **M0 Sandbox** cluster (or M10+ for production).
2. **Create Database User**:
   - Go to **Security** → **Database Access** → **Add New Database User**.
   - Select **Password Authentication**.
   - Assign user role: **Read and write to any database**.
   - Note down username and password securely.
3. **Configure Network Access**:
   - Go to **Security** → **Network Access** → **Add IP Address**.
   - For cloud platforms (Vercel/Render/Railway), add `0.0.0.0/0` (Allow access from anywhere) or specify your dedicated hosting egress IPs.
4. **Obtain Connection String**:
   - Go to **Databases** → **Connect** → **Drivers (Python)**.
   - Copy connection string:
     ```text
     mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority&appName=WhitfieldWMS
     ```
   - Replace `<username>` and `<password>` with the credentials created in step 2.
5. **Set in Backend Environment**:
   - Set `MONGODB_URI` to this connection string.
   - Set `MONGODB_DATABASE=whitfield_wms`.

---

## 🚀 Deployment Guide

### Deployment Architecture
- **Frontend**: Deploy `frontend/` to **Vercel**.
- **Backend**: Deploy `backend/` to **Render / Railway / Fly.io / AWS App Runner / Docker Container**.
- **Database**: **MongoDB Atlas**.

---

### Step 1: Deploy Backend (FastAPI Service)

#### Option A: Deploy on Render
1. Connect your GitHub repository to [Render](https://render.com/).
2. Create a new **Web Service**.
3. Configure the service:
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add Environment Variables:
   - `MONGODB_URI`: `<Your MongoDB Atlas URI>`
   - `MONGODB_DATABASE`: `whitfield_wms`
   - `JWT_SECRET`: `<Generate a random 64-char string>`
   - `CORS_ORIGINS`: `https://<YOUR-FRONTEND-APP>.vercel.app,http://localhost:5173`
   - `GEMINI_API_KEY`: `<Your Gemini API Key>` (optional for AI)
   - `ADMIN_EMAIL`: `admin@whitfield.com`
   - `ADMIN_PASSWORD`: `<Your secure password>`
5. Deploy and copy your live backend URL (e.g. `https://whitfield-backend.onrender.com`).

#### Option B: Deploy with Docker / Railway / Fly.io
- Build from `backend/` directory using Python 3.11+.
- Entry point: `uvicorn main:app --host 0.0.0.0 --port 8000`.

---

### Step 2: Deploy Frontend on Vercel

1. Log into [Vercel](https://vercel.com/) and click **Add New Project**.
2. Import the GitHub repository: `Warehouse_management_system`.
3. In Project Configuration:
   - **Framework Preset**: `Vite` (or `Other`)
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.vercel/output/static` (or default Build Output API)
4. Add Environment Variable:
   - `VITE_API_BASE_URL`: `https://whitfield-backend.onrender.com` (your deployed backend URL, without trailing slash)
5. Click **Deploy**.
6. Once deployed, note your Vercel URL (e.g. `https://whitfield-wms.vercel.app`) and ensure it is listed in the backend's `CORS_ORIGINS` variable.

---

## 🧪 Build & Test Verification

All automated tests and linters pass without regressions:

```bash
# Frontend Validation (51+ tests)
cd frontend
npm run lint         # 0 errors
npx tsc --noEmit     # 0 type errors
npx vitest run       # 51 passed
npm run build        # Production bundle verified

# Backend Validation (118+ tests)
cd backend
python -m pytest     # 118 passed
```

---

## ✅ Post-Deployment Smoke Test Checklist

After completing deployment, verify the following 20 core workflows:

- [ ] 1. Open deployed Vercel frontend URL in browser over HTTPS.
- [ ] 2. Login with valid credentials (`/login`).
- [ ] 3. Verify `/auth/me` resolves and user session initializes.
- [ ] 4. Dashboard loads summary metrics (inventory count, active orders, warehouses).
- [ ] 5. Warehouse selector toggles between `RENO` and `COLUMBUS`.
- [ ] 6. Products catalog loads with SKU, category, and price data (`/products`).
- [ ] 7. Sellers view loads active vendor and supplier listings (`/sellers`).
- [ ] 8. Inventory table displays stock levels, reservations, and damaged units (`/inventory`).
- [ ] 9. Receiving module displays inbound records (`/receiving`).
- [ ] 10. Orders module displays order list, customer info, and line items (`/orders`).
- [ ] 11. Fulfillment module displays pick/pack/ship workflows (`/fulfillment`).
- [ ] 12. Barcode scanner interface opens and camera/manual input responds (`/scanner`).
- [ ] 13. Audit trail records log operational movements and changes (`/audit`).
- [ ] 14. Users view displays user list and role management for `ADMIN` role (`/users`).
- [ ] 15. Knowledge Center interface opens (`/knowledge`).
- [ ] 16. RAG handbook search endpoint responds with citations or procedural fallback.
- [ ] 17. Voice AI modal opens with browser microphone permission prompt.
- [ ] 18. Voice command dispatches to `/v1/voice/command` and executes intent.
- [ ] 19. RBAC permission barriers properly restrict unauthorized routes/actions.
- [ ] 20. User logout clears tokens and redirects securely to `/login`.

---

## 📄 License & Compliance

Proprietary Warehouse Management System — Whitfield Fulfillment. All rights reserved.
