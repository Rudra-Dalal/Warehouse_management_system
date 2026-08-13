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
Services (InventoryReservationService for shared reservation logic)
     ↓
CRUD Wrappers (PyMongo Async database access)
     ↓
Models / Database (MongoDB collections & indexes)
```

---

## 2. Domain Relationship (Phase 3, Phase 4, Phase 5 & Phase 6)

```text
    SELLER
       │
       ├─── seller_id ───> ORDER (Customer Order)
       ▼                     │
    PRODUCT ◄────────────────┼─── order_number (UNIQUE)
       │                     ▼
       │ product_id       INVENTORY RESERVATION SERVICE
       ▼                     │
    INVENTORY ───────────────┼───> INVENTORY MOVEMENT (RESERVATION)
       │                     │
       │ warehouse_id        ▼
       ▼                  CONFIRMED ORDER
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
7. **Order Management & Transaction-Backed Multi-Item Atomicity (Phase 6)**: Order creation (`POST /v1/orders`) validates seller, warehouse, and products, then reserves inventory across all line items using `InventoryReservationService`.
   - **Transaction Requirement**: Multi-item order creation requires a **transaction-capable MongoDB deployment (Replica Set or Atlas)**. The entire workflow (`reserve inventory -> log movements -> insert order`) executes inside a single MongoDB transaction (`client.start_session()` + `start_transaction()`).
   - **Session Propagation**: The transaction session propagates from `OrderController` $\rightarrow$ `InventoryReservationService` $\rightarrow$ `InventoryCRUD.reserve_inventory_atomic(..., session=session)` $\rightarrow$ `InventoryMovementCRUD.create_movement(..., session=session)`.
   - **All-or-Nothing Multi-Item Transaction Rollback**: If any line item in an order fails reservation (insufficient stock, invalid product) or if order creation fails, **MongoDB aborts the transaction**, automatically rolling back all inventory changes and movement logs in database state (`HTTP 409 Conflict`). Zero manual compensation code or partial reservations occur.
   - **Order Idempotency**: MongoDB enforces `UNIQUE(order_number)`. Resubmitting an existing `order_number` returns the existing confirmed order (`HTTP 200 OK`) without double-reserving inventory or creating duplicate movement logs.
8. **Fulfillment Execution & State Machine (Phase 7)**: Operational execution of a confirmed order follows a strict state machine: `READY_TO_PICK` $\rightarrow$ `PICKED` $\rightarrow$ `PACKED` $\rightarrow$ `SHIPPED`.
   - **One Fulfillment Per Order**: MongoDB enforces a strict `UNIQUE(order_id)` index on the `fulfillments` collection. Submitting `POST /v1/fulfillment` multiple times for the same order returns the existing record idempotently.
   - **Picking Consumes Reservation (Zero Double-Decrement)**: Order creation (Phase 6) already decremented `available_quantity` and incremented `reserved_quantity`. Picking (`POST /v1/fulfillment/{id}/pick`) **consumes the reservation**: `reserved_quantity -= picked_quantity`. **Available quantity is NOT decremented again during picking** (`available=90`, `reserved=10` $\rightarrow$ after pick: `available=90`, `reserved=0`).
   - **Transactional Picking & Shipping**: Picking updates inventory reservations, records `PICK` movement logs (`movement_type = "PICK"`), and updates status inside a single MongoDB transaction. Shipping (`POST /v1/fulfillment/{id}/ship`) updates fulfillment and order statuses to `SHIPPED` inside a single MongoDB transaction.
   - **Invalid Transition Protection**: Invalid state transitions (e.g. `READY_TO_PICK` $\rightarrow$ `PACKED` or `SHIPPED`) return `HTTP 409 Conflict`.
9. **Non-Negative Stock Invariant**: `available_quantity >= 0` and `reserved_quantity >= 0` are strictly enforced.

---

## 3. Security, Roles & Permissions

