from fastapi import APIRouter

from core.apis.routes import auth_router, inventory_router, product_router, seller_router, user_router

api_router = APIRouter()
api_router.include_router(auth_router.router)
api_router.include_router(user_router.router)
api_router.include_router(seller_router.router)
api_router.include_router(product_router.router)
api_router.include_router(inventory_router.router)
