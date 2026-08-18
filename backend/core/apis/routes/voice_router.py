from fastapi import APIRouter, Depends, HTTPException, status
from commons.auth import get_current_user, authorize_warehouse
from commons.logger import get_logger
from core.apis.schemas.requests.voice_request import VoiceCommandRequest
from core.apis.schemas.responses.voice_response import VoiceCommandResponse
from core.cruds.product_crud import ProductCRUD
from core.cruds.inventory_crud import InventoryCRUD
from core.cruds.order_crud import OrderCRUD
from core.cruds.audit_crud import AuditCRUD
from core.cruds.role_crud import RoleCRUD
from core.cruds.permission_crud import PermissionCRUD
from bson import ObjectId

from uuid import uuid4
from core.apis.schemas.requests.inventory_request import InventoryAdjustmentRequest
from core.apis.schemas.requests.receiving_request import ReceivingCreateRequest, ReceivingItemRequest
from core.controllers.inventory_controller import InventoryController
from core.controllers.receiving_controller import ReceivingController
from core.cruds.seller_crud import SellerCRUD
from core.database.database import DatabaseManager
from core.models.user_model import UserModel

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/voice", tags=["Voice AI"])

product_crud = ProductCRUD()
inventory_crud = InventoryCRUD()
order_crud = OrderCRUD()
audit_crud = AuditCRUD()
seller_crud = SellerCRUD()
inventory_controller = InventoryController()
receiving_controller = ReceivingController()


