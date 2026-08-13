import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from commons.security import create_access_token, hash_password
from core.cruds.role_crud import RoleCRUD
from core.cruds.user_crud import UserCRUD
from core.models.user_model import UserModel


@pytest.mark.asyncio
async def test_rbac_authorized_user_permission():
    """Verifies that a user with 'users.manage' permission receives HTTP 200 on GET /v1/users."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin User",
        email="adminperm@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/v1/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_rbac_forbidden_lacking_permission():
    """Verifies that WAREHOUSE_STAFF lacking 'users.manage' permission receives HTTP 403 Forbidden on GET /v1/users."""
    role_crud = RoleCRUD()
    staff_role = await role_crud.get_by_name("WAREHOUSE_STAFF")

    user_crud = UserCRUD()
    staff_user = UserModel(
        name="Staff User",
        email="staffuser@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=staff_role.id,
        is_active=True,
    )
    created_staff = await user_crud.create_user(staff_user)
    token = create_access_token(subject=created_staff.id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/v1/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert "Forbidden" in response.json()["detail"]


@pytest.mark.asyncio
async def test_rbac_unauthenticated_request():
    """Verifies unauthenticated request to permission-protected endpoint returns HTTP 401 Unauthorized."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/users")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_user_cannot_escalate_privileges():
    """Verifies privilege escalation protection: WAREHOUSE_STAFF cannot assign themselves ADMIN role."""
    role_crud = RoleCRUD()
    staff_role = await role_crud.get_by_name("WAREHOUSE_STAFF")
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    staff_user = UserModel(
        name="Staff Escalation Attempt",
        email="escalate@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=staff_role.id,
        is_active=True,
    )
    created_staff = await user_crud.create_user(staff_user)
    token = create_access_token(subject=created_staff.id)

    # Attempt to elevate own role to ADMIN
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.patch(
            f"/v1/users/{created_staff.id}",
            json={"role_id": admin_role.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert "users.manage" in response.json()["detail"]

    # Verify role was NOT updated in database
    db_user = await user_crud.get_by_id(created_staff.id)
    assert db_user.role_id == staff_role.id


@pytest.mark.asyncio
async def test_staff_cannot_create_user():
    """Verifies that WAREHOUSE_STAFF without users.manage permission receives HTTP 403 when creating a user."""
    role_crud = RoleCRUD()
    staff_role = await role_crud.get_by_name("WAREHOUSE_STAFF")

    user_crud = UserCRUD()
    staff_user = UserModel(
        name="Staff User",
        email="staffcreate@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=staff_role.id,
        is_active=True,
    )
    created_staff = await user_crud.create_user(staff_user)
    token = create_access_token(subject=created_staff.id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/users",
            json={
                "name": "New User",
                "email": "newuser@example.com",
                "password": "NewUserPass123!",
                "role_id": staff_role.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_create_user():
    """Verifies that ADMIN with users.manage permission receives HTTP 201 Created when creating a user."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")
    staff_role = await role_crud.get_by_name("WAREHOUSE_STAFF")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin User",
        email="admincreate@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/users",
            json={
                "name": "New Staff Member",
                "email": "newstaff@example.com",
                "password": "NewStaffPass123!",
                "role_id": staff_role.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newstaff@example.com"
        assert data["role_id"] == staff_role.id
        assert "password_hash" not in data