### Roles
- **`ADMIN`**: Full administrative access (`all permissions`).
- **`MANAGER`**: Management and operational access (`all permissions`).
- **`WAREHOUSE_STAFF`**: Operational warehouse access (`inventory.read`, `inventory.reserve`, `inventory.receive`, `orders.read`, `orders.confirm`, `fulfillment.read`, `fulfillment.pick`, `fulfillment.pack`, `fulfillment.ship`, `products.read`, `sellers.read`).

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
- `orders.read`: View customer order details and order listing (Phase 6)
- `orders.confirm`: Create and confirm customer orders with atomic stock reservation (Phase 6)
- `fulfillment.read`: View operational fulfillment records and details (Phase 7)
- `fulfillment.pick`: Perform pick tasks and consume reservations (Phase 7)
- `fulfillment.pack`: Perform packing operations (Phase 7)
- `fulfillment.ship`: Finalize order shipping (Phase 7)
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

### Customer Order Management (`orders.confirm`, `orders.read`)
- `POST /v1/orders`: Create and confirm customer order (single/multi-product). Atomically reserves stock across all line items under all-or-nothing semantics. Enforces `UNIQUE(order_number)` idempotency.
- `GET /v1/orders`: List customer orders (optional `warehouse_code`, `seller_id`, or `status` filters).
- `GET /v1/orders/{order_id}`: Get detailed order information.

---

## 5. Environment Configuration

Create a `.env` file in `backend/`:

```env
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=whitfield_wms
JWT_SECRET=replace-with-a-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# Optional Development Admin Seed Credentials
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=replace-with-a-local-admin-password
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

The test suite executes against an isolated test database (`whitfield_wms_test`) and validates infrastructure, security, auth API, RBAC, sellers, products, UPC string preservation, warehouse stock isolation, inventory adjustments, atomic reservation APIs, inbound receiving idempotency, customer order management, and deterministic concurrency safety.

### Running Complete Test Suite (56 / 56 Tests)
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

# Customer Order API Integration Tests
python -m pytest tests/api/test_order_api.py -v

# Customer Order Concurrency Safety Tests (10x simultaneous order requests)
python -m pytest tests/concurrency/test_concurrent_orders.py -v
```

---

## 8. Command Line Interface (Phase 9 CLI)

The project includes a thin, scriptable Command Line Interface (CLI) that enables warehouse operators to manage inventory, products, orders, fulfillment tasks, and audit logs.

### Key Architecture Rules
- **HTTP Communication Only**: The CLI communicates strictly with the FastAPI backend over HTTP using Python's standard `urllib` library.
- **No Direct Database Access**: The CLI **never** connects to MongoDB directly, imports database CRUD classes, or runs backend controllers.
- **RBAC Enforcement**: All authorization and validation rules are executed and enforced on the FastAPI backend.

### Setup & Base URL Configuration

The CLI defaults to communicating with `http://127.0.0.1:8000`. You can configure this base URL using the `WMS_API_BASE_URL` environment variable:

```bash
# On Linux/macOS
export WMS_API_BASE_URL="http://127.0.0.1:8000"

# On Windows (PowerShell)
$env:WMS_API_BASE_URL="http://127.0.0.1:8000"
```

### Session State & Authentication

The CLI supports persistent login sessions across commands:
1. **Local Persistent Cache**: Log in to cache the JWT token locally at `~/.wms_session.json` (outside the repository folder).
2. **Environment Variable Override**: You can also supply the token dynamically via the `WMS_TOKEN` environment variable.
3. **Session Removal**: Logging out deletes `~/.wms_session.json` safely.

### Commands Reference

Run the help command to see all commands and subcommands:
```bash
python -m cli --help
```

#### Authentication
```bash
# Log in and cache JWT token
python -m cli login

# View current user identity
python -m cli whoami

# Clear token and log out
python -m cli logout
```

#### Service Health
```bash
python -m cli health
```

#### Inventory Management
```bash
# List stock levels (filters: --warehouse-code, --sku, --product-id)
python -m cli inventory list --warehouse-code RENO

# Get details of a specific inventory item
python -m cli inventory get <inventory_id>

# Adjust available stock with signed delta (and optional note)
python -m cli inventory adjust <inventory_id> --quantity -5 --note "Cycle count"

# Reserve available stock
python -m cli inventory reserve <inventory_id> --quantity 10

# List stock movements
python -m cli inventory movements <inventory_id>
```

#### Product Catalog
```bash
# List catalog products (filter: --seller-id)
python -m cli products list

# Get details of a specific product
python -m cli products get <product_id>

# Lookup product by SKU
python -m cli products sku <sku>

# Lookup product by UPC (preserves leading zeros as string)
python -m cli products upc 012345678905

# MVP Scan lookup (string barcode emulation)
python -m cli products scan 012345678905
```

