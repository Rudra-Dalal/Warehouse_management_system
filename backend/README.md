# Whitfield Fulfillment WMS Backend

Centralized Warehouse Management System (WMS) FastAPI backend for Whitfield Fulfillment, operating fixed warehouses in **Reno, NV** and **Columbus, OH**.

---

## 1. Architecture Overview

The application follows the **EIGI FastAPI Architecture Standard**:

```text
HTTP Request
     ↓
Authentication / Authorization Dependencies
     ↓
API Routers (thin routes, request/response models)
     ↓
Controllers (business logic, security rules, orchestration)
     ↓
CRUD Wrappers (PyMongo Async database access)
     ↓
Models / Database (MongoDB collections & indexes)
```

---

## 2. Authentication & Security (Phase 2)

### Authentication Flow
1. **Login**: `POST /v1/auth/login` validates credentials against stored bcrypt password hashes.
2. **Token Generation**: On success, issues a signed JWT access token containing subject claim `sub` (user_id) and expiration `exp`.
3. **Protected Requests**: Clients pass `Authorization: Bearer <access_token>` in HTTP headers.
4. **Current User Dependency**: `commons/auth.py` -> `get_current_user` extracts JWT, verifies signature/expiration, and loads the active user from MongoDB. Invalid/expired tokens return `HTTP 401 Unauthorized`.

### Role-Based Access Control (RBAC) Architecture
- **User**: Stores reference to assigned role (`role_id`).
- **Role**: Stores list of granted permission ObjectIds (`permission_ids`).
- **Permission**: Defines action strings (`inventory.read`, `users.manage`, etc.).

```text
User ──> role_id ──> Role ──> permission_ids ──> Permissions
```

- **Permission Enforcement**: `commons/auth.py` -> `require_permission("permission_name")` resolves user permissions and returns `HTTP 403 Forbidden` if denied.
- **Privilege Escalation Protection**: Users without `users.manage` permission cannot grant themselves higher roles or modify account states.

---

## 3. Initial Roles & Permissions

### Roles
- **`ADMIN`**: Full administrative access (`all permissions`).
- **`MANAGER`**: Management and operational access (`all permissions`).
- **`WAREHOUSE_STAFF`**: Operational access (`inventory.read`, `inventory.receive`, `orders.read`, `fulfillment.pick`, `fulfillment.pack`, `fulfillment.ship`).

### Permissions
- `inventory.read`
- `inventory.adjust`
- `inventory.receive`
- `orders.read`
- `orders.confirm`
- `fulfillment.pick`
- `fulfillment.pack`
- `fulfillment.ship`
- `audit.read`
- `users.manage`

---

## 4. API Endpoints

### Infrastructure
- `GET /health`: System health and MongoDB ping status.

### Authentication
- `POST /v1/auth/login`: Authenticates credentials and returns JWT bearer token.
- `GET /v1/auth/me`: Returns current user profile, role name, and granted permission list.

### User Management (`users.manage` protected)
- `GET /v1/users`: List all user accounts.
- `POST /v1/users`: Create a new user account.
- `GET /v1/users/{user_id}`: Get specific user profile.
- `PATCH /v1/users/{user_id}`: Update user profile, status, or role assignment.

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

The test suite runs against an isolated test database (`whitfield_wms_test`) and covers security unit tests, Auth API contracts, RBAC permission checks, and privilege escalation protection.

### Running Complete Test Suite
```bash
python -m pytest tests/ -v
```

### Running Specific Test Groups
```bash
# Security unit tests (bcrypt & JWT)
python -m pytest tests/unit/test_security.py -v

# Auth API tests (login, tokens, /me)
python -m pytest tests/api/test_auth_api.py -v

# RBAC authorization & privilege escalation tests
python -m pytest tests/api/test_rbac.py -v
```
