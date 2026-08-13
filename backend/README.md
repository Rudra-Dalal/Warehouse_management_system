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

## 2. Domain Relationship (Phase 3)

```text
    SELLER
       │
       │ seller_id
       ▼
    PRODUCT
       │
       │ product_id
       ▼
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
4. **Inventory State & Movements**: `Inventory` documents maintain `available_quantity`, `reserved_quantity` (Phase 4 placeholder), and `damaged_quantity`. Cycle count stock adjustments (`PATCH /v1/inventory/{id}/adjust`) log signed integer movements (`+` for increase, `-` for decrease) in a separate `inventory_movements` collection and record `user_id`.
5. **Non-Negative Stock Invariant**: `available_quantity >= 0` is strictly enforced. Adjustments resulting in negative stock are rejected with `HTTP 400 Bad Request`.

> [!NOTE]
> Inventory reservation & concurrency logic is strictly deferred to **Phase 4**. Receiving workflows are deferred to **Phase 5**.

---

## 3. Security, Roles & Permissions (Phase 2 & Phase 3)

### Roles
- **`ADMIN`**: Full administrative access (`all permissions`).
- **`MANAGER`**: Management and operational access (`all permissions`).
- **`WAREHOUSE_STAFF`**: Operational warehouse access (`inventory.read`, `inventory.receive`, `orders.read`, `fulfillment.pick`, `fulfillment.pack`, `fulfillment.ship`, `products.read`, `sellers.read`).

### Permissions List
- `users.manage`: User account administration
- `sellers.read`: View seller profile details
- `sellers.manage`: Create and update seller accounts
- `products.read`: View product catalog items, lookup by SKU/UPC
- `products.manage`: Create and update product catalog definitions
- `inventory.read`: View warehouse stock levels and movement history
- `inventory.adjust`: Create initial inventory and adjust stock levels
- `inventory.receive`: Receive stock shipments (Phase 5)
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

### Inventory State & Movements (`inventory.read`, `inventory.adjust`)
- `GET /v1/inventory`: List stock levels (filters: `warehouse_code`, `sku`, `product_id`).
- `POST /v1/inventory`: Register initial stock for a product at a warehouse.
- `GET /v1/inventory/{inventory_id}`: Get inventory record state.
- `PATCH /v1/inventory/{inventory_id}/adjust`: Cycle count adjustment (+/- signed delta, logs movement & user).
- `GET /v1/inventory/{inventory_id}/movements`: Get historical movement logs for an inventory item.

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

The test suite executes against an isolated test database (`whitfield_wms_test`) and validates infrastructure, security, auth API, RBAC, sellers, products, UPC string preservation, warehouse stock isolation, and inventory adjustments.

### Running Complete Test Suite (28 / 28 Tests)
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
```