#### Inbound Receiving
```bash
# List inbound shipments
python -m cli receiving list

# Get shipment details
python -m cli receiving get <receiving_id>

# Create inbound receiving shipment (items formatted as product_id:quantity)
python -m cli receiving create --reference REC-100 --warehouse-code COLUMBUS --seller-id <seller_id> --items prod1:50,prod2:100
```

#### Customer Orders
```bash
# List customer orders
python -m cli orders list

# Get order details
python -m cli orders get <order_id>

# Create and confirm order (items formatted as product_id:quantity)
python -m cli orders create --order-number ORD-200 --warehouse-code RENO --seller-id <seller_id> --items prod1:5,prod2:10
```

#### Fulfillment Tasks
```bash
# List fulfillment tasks
python -m cli fulfillment list

# Get fulfillment details
python -m cli fulfillment get <fulfillment_id>

# Create fulfillment task
python -m cli fulfillment create --order-id <order_id>

# Pick items for fulfillment task
python -m cli fulfillment pick <fulfillment_id> --items prod1:5,prod2:10

# Pack fulfillment task
python -m cli fulfillment pack <fulfillment_id> --note "Packed in Medium Box"

# Ship fulfillment task
python -m cli fulfillment ship <fulfillment_id> --tracking TRK987654321
```

#### Audit Logs
```bash
# List audit logs with pagination and filters
python -m cli audit list --action CREATE --entity-type PRODUCT --limit 10

# Get detailed audit log
python -m cli audit get <audit_id>

# Get audit history for specific entity
python -m cli audit entity PRODUCT <product_id>

# Get audit history for specific user
python -m cli audit user <user_id>
```

### Running CLI Unit Tests

Run the CLI integration and mock tests via pytest:
```bash
python -m pytest tests/cli/ -v
```

---

## 9. Phase 10 – Barcode / UPC Scanning MVP

This phase implements a reusable, keyboard-emulated Barcode and UPC Scanning MVP workflow built on top of the WMS CLI and FastAPI backend.

### Architecture Flow
```
Barcode Input (Single Scan / Interactive loop)
         ↓
Normalization (Whitespace trimmed, leading zeros preserved, empty rejected)
         ↓
HTTP Product Resolution (GET /v1/products/by-upc/{upc})
         ↓
HTTP Inventory Lookup (GET /v1/inventory?product_id={product_id})
         ↓
Display Product details + stock levels at RENO and COLUMBUS
```

### Key Highlights & Features
- **Strict String Preserves**: Barcodes are treated strictly as strings to prevent truncation of leading zeros.
- **Normalization Utility**: The `normalize_barcode(barcode: str) -> str` utility trims leading/trailing whitespace, validates non-emptiness, and guarantees uniform input representation across the system.
- **Unified APIs**: The existing `GET /v1/products/by-upc/{upc}` endpoint is reused and backed by `BarcodeService` to resolve normalized UPC queries, keeping API layers DRY.
- **Inventory Integration**: After product resolution, the CLI automatically makes a second API request to fetch and display the product's real-time inventory counts at `RENO` and `COLUMBUS`.
- **Single Scan Command**: Operators can run a single lookup:
  ```bash
  python -m cli products scan 012345678905
  ```
- **Interactive Scan Mode**: Running the command without arguments launches an interactive loop:
  ```bash
  python -m cli products scan
  ```
  This is fully compatible with standard USB/Bluetooth barcode scanners operating in keyboard-emulation mode. Operators can scan multiple barcodes sequentially and exit cleanly by typing `q` or pressing `Ctrl+C` (without raw Python tracebacks).
- **Error & Status Handling**:
  - **404 Not Found**: Clearly states when a barcode isn't registered, instructing the operator to verify product master data.
  - **Inactive Products**: Clearly displays when a resolved product has a status of `INACTIVE`.
- **RBAC Enforcement**: The workflow executes over backend endpoints secured by `products.read` and `inventory.read` permissions, ensuring RBAC and security remains intact.
- **Disclaimer**: Phase 10 does not implement physical barcode hardware, camera scanning, OCR, or image recognition.

