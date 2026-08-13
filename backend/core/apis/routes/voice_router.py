from fastapi import APIRouter, Depends, HTTPException, status
from commons.auth import get_current_user
from commons.logger import get_logger
from core.apis.schemas.requests.voice_request import VoiceCommandRequest
from core.apis.schemas.responses.voice_response import VoiceCommandResponse
from core.cruds.product_crud import ProductCRUD
from core.cruds.inventory_crud import InventoryCRUD
from core.cruds.order_crud import OrderCRUD
from core.cruds.audit_crud import AuditCRUD

from core.models.user_model import UserModel

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/voice", tags=["Voice AI"])

product_crud = ProductCRUD()
inventory_crud = InventoryCRUD()
order_crud = OrderCRUD()
audit_crud = AuditCRUD()


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
    if intent in ("adjust_inventory", "reserve_inventory"):
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

        product = None
        if sku:
            product = await product_crud.get_by_sku(sku)
        elif upc:
            product = await product_crud.get_by_upc(upc)

        if product:
            inv_list = await inventory_crud.list_inventory(
                warehouse_id=warehouse_id, product_id=str(product.id)
            )
            data = {
                "product": {
                    "sku": product.sku,
                    "name": product.name,
                    "upc": product.upc,
                },
                "inventory": [
                    {
                        "warehouse_id": item.warehouse_id,
                        "available": item.quantity_available,
                        "reserved": item.quantity_reserved,
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
            total_avail = sum(i.quantity_available for i in inv_list)
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
        return VoiceCommandResponse(
            intent=intent,
            status="success",
            message=f"Order book query: {len(orders)} order(s) found.",
            data={"total_orders": len(orders)},
        )

    # Intent: Mutating Adjust Inventory
    elif intent == "adjust_inventory":
        if "inventory:adjust" not in current_user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: 'inventory:adjust' required for voice stock adjustments.",
            )

        sku = entities.get("sku")
        warehouse_id = entities.get("warehouse_id") or "RENO"
        quantity_delta = entities.get("quantity", 0)

        product = await product_crud.get_by_sku(sku) if sku else None
        if not product:
            return VoiceCommandResponse(
                intent=intent,
                status="error",
                message=f"Product with SKU {sku} not found for adjustment.",
            )

        updated_inv = await inventory_crud.adjust_stock(
            warehouse_id=warehouse_id,
            product_id=str(product.id),
            quantity_delta=quantity_delta,
            user_id=str(current_user.id),
            reason=f"Voice AI Command: {request.transcript}",
        )

        await audit_crud.log_event(
            entity_type="INVENTORY",
            entity_id=str(updated_inv.id),
            action="VOICE_ADJUST_STOCK",
            user_id=str(current_user.id),
            warehouse_id=warehouse_id,
            metadata={"transcript": request.transcript, "delta": quantity_delta},
        )

        return VoiceCommandResponse(
            intent=intent,
            status="success",
            message=f"Adjusted stock for {product.name} ({warehouse_id}) by {quantity_delta}. New available: {updated_inv.quantity_available}.",
            data={
                "warehouse_id": updated_inv.warehouse_id,
                "quantity_available": updated_inv.quantity_available,
            },
        )

    # Fallback/General Intent Query
    return VoiceCommandResponse(
        intent=intent,
        status="success",
        message=f"Processed query '{request.transcript}' successfully.",
        data={"intent": intent, "entities": entities},
    )
