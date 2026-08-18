"""
AI Tools Service — Read-only, RBAC-enforced tool callables for the Operational AI Assistant.
The LLM layer never decides permissions. Every tool checks warehouse scope before fetching data.
"""
from typing import List, Dict, Any, Optional
from commons.logger import get_logger
from core.controllers.inventory_controller import InventoryController
from core.controllers.order_controller import OrderController
from core.controllers.receiving_controller import ReceivingController
from core.models.user_model import UserModel
from commons.auth import authorize_warehouse

logger = get_logger(__name__)


class AIToolsService:
    """Strict read-only tool allowlist for the WMS AI Assistant.
    Each method re-validates warehouse scope for the calling user before returning data.
    """

    def __init__(self):
        self.inventory_ctrl = InventoryController()
        self.order_ctrl = OrderController()

    async def get_inventory(
        self,
        current_user: UserModel,
        warehouse_code: Optional[str] = None,
        sku: Optional[str] = None,
        product_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch live inventory levels from the WMS for an optional warehouse/SKU filter."""
        logger.info(f"AI tool: get_inventory wh={warehouse_code} sku={sku} for {current_user.email}")
        if warehouse_code:
            await authorize_warehouse(current_user, warehouse_code)
        records = await self.inventory_ctrl.list_inventory(
            warehouse_code=warehouse_code,
            sku=sku,
            product_id=product_id,
        )
        # Non-admin users: filter to assigned warehouses
        from core.cruds.role_crud import RoleCRUD
        role_crud = RoleCRUD()
        role = await role_crud.get_by_id(current_user.role_id)
        if not role or role.name != "ADMIN":
            records = [r for r in records if r.warehouse_code in current_user.assigned_warehouse_ids]
        return [r.model_dump(mode="json") for r in records]

    async def list_orders(
        self,
        current_user: UserModel,
        warehouse_code: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch live orders from the WMS for an optional warehouse/status filter."""
        logger.info(f"AI tool: list_orders wh={warehouse_code} status={status} for {current_user.email}")
        if warehouse_code:
            await authorize_warehouse(current_user, warehouse_code)
        results = await self.order_ctrl.list_orders(
            warehouse_code=warehouse_code,
            status=status,
        )
        # Non-admin users: filter to assigned warehouses
        from core.cruds.role_crud import RoleCRUD
        role_crud = RoleCRUD()
        role = await role_crud.get_by_id(current_user.role_id)
        if not role or role.name != "ADMIN":
            results = [r for r in results if r.warehouse_code in current_user.assigned_warehouse_ids]
        return [r.model_dump(mode="json") for r in results]

    async def get_inventory_summary(
        self,
        current_user: UserModel,
        warehouse_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Returns a high-level inventory summary (total SKUs, total units) for the requested warehouse."""
        logger.info(f"AI tool: get_inventory_summary wh={warehouse_code} for {current_user.email}")
        records = await self.get_inventory(current_user=current_user, warehouse_code=warehouse_code)
        total_units = sum(r.get("available_quantity", 0) for r in records)
        return {
            "warehouse_code": warehouse_code or "ALL",
            "total_sku_count": len(records),
            "total_available_units": total_units,
        }

    async def get_order_summary(
        self,
        current_user: UserModel,
        warehouse_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Returns a high-level order summary grouped by status."""
        logger.info(f"AI tool: get_order_summary wh={warehouse_code} for {current_user.email}")
        orders = await self.list_orders(current_user=current_user, warehouse_code=warehouse_code)
        summary: Dict[str, int] = {}
        for o in orders:
            s = o.get("status", "UNKNOWN")
            summary[s] = summary.get(s, 0) + 1
        return {
            "warehouse_code": warehouse_code or "ALL",
            "total_orders": len(orders),
            "by_status": summary,
        }
