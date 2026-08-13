# Whitfield Fulfillment WMS Backend

Centralized Warehouse Management System (WMS) FastAPI backend for Whitfield Fulfillment, operating fixed warehouses in **Reno, NV** and **Columbus, OH**.

---

## 1. Architecture Overview

The application follows the **EIGI FastAPI Architecture Standard**:

```text
HTTP Request
     ↓
Authentication / Authorization Dependencies (JWT & RBAC)
     ↓
API Routers (thin routes, request/response Pydantic models)
     ↓
Controllers (business logic, security rules, domain orchestration)
     ↓
CRUD Wrappers (PyMongo Async database access)
     ↓
Models / Database (MongoDB collections & indexes)
```

---

## 2. Domain Relationship (Phase 3, Phase 4 & Phase 5)

```text
    SELLER
       │
       │ seller_id
       ▼
    PRODUCT ◄─────── RECEIVING SHIPMENT (Inbound)
       │                    │
       │ product_id         │ receiving_reference (UNIQUE)
       ▼                    ▼
    INVENTORY ───> INVENTORY MOVEMENT (History)
       │
       │ warehouse_id
       ▼
    WAREHOUSE (RENO / COLUMBUS)
```

### Key Domain Rules & Invariants
1. **Warehouse Specific Inventory**: Stock is isolated per warehouse. Unique composite index `(product_id, warehouse_id)` enforces one stock record per product per warehouse.
2. **UPC String Preservation**: UPC barcode codes are stored and queried strictly as `strings` (e.g., `"012345678905"`) to preserve leading zeros. Non-empty UPCs are enforced unique via a MongoDB partial unique index.
3. **SKU Uniqueness**: SKU business codes are unique uppercase identifiers across the catalog.
4. **Inventory State & Movements**: `Inventory` documents maintain `available_quantity`, `reserved_quantity`, and `damaged_quantity`. Cycle count stock adjustments (`PATCH /v1/inventory/{id}/adjust`) log signed integer movements (`+` for increase, `-` for decrease).
5. **Atomic Inventory Reservation (Phase 4)**: Stock reservation (`POST /v1/inventory/{id}/reserve`) is performed via a **single atomic MongoDB conditional update** (`find_one_and_update`).
   - **Filter**: `{"_id": ObjectId(inventory_id), "available_quantity": {"$gte": requested_quantity}}`
   - **Update**: `{"$inc": {"available_quantity": -requested_quantity, "reserved_quantity": requested_quantity}, "$set": {"updated_at": ...}}`
   - **Concurrency Safety**: Solves race conditions without Python-level locks (`asyncio.Lock`, `threading.Lock`) or read-check-write loops. Guaranteed oversell protection: if 10 concurrent requests each attempt to reserve 9 units when only 9 units are available, **exactly 1 succeeds (200 OK)** and **exactly 9 fail (409 Conflict)**.
6. **Inbound Receiving & Strict Idempotency (Phase 5)**: Inbound inventory receiving (`POST /v1/receiving`) processes shipment receipts with strict idempotency.
   - **Database Unique Constraint**: MongoDB enforces a strict `UNIQUE(receiving_reference)` index.
   - **Zero Double-Counting**: Submitting an identical `receiving_reference` multiple times (network retries, double clicks) returns the existing `ReceivingResponse` (`HTTP 200 OK`) without double-incrementing stock or creating additional movement logs.
   - **High-Concurrency Guarantee**: If 10 concurrent requests simultaneously submit `"WH-REC-CONC-001"` (+100 units), **exactly 1 receiving shipment is created**, stock is incremented **exactly once (+100)**, and exactly 1 `RECEIVING` movement log is created.
7. **Non-Negative Stock Invariant**: `available_quantity >= 0` is strictly enforced. Adjustments or reservations exceeding available stock return `HTTP 400 Bad Request` or `HTTP 409 Conflict` respectively.

> [!NOTE]
> Orders handling is strictly deferred to **Phase 6**. Order fulfillment is deferred to **Phase 7**.

---

## 3. Security, Roles & Permissions (Phase 2, Phase 3, Phase 4 & Phase 5)

### Roles
- **`ADMIN`**: Full administrative access (`all permissions`).
- **`MANAGER`**: Management and operational access (`all permissions`).
- **`WAREHOUSE_STAFF`**: Operational warehouse access (`inventory.read`, `inventory.reserve`, `inventory.receive`, `orders.read`, `fulfillment.pick`, `fulfillment.pack`, `fulfillment.ship`, `products.read`, `sellers.read`).

### Permissions List
- `users.manage`: User account administration
- `sellers.read`: View seller profile details
- `sellers.manage`: Create and update seller accounts
- `products.read`: View product catalog items, lookup by SKU/UPC
- `products.manage`: Create and update product catalog definitions
- `inventory.read`: View warehouse stock levels and movement history
- `inventory.adjust`: Create initial inventory and adjust stock levels
- `inventory.reserve`: Atomically reserve available inventory stock for orders
- `inventory.receive`: Receive inbound stock shipments (Phase 5)
- `orders.read` / `orders.confirm`: Orders handling (Phase 6)
- `fulfillment.pick` / `fulfillment.pack` / `fulfillment.ship`: Order fulfillment (Phase 7)
- `audit.read`: View system audit logs

