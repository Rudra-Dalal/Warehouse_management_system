from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from commons.logger import get_logger
from core.database.database import DatabaseManager, seed_fixed_warehouses
from core.database.indexes import create_database_indexes

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and shutdown lifecycle events.
    Connects to MongoDB, seeds fixed warehouses, creates indexes, and closes connection.
    """
    logger.info("Executing application startup lifespan event")
    try:
        await DatabaseManager.connect_to_database()
        await seed_fixed_warehouses()
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
