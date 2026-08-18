from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from commons.logger import get_logger
from core.apis.api import api_router
from core.config import settings
from core.database.database import DatabaseManager, seed_fixed_warehouses
from core.database.indexes import create_database_indexes
from core.database.seed_rbac import seed_rbac_data

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and shutdown lifecycle events.
    Connects to MongoDB, seeds fixed warehouses, seeds RBAC data, creates indexes, and closes connection.
    """
    logger.info("Executing application startup lifespan event")
    try:
        await DatabaseManager.connect_to_database()
        await seed_fixed_warehouses()
        await seed_rbac_data()
        await create_database_indexes()
        logger.info("Application startup initialization completed successfully")
    except Exception as error:
        logger.error(f"Error during application startup initialization: {error}")
        raise error

    yield

    logger.info("Executing application shutdown lifespan event")
    await DatabaseManager.close_database_connection()


app = FastAPI(
    title="Whitfield Fulfillment WMS API",
    description="Backend API for Whitfield Warehouse Management System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers under root
app.include_router(api_router)


@app.get("/health")
async def health_check():
    """Returns the operational status of the backend API service.
    Performs a lightweight ping check to verify database readiness.

    Returns:
        dict: A dictionary containing health status and service metadata.
    """
    logger.info("Calling GET /health endpoint")
    try:
        db = DatabaseManager.get_db()
        await db.command("ping")
        return {
            "status": "healthy",
            "service": "Whitfield Fulfillment WMS Backend",
            "database": "connected",
        }
    except Exception as error:
        logger.error(f"Error in GET /health endpoint: {error}")
        raise HTTPException(
            status_code=500,
            detail=f"Database health check failed: {str(error)}",
        )