---

## 4. API Endpoints Summary

### Infrastructure
- `GET /health`: System health and MongoDB ping status.

### Authentication & Self Services
- `POST /v1/auth/login`: Authenticate credentials and receive JWT bearer token.
- `GET /v1/auth/me`: Retrieve current authenticated user profile and permissions.

### User Management (`users.manage`)
- `GET /v1/users`: List all user accounts.
- `POST /v1/users`: Create user account.
- `GET /v1/users/{user_id}`: Get specific user details.
- `PATCH /v1/users/{user_id}`: Update user details or role.

### Seller Management (`sellers.read`, `sellers.manage`)
- `GET /v1/sellers`: List e-commerce sellers.
- `POST /v1/sellers`: Register a new seller.
- `GET /v1/sellers/{seller_id}`: Get seller details.
- `PATCH /v1/sellers/{seller_id}`: Update seller profile.

### Product Catalog (`products.read`, `products.manage`)
- `GET /v1/products`: List products (optional `seller_id` filter).
- `POST /v1/products`: Create a product item (validates `seller_id`, unique `sku`, and string `upc`).
- `GET /v1/products/by-sku/{sku}`: Lookup product by unique SKU.
- `GET /v1/products/by-upc/{upc}`: Resolve product by UPC string (preserves leading zeros).
- `GET /v1/products/{product_id}`: Get product details.
- `PATCH /v1/products/{product_id}`: Update product metadata or UPC string.

### Inventory State & Atomic Reservation (`inventory.read`, `inventory.adjust`, `inventory.reserve`)
- `GET /v1/inventory`: List stock levels (filters: `warehouse_code`, `sku`, `product_id`).
- `POST /v1/inventory`: Register initial stock for a product at a warehouse.
- `GET /v1/inventory/{inventory_id}`: Get inventory record state.
- `PATCH /v1/inventory/{inventory_id}/adjust`: Cycle count adjustment (+/- signed delta, logs movement & user).
- `POST /v1/inventory/{inventory_id}/reserve`: Atomically reserve stock (`quantity > 0`). Returns 200 OK on success, 409 Conflict if stock is insufficient, 404 if inventory ID does not exist. Logs `RESERVATION` movement with signed `quantity = -requested_quantity`.
- `GET /v1/inventory/{inventory_id}/movements`: Get historical movement logs for an inventory item.

### Inbound Receiving & Idempotency (`inventory.receive`, `inventory.read`)
- `POST /v1/receiving`: Receive inbound inventory shipment (single/multi-product). Enforces `UNIQUE(receiving_reference)`. Duplicate requests return existing result (`200 OK`) without double-counting stock.
- `GET /v1/receiving`: List receiving shipments (optional `warehouse_code` or `seller_id` filters).
- `GET /v1/receiving/{receiving_id}`: Get detailed receiving shipment information.

---

## 5. Environment Configuration

Create a `.env` file in `backend/`:

```env
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=whitfield_wms
JWT_SECRET=supersecretkey_change_in_production_123456789
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# Optional Development Admin Seed Credentials
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=AdminSecurePassword123!
```

---

## 6. Setup & Running

### Installation
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### Running Server
```bash
uvicorn main:app --reload --port 8000
```

OpenAPI docs will be available at `http://localhost:8000/docs`.

---

## 7. Testing Strategy & Instructions

The test suite executes against an isolated test database (`whitfield_wms_test`) and validates infrastructure, security, auth API, RBAC, sellers, products, UPC string preservation, warehouse stock isolation, inventory adjustments, atomic reservation APIs, inbound receiving idempotency, and deterministic concurrency safety.

### Running Complete Test Suite (46 / 46 Tests)
```bash
python -m pytest tests/ -v
```

### Running Specific Test Categories
```bash
# Infrastructure & Seeding
python -m pytest tests/unit/test_milestone1.py -v

# Security Unit Tests (bcrypt & JWT)
python -m pytest tests/unit/test_security.py -v

# Authentication API Tests
python -m pytest tests/api/test_auth_api.py -v

# RBAC & Privilege Escalation Tests
python -m pytest tests/api/test_rbac.py -v

# Seller API Tests
python -m pytest tests/api/test_seller_api.py -v

# Product Catalog & UPC String Lookup Tests
python -m pytest tests/api/test_product_api.py -v

# Warehouse Inventory & Movement Log Tests
python -m pytest tests/api/test_inventory_api.py -v

# Reservation API Integration Tests
python -m pytest tests/api/test_reservation_api.py -v

# Reservation Concurrency Safety Tests (10x simultaneous reservation requests)
python -m pytest tests/concurrency/test_concurrent_reservation.py -v

# Receiving API Integration & Idempotency Tests
python -m pytest tests/api/test_receiving_api.py -v

# Receiving Concurrency & Duplicate Protection Tests (10x simultaneous duplicate shipments)
python -m pytest tests/concurrency/test_concurrent_receiving.py -v
```
