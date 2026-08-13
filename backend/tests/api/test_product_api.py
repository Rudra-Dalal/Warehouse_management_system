import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from commons.security import create_access_token, hash_password
from core.cruds.role_crud import RoleCRUD
from core.cruds.seller_crud import SellerCRUD
from core.cruds.user_crud import UserCRUD
from core.models.seller_model import SellerModel
from core.models.user_model import UserModel


@pytest.mark.asyncio
async def test_product_lifecycle_sku_and_upc_string_lookups():
    """Verifies Product creation, SKU lookup, UPC barcode string lookup preserving leading zeros, and uniqueness."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Product Test",
        email="prodtest@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    # Create test Seller
    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(
        SellerModel(code="PRODUCT_SELLER", name="Product Seller Inc")
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create Product 1 with leading-zero UPC string
        res1 = await client.post(
            "/v1/products",
            json={
                "sku": "SHOE-BLACK-42",
                "name": "Black Running Shoes 42",
                "seller_id": seller.id,
                "upc": "012345678905",
                "description": "High performance shoes",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res1.status_code == 201
        p1 = res1.json()
        assert p1["sku"] == "SHOE-BLACK-42"
        assert p1["upc"] == "012345678905"  # Preserved leading zero string
        product_id = p1["id"]

        # Duplicate SKU -> 409
        res_dup_sku = await client.post(
            "/v1/products",
            json={
                "sku": "shoe-black-42",
                "name": "Duplicate SKU Shoe",
                "seller_id": seller.id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_dup_sku.status_code == 409

        # Duplicate UPC -> 409
        res_dup_upc = await client.post(
            "/v1/products",
            json={
                "sku": "SHOE-RED-42",
                "name": "Red Running Shoes 42",
                "seller_id": seller.id,
                "upc": "012345678905",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_dup_upc.status_code == 409

        # Lookup by SKU
        res_sku = await client.get(
            "/v1/products/by-sku/SHOE-BLACK-42",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_sku.status_code == 200
        assert res_sku.json()["id"] == product_id

        # Lookup by UPC with leading zero
        res_upc = await client.get(
            "/v1/products/by-upc/012345678905",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_upc.status_code == 200
        assert res_upc.json()["id"] == product_id

        # Unknown SKU -> 404
        res_nosku = await client.get(
            "/v1/products/by-sku/NONEXISTENT-SKU",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_nosku.status_code == 404

        # Unknown UPC -> 404
        res_noupc = await client.get(
            "/v1/products/by-upc/999999999999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_noupc.status_code == 404


@pytest.mark.asyncio
async def test_product_creation_invalid_seller():
    """Verifies attempting to create a product referencing a non-existent seller ID returns HTTP 404."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Test",
        email="invalidseller@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            "/v1/products",
            json={
                "sku": "SKU-BAD-SELLER",
                "name": "Bad Seller Product",
                "seller_id": "65c3b1a2f91a2b3c4d5e6f7a",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_product_upc_barcode_normalization_and_inactive():
    """Verifies that whitespace is normalized, inactive products are retrieved, and unauthenticated requests are rejected."""
    role_crud = RoleCRUD()
    admin_role = await role_crud.get_by_name("ADMIN")

    user_crud = UserCRUD()
    admin_user = UserModel(
        name="Admin Test",
        email="barcodetest@example.com",
        password_hash=hash_password("Pass123!"),
        role_id=admin_role.id,
        is_active=True,
    )
    created_admin = await user_crud.create_user(admin_user)
    token = create_access_token(subject=created_admin.id)

    seller_crud = SellerCRUD()
    seller = await seller_crud.create_seller(
        SellerModel(code="BARCODE_SELLER", name="Barcode Seller Inc")
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create an inactive product
        res_create = await client.post(
            "/v1/products",
            json={
                "sku": "INACTIVE-SKU",
                "name": "Inactive Item",
                "seller_id": seller.id,
                "upc": "000999888111",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_create.status_code == 201
        prod_id = res_create.json()["id"]

        # Deactivate it
        res_patch = await client.patch(
            f"/v1/products/{prod_id}",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_patch.status_code == 200
        assert res_patch.json()["is_active"] is False

        # Query by UPC with surrounding whitespace
        res_whitespace = await client.get(
            "/v1/products/by-upc/%20000999888111%20",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_whitespace.status_code == 200
        assert res_whitespace.json()["id"] == prod_id
        assert res_whitespace.json()["is_active"] is False

        # Query without authentication -> 401
        res_unauth = await client.get(
            "/v1/products/by-upc/000999888111",
        )
        assert res_unauth.status_code == 401

