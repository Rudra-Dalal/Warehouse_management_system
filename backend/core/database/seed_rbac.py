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
        {"name": "inventory.receive", "description": "Receive new stock shipments"},
        {"name": "orders.read", "description": "Read order details and status"},
        {"name": "orders.confirm", "description": "Confirm orders and reserve inventory"},
        {"name": "fulfillment.pick", "description": "Perform pick tasks"},
        {"name": "fulfillment.pack", "description": "Perform packing operations"},
        {"name": "fulfillment.ship", "description": "Ship orders and assign tracking"},
        {"name": "audit.read", "description": "Read system audit log records"},
        {"name": "users.manage", "description": "Manage user accounts and role assignments"},
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
        "inventory.receive",
        "orders.read",
        "fulfillment.pick",
        "fulfillment.pack",
        "fulfillment.ship",
    ]
    staff_perm_ids = [permission_map[name] for name in staff_perm_names if name in permission_map]

    # Initial Roles Definition
    roles_definitions = [
        {"name": "ADMIN", "description": "System Administrator with unrestricted access", "permission_ids": all_perm_ids},
        {"name": "MANAGER", "description": "Warehouse Manager with operational and management access", "permission_ids": all_perm_ids},
        {"name": "WAREHOUSE_STAFF", "description": "Warehouse Staff with operational access", "permission_ids": staff_perm_ids},
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

    # Optional Development Admin User Seeding
    if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD and admin_role_id:
        admin_email = settings.ADMIN_EMAIL.lower().strip()
        existing_admin = await user_crud.get_by_email(admin_email)
        if not existing_admin:
            hashed_pwd = hash_password(settings.ADMIN_PASSWORD)
            admin_user = UserModel(
                name="System Administrator",
                email=admin_email,
                password_hash=hashed_pwd,
                role_id=admin_role_id,
                is_active=True,
            )
            await user_crud.create_user(admin_user)
            logger.info(f"Seeded development admin user: {admin_email}")
        else:
            logger.info(f"Development admin user {admin_email} already exists")
