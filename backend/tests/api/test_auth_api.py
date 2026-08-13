from datetime import timedelta
import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from commons.security import create_access_token, hash_password
from core.cruds.role_crud import RoleCRUD
from core.cruds.user_crud import UserCRUD
from core.models.user_model import UserModel


@pytest.mark.asyncio
async def test_successful_login():
    """Verifies POST /v1/auth/login returns HTTP 200 and access_token for valid credentials."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    test_user = UserModel(
        name="Test User",
        email="testlogin@example.com",
        password_hash=hash_password("ValidPass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    await user_crud.create_user(test_user)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/auth/login",
            json={"email": "testlogin@example.com", "password": "ValidPass123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password():
    """Verifies POST /v1/auth/login returns HTTP 401 Unauthorized for incorrect password."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    test_user = UserModel(
        name="Test User",
        email="wrongpass@example.com",
        password_hash=hash_password("ValidPass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    await user_crud.create_user(test_user)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/auth/login",
            json={"email": "wrongpass@example.com", "password": "WrongPassword!"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_unknown_email():
    """Verifies POST /v1/auth/login returns HTTP 401 Unauthorized for unknown email."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/auth/login",
            json={"email": "unknown@example.com", "password": "SomePassword123!"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_inactive_user():
    """Verifies POST /v1/auth/login returns HTTP 401 Unauthorized for disabled user account."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    test_user = UserModel(
        name="Inactive User",
        email="inactive@example.com",
        password_hash=hash_password("ValidPass123!"),
        role_id=admin_role.id,
        is_active=False,
    )
    await user_crud.create_user(test_user)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/auth/login",
            json={"email": "inactive@example.com", "password": "ValidPass123!"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "User account is disabled"


@pytest.mark.asyncio
async def test_get_me_with_valid_token():
    """Verifies GET /v1/auth/me returns HTTP 200 and user metadata with assigned permissions."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    test_user = UserModel(
        name="Me User",
        email="meuser@example.com",
        password_hash=hash_password("ValidPass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_user = await user_crud.create_user(test_user)
    token = create_access_token(subject=created_user.id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "meuser@example.com"
        assert data["role"] == "ADMIN"
        assert "users.manage" in data["permissions"]
        assert "password_hash" not in data


@pytest.mark.asyncio
async def test_get_me_without_token():
    """Verifies GET /v1/auth/me returns HTTP 401 Unauthorized when missing Authorization header."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/auth/me")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_invalid_token():
    """Verifies GET /v1/auth/me returns HTTP 401 Unauthorized for malformed/invalid token."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/v1/auth/me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_expired_token():
    """Verifies GET /v1/auth/me returns HTTP 401 Unauthorized for expired JWT token."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    test_user = UserModel(
        name="Expired User",
        email="expired@example.com",
        password_hash=hash_password("ValidPass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_user = await user_crud.create_user(test_user)
    expired_token = create_access_token(
        subject=created_user.id,
        expires_delta=timedelta(seconds=-10),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401
