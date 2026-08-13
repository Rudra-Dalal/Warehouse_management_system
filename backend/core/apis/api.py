from fastapi import APIRouter

from core.apis.routes import (
    audit_router,
    auth_router,
    fulfillment_router,
    inventory_router,
    order_router,
    product_router,
    receiving_router,
    seller_router,
    user_router,
)

api_router = APIRouter()
api_router.include_router(auth_router.router)
api_router.include_router(user_router.router)
api_router.include_router(seller_router.router)
api_router.include_router(product_router.router)
api_router.include_router(inventory_router.router)
api_router.include_router(receiving_router.router)
api_router.include_router(order_router.router)
api_router.include_router(fulfillment_router.router)
api_router.include_router(audit_router.router)
