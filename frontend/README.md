# Whitfield Fulfillment — WMS Frontend

Production-quality Warehouse Management System frontend built with React, TanStack Start/Router, TanStack Query, TailwindCSS, and Lucide React. Integrated directly with the FastAPI + MongoDB replica set backend.

---

## Architecture Overview

```
React UI (Whitfield Design Language)
   ↓
React Components & Route Views
   ↓
TanStack Query (Server State Management & Caching)
   ↓
Domain API Modules (src/api/*.ts)
   ↓
Central API Client (src/api/client.ts & src/api/errors.ts)
   ↓
HTTP + JWT Authorization Header
   ↓
FastAPI Backend (/v1/*)
   ↓
Controllers / CRUD Services / PyMongo
   ↓
MongoDB Replica Set
```

The backend is the sole source of truth for all business rules, stock availability, multi-document transactions, and RBAC security.

---

## Environment Setup

Create `.env` in `frontend/` directory (or copy from `.env.example`):

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

## Development Commands

```bash
# Install dependencies
npm install

# Start local dev server (port 3000 / Vite dev)
npm run dev

# Run Vitest unit & integration test suite
npm run test

# Build for production
npm run build
```

---

## Integrated Domains

1. **Authentication:** `/login` & JWT session restoration via `POST /v1/auth/login` and `GET /v1/auth/me`.
2. **RBAC:** Role & permission checks (`ADMIN`, `WAREHOUSE_MANAGER`, `INVENTORY_CLERK`, `READ_ONLY`).
3. **Products:** Master catalog lookup, search filtering, product creation.
4. **Sellers:** Merchant accounts, active seller stats, onboarding modal.
5. **Inventory:** Real-time stock across Reno and Columbus hubs, stock adjustments with 409 conflict handling, reservations.
6. **Barcode Scanner:** Scanner gun & keyboard UPC/SKU resolution (`/v1/products/upc/{upc}`), leading-zero barcode normalization.
7. **Receiving:** Inbound shipment logs, discrepancy flags, receipt logging modal.
8. **Orders:** Full order book, status filter badges, customer order placement modal.
9. **Fulfillment:** Visual Pick-Pack-Ship pipeline with real backend state mutations (`/v1/fulfillment/pick`, `/v1/fulfillment/pack`, `/v1/fulfillment/ship`).
10. **Audit Trail:** Live audit timeline (`/v1/audit/logs`), entity filtering, prior vs. new JSON state diff inspector.
11. **Users:** Account management, role assignment, user creation modal.
12. **Dashboard:** Real-time statistics aggregated from API queries.

---

## Testing & Quality Assurance

- **Vitest Unit/Integration Tests:** 36 / 36 tests passing across 11 test modules (`npm run test`).
- **Backend Pytest Suite:** 116 / 116 tests passing against MongoDB replica set on port 27018 (`pytest tests/ -v`).
- **Production Build:** `npm run build` passes with zero errors.
