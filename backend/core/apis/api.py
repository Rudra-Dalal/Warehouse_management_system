from fastapi import APIRouter

from core.apis.routes import auth_router, user_router

api_router = APIRouter()
api_router.include_router(auth_router.router)
api_router.include_router(user_router.router)