@router.post("/command", response_model=VoiceCommandResponse)
async def process_voice_command(
    request: VoiceCommandRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """Processes structured Voice Commands, validating permissions, resolving entities,
    and delegating to existing WMS backend CRUD services with audit tracking.
    """
    logger.info(f"Processing voice command '{request.intent}' for user {current_user.email}")
    intent = request.intent
    entities = request.entities

    # 1. Mutating Commands require confirmation flag
    if intent in ("adjust_inventory", "reserve_inventory", "receive_inventory"):
        if not request.confirmed:
            return VoiceCommandResponse(
                intent=intent,
                status="confirmation_required",
                message=f"Please confirm: {intent.replace('_', ' ').capitalize()} with parameters {entities}",
                data={"entities": entities, "transcript": request.transcript},
                requires_confirmation=True,
            )

    # 2. Intent Handlers reusing existing WMS services

    # Intent: Inventory Lookup
    if intent == "inventory_lookup":
        sku = entities.get("sku")
        upc = entities.get("upc")
        warehouse_id = entities.get("warehouse_id")

        if warehouse_id:
            await authorize_warehouse(current_user, warehouse_id)

        product = None
        if sku:
            product = await product_crud.get_by_sku(sku)
        elif upc:
            product = await product_crud.get_by_upc(upc)

        if product:
            inv_list = await inventory_crud.list_inventory(
                warehouse_id=warehouse_id, product_id=str(product.id)
            )
            # Filter for assigned warehouses if no specific warehouse requested
            if not warehouse_id:
                from core.cruds.role_crud import RoleCRUD
                role_crud = RoleCRUD()
                role = await role_crud.get_by_id(current_user.role_id)
                if not role or role.name != "ADMIN":
                    db = DatabaseManager.get_db()
                    filtered_inv_list = []
                    for item in inv_list:
                        wh = await db["warehouses"].find_one({"_id": ObjectId(item.warehouse_id)})
                        if wh and wh["code"] in current_user.assigned_warehouse_ids:
                            filtered_inv_list.append(item)
                    inv_list = filtered_inv_list

            data = {
                "product": {
                    "sku": product.sku,
                    "name": product.name,
                    "upc": product.upc,
                },
                "inventory": [
                    {
                        "warehouse_id": item.warehouse_id,
                        "available": item.available_quantity,
                        "reserved": item.reserved_quantity,
                    }
                    for item in inv_list
                ],
            }
            return VoiceCommandResponse(
                intent=intent,
                status="success",
                message=f"Stock query for {product.name} ({product.sku}): {len(inv_list)} inventory record(s) found.",
                data=data,
            )
        else:
            inv_list = await inventory_crud.list_inventory(warehouse_id=warehouse_id)
            if not warehouse_id:
                from core.cruds.role_crud import RoleCRUD
                role_crud = RoleCRUD()
                role = await role_crud.get_by_id(current_user.role_id)
                if not role or role.name != "ADMIN":
                    db = DatabaseManager.get_db()
                    filtered_inv_list = []
                    for item in inv_list:
                        wh = await db["warehouses"].find_one({"_id": ObjectId(item.warehouse_id)})
                        if wh and wh["code"] in current_user.assigned_warehouse_ids:
                            filtered_inv_list.append(item)
                    inv_list = filtered_inv_list

            total_avail = sum(i.available_quantity for i in inv_list)
            return VoiceCommandResponse(
                intent=intent,
                status="success",
                message=f"Network inventory query: {total_avail} available units across {len(inv_list)} record(s).",
                data={"total_available": total_avail, "records": len(inv_list)},
            )

    # Intent: Product Lookup
    elif intent == "product_lookup":
        sku = entities.get("sku")
        upc = entities.get("upc")
        product = None
        if sku:
            product = await product_crud.get_by_sku(sku)
        elif upc:
            product = await product_crud.get_by_upc(upc)

        if product:
            return VoiceCommandResponse(
                intent=intent,
                status="success",
                message=f"Product found: {product.name} (SKU: {product.sku}, UPC: {product.upc}).",
                data={
                    "product_id": str(product.id),
                    "sku": product.sku,
                    "name": product.name,
                    "upc": product.upc,
                    "reorder_point": product.reorder_point,
                },
            )
        else:
            return VoiceCommandResponse(
                intent=intent,
                status="success",
                message="No product record matched the specified SKU/UPC.",
                data=None,
            )

    # Intent: Order Lookup
    elif intent == "order_lookup":
        order_id = entities.get("order_id")
        if order_id:
            order = await order_crud.get_by_id(order_id)
            if order:
                db = DatabaseManager.get_db()
                wh = await db["warehouses"].find_one({"_id": ObjectId(order.warehouse_id)})
                if wh:
                    await authorize_warehouse(current_user, wh["code"])
                
                return VoiceCommandResponse(
                    intent=intent,
                    status="success",
                    message=f"Order {order.id}: Status is {order.status}, Customer {order.customer_name}.",
                    data={
                        "order_id": str(order.id),
                        "status": order.status,
                        "customer": order.customer_name,
                        "warehouse_id": order.warehouse_id,
                        "item_count": len(order.items),
                    },
                )
        orders = await order_crud.list_orders()
        
        from core.cruds.role_crud import RoleCRUD
        role_crud = RoleCRUD()
        role = await role_crud.get_by_id(current_user.role_id)
        if not role or role.name != "ADMIN":
            db = DatabaseManager.get_db()
            filtered_orders = []
            for order in orders:
                wh = await db["warehouses"].find_one({"_id": ObjectId(order.warehouse_id)})
                if wh and wh["code"] in current_user.assigned_warehouse_ids:
                    filtered_orders.append(order)
            orders = filtered_orders
            
        return VoiceCommandResponse(
            intent=intent,
            status="success",
            message=f"Order book query: {len(orders)} order(s) found.",
            data={"total_orders": len(orders)},
        )

    # Intent: Mutating Adjust Inventory
    elif intent == "adjust_inventory":
        role_crud = RoleCRUD()
        role = await role_crud.get_by_id(current_user.role_id)
        permission_crud = PermissionCRUD()
        permissions = await permission_crud.get_by_ids(role.permission_ids) if role else []
        perm_names = [p.name for p in permissions]
        if "inventory.adjust" not in perm_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: 'inventory.adjust' required for voice stock adjustments.",
            )

        sku = entities.get("sku")
        warehouse_id = entities.get("warehouse_id") or "RENO"
        
        await authorize_warehouse(current_user, warehouse_id)
        
        quantity_delta = entities.get("quantity", 0)

        product = await product_crud.get_by_sku(sku) if sku else None
        if not product:
            return VoiceCommandResponse(
                intent=intent,
                status="error",
                message=f"Product with SKU {sku} not found for adjustment.",
            )

        db = DatabaseManager.get_db()
        wh = await db["warehouses"].find_one({"code": warehouse_id})
        wh_id = str(wh["_id"]) if wh else warehouse_id

        inv_rec = await inventory_crud.get_by_product_and_warehouse(str(product.id), wh_id)
        if not inv_rec:
            return VoiceCommandResponse(
                intent=intent,
                status="error",
                message=f"Inventory record for SKU {sku} at warehouse {warehouse_id} not found.",
            )

        updated_inv = await inventory_controller.adjust_inventory(
            inventory_id=inv_rec.id,
            request=InventoryAdjustmentRequest(
                quantity_delta=quantity_delta,
                note=f"Voice AI Command: {request.transcript}",
            ),
            current_user=current_user,
        )

        return VoiceCommandResponse(
            intent=intent,
            status="success",
            message=f"Adjusted stock for {product.name} ({warehouse_id}) by {quantity_delta}. New available: {updated_inv.available_quantity}.",
            data={
                "warehouse_id": updated_inv.warehouse_id,
                "available_quantity": updated_inv.available_quantity,
            },
        )

    # Intent: Mutating Receive Inventory
    elif intent == "receive_inventory":
        role_crud = RoleCRUD()
        role = await role_crud.get_by_id(current_user.role_id)
        permission_crud = PermissionCRUD()
        permissions = await permission_crud.get_by_ids(role.permission_ids) if role else []
        perm_names = [p.name for p in permissions]
        if "receiving:write" not in perm_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: 'receiving:write' required for voice inbound receiving.",
            )

        sku = entities.get("sku")
        upc = entities.get("upc")
        product_id = entities.get("product_id")
        warehouse_code = (entities.get("warehouse_id") or entities.get("warehouse_code") or "RENO").upper()
        quantity = int(entities.get("quantity") or entities.get("quantity_received") or 0)
        seller_id = entities.get("seller_id")

        if quantity <= 0:
            return VoiceCommandResponse(
                intent=intent,
                status="error",
                message="Received quantity must be greater than zero.",
            )

        await authorize_warehouse(current_user, warehouse_code)

        product = None
        if product_id:
            product = await product_crud.get_by_id(product_id)
        elif sku:
            product = await product_crud.get_by_sku(sku)
        elif upc:
            product = await product_crud.get_by_upc(upc)

        if not product:
            return VoiceCommandResponse(
                intent=intent,
                status="error",
                message=f"Product with identifier (SKU: {sku}, UPC: {upc}) not found.",
            )

        # Resolve seller
        if not seller_id:
            seller_id = product.seller_id

        rec_ref = f"VOICE-REC-{uuid4().hex[:8].upper()}"
        receiving_res = await receiving_controller.receive_shipment(
            request=ReceivingCreateRequest(
                receiving_reference=rec_ref,
                warehouse_code=warehouse_code,
                seller_id=seller_id,
                items=[ReceivingItemRequest(product_id=str(product.id), quantity=quantity)],
            ),
            current_user=current_user,
        )

        return VoiceCommandResponse(
            intent=intent,
            status="success",
            message=f"Successfully received {quantity} units of {product.name} ({sku or product.sku}) into {warehouse_code} hub. Reference: {rec_ref}.",
            data={
                "receiving_id": receiving_res.id,
                "receiving_reference": receiving_res.receiving_reference,
                "warehouse_code": receiving_res.warehouse_code,
                "product_id": str(product.id),
                "sku": product.sku,
                "quantity_received": quantity,
            },
        )

    # Fallback/General Intent Query
    return VoiceCommandResponse(
        intent=intent,
        status="success",
        message=f"Processed query '{request.transcript}' successfully.",
        data={"intent": intent, "entities": entities},
    )

