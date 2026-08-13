from bson import ObjectId
from commons.logger import get_logger
from commons.security import hash_password
from core.config import settings
from core.cruds.permission_crud import PermissionCRUD
from core.cruds.role_crud import RoleCRUD
from core.cruds.user_crud import UserCRUD
from core.models.permission_model import PermissionModel
from core.models.role_model import RoleModel
from core.models.user_model import UserModel

logger = get_logger(__name__)


async def seed_rbac_data() -> None:
    """Idempotently seeds initial permissions, security roles, and optional dev admin user.
    Ensures re-running seed operations never creates duplicate permissions or roles.
    """
    logger.info("Executing seed_rbac_data")
    permission_crud = PermissionCRUD()
    role_crud = RoleCRUD()
    user_crud = UserCRUD()

    # Initial Permissions List
    initial_permissions = [
        {"name": "inventory.read", "description": "Read inventory quantities and stock levels"},
        {"name": "inventory.adjust", "description": "Adjust stock levels and damaged quantities"},
        {"name": "inventory.reserve", "description": "Reserve available inventory for orders"},
        {"name": "inventory.receive", "description": "Receive new stock shipments"},
        {"name": "orders.read", "description": "Read order details and status"},
        {"name": "orders.confirm", "description": "Confirm orders and reserve inventory"},
        {"name": "fulfillment.read", "description": "Read fulfillment details and status"},
        {"name": "fulfillment.pick", "description": "Perform pick tasks"},
        {"name": "fulfillment.pack", "description": "Perform packing operations"},
        {"name": "fulfillment.ship", "description": "Ship orders and assign tracking"},
        {"name": "audit.read", "description": "Read system audit log records"},
        {"name": "users.manage", "description": "Manage user accounts and role assignments"},
        {"name": "sellers.read", "description": "Read seller details"},
        {"name": "sellers.manage", "description": "Manage seller accounts and profiles"},
        {"name": "products.read", "description": "Read product catalog details"},
        {"name": "products.manage", "description": "Manage products and SKU definitions"},
    ]

    permission_map = {}
    for p_data in initial_permissions:
        existing = await permission_crud.get_by_name(p_data["name"])
        if not existing:
            new_perm = await permission_crud.create_permission(PermissionModel(**p_data))
            permission_map[p_data["name"]] = new_perm.id
            logger.info(f"Seeded permission: {p_data['name']}")
        else:
            permission_map[p_data["name"]] = existing.id

    all_perm_ids = list(permission_map.values())
    staff_perm_names = [
        "inventory.read",
        "inventory.reserve",
        "inventory.receive",
        "orders.read",
        "fulfillment.read",
        "fulfillment.pick",
        "fulfillment.pack",
        "fulfillment.ship",
        "audit.read",
        "products.read",
        "sellers.read",
    ]
    staff_perm_ids = [permission_map[name] for name in staff_perm_names if name in permission_map]
    readonly_perm_names = [
        "inventory.read",
        "orders.read",
        "fulfillment.read",
        "audit.read",
        "products.read",
        "sellers.read",
    ]
    readonly_perm_ids = [permission_map[name] for name in readonly_perm_names if name in permission_map]

    # Initial Roles Definition
    roles_definitions = [
        {"name": "ADMIN", "description": "System Administrator with unrestricted access", "permission_ids": all_perm_ids},
        {"name": "MANAGER", "description": "Warehouse Manager with operational and management access", "permission_ids": all_perm_ids},
        {"name": "WAREHOUSE_STAFF", "description": "Warehouse Staff with operational access", "permission_ids": staff_perm_ids},
        {"name": "READ_ONLY", "description": "Read-only access to operations and data", "permission_ids": readonly_perm_ids},
    ]

    admin_role_id = None
    for r_data in roles_definitions:
        existing_role = await role_crud.get_by_name(r_data["name"])
        if not existing_role:
            new_role = await role_crud.create_role(RoleModel(**r_data))
            if r_data["name"] == "ADMIN":
                admin_role_id = new_role.id
            logger.info(f"Seeded security role: {r_data['name']}")
        else:
            if r_data["name"] == "ADMIN":
                admin_role_id = existing_role.id
            # Sync new permissions to existing roles
            existing_perm_ids = set(existing_role.permission_ids)
            target_perm_ids = set(r_data["permission_ids"])
            if existing_perm_ids != target_perm_ids:
                updated_perm_ids = list(existing_perm_ids | target_perm_ids)
                await role_crud.collection.update_one(
                    {"_id": ObjectId(existing_role.id)},
                    {"$set": {"permission_ids": updated_perm_ids}},
                )

    # Seed Default WMS Accounts
    default_accounts = [
        ("admin@whitfield.com", "Admin123!", "System Administrator", "ADMIN"),
        ("manager@whitfield.com", "Manager123!", "Warehouse Manager", "MANAGER"),
        ("clerk@whitfield.com", "Clerk123!", "Inventory Clerk", "WAREHOUSE_STAFF"),
        ("readonly@whitfield.com", "Readonly123!", "Read Only Viewer", "READ_ONLY"),
    ]

    for email, pwd, name, role_name in default_accounts:
        existing = await user_crud.get_by_email(email)
        role = await role_crud.get_by_name(role_name)
        if not existing and role:
            user = UserModel(
                name=name,
                email=email,
                password_hash=hash_password(pwd),
                role_id=role.id,
                is_active=True,
            )
            await user_crud.create_user(user)
            logger.info(f"Seeded user account: {email}")

