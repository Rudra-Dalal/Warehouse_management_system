from typing import List, Optional
from fastapi import HTTPException, status

from commons.logger import get_logger
from core.apis.schemas.requests.seller_request import SellerCreateRequest, SellerUpdateRequest
from core.apis.schemas.responses.seller_response import SellerResponse
from core.cruds.seller_crud import SellerCRUD
from core.models.audit_log_model import AuditAction
from core.models.seller_model import SellerModel
from core.models.user_model import UserModel
from core.services.audit_service import AuditService

logger = get_logger(__name__)


class SellerController:
    """Business logic controller handling seller registration and account management.
    Validates seller code uniqueness and orchestrates seller CRUD operations.
    """

    def __init__(self):
        """Initializes SellerController with SellerCRUD instance."""
        self.seller_crud = SellerCRUD()

    async def list_sellers(self) -> List[SellerResponse]:
        """Retrieves all registered seller client accounts.
        Returns a list of public SellerResponse schemas.

        Returns:
            List[SellerResponse]: List of all seller accounts.
        """
        logger.info("Executing SellerController.list_sellers")
        sellers = await self.seller_crud.list_sellers()
        return [
            SellerResponse(
                id=s.id,
                code=s.code,
                name=s.name,
                email=s.email,
                phone=s.phone,
                is_active=s.is_active,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in sellers
        ]

    async def get_seller_by_id(self, seller_id: str) -> SellerResponse:
        """Retrieves a specific seller account by string ObjectId.
        Raises HTTP 404 Not Found if no seller exists.

        Args:
            seller_id (str): Target seller ObjectId string.

        Returns:
            SellerResponse: Target seller account profile.
        """
        logger.info(f"Executing SellerController.get_seller_by_id for {seller_id}")
        seller = await self.seller_crud.get_by_id(seller_id)
        if not seller:
            logger.warning(f"Seller ID {seller_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seller with ID '{seller_id}' not found",
            )
        return SellerResponse(
            id=seller.id,
            code=seller.code,
            name=seller.name,
            email=seller.email,
            phone=seller.phone,
            is_active=seller.is_active,
            created_at=seller.created_at,
            updated_at=seller.updated_at,
        )

    async def create_seller(
        self, request: SellerCreateRequest, current_user: Optional[UserModel] = None
    ) -> SellerResponse:
        """Registers a new seller account with unique seller code validation.
        Raises HTTP 409 Conflict if code is already registered.

        Args:
            request (SellerCreateRequest): Seller creation parameters.

        Returns:
            SellerResponse: The created seller account details.
        """
        logger.info(f"Executing SellerController.create_seller for code {request.code}")
        existing = await self.seller_crud.get_by_code(request.code)
        if existing:
            logger.warning(f"Seller creation failed: Code {request.code} already exists")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Seller with code '{request.code}' already exists",
            )

        new_seller = SellerModel(
            code=request.code,
            name=request.name,
            email=request.email,
            phone=request.phone,
            is_active=True,
        )
        created = await self.seller_crud.create_seller(new_seller)
        audit_service = AuditService()
        await audit_service.record_event(
            action=AuditAction.SELLER_CREATED,
            entity_type="SELLER",
            entity_id=created.id,
            user_id=current_user.id if current_user else None,
            new_state={"code": created.code, "name": created.name, "email": created.email},
        )
        return SellerResponse(
            id=created.id,
            code=created.code,
            name=created.name,
            email=created.email,
            phone=created.phone,
            is_active=created.is_active,
            created_at=created.created_at,
            updated_at=created.updated_at,
        )

    async def update_seller(
        self, seller_id: str, request: SellerUpdateRequest, current_user: Optional[UserModel] = None
    ) -> SellerResponse:
        """Updates specific metadata or active state of a seller account.
        Raises HTTP 404 Not Found if target seller is missing.

        Args:
            seller_id (str): Target seller ObjectId string.
            request (SellerUpdateRequest): Field update parameters.
            current_user (Optional[UserModel]): Authenticated user performing action.

        Returns:
            SellerResponse: The updated seller account details.
        """
        logger.info(f"Executing SellerController.update_seller for {seller_id}")
        existing = await self.seller_crud.get_by_id(seller_id)
        if not existing:
            logger.warning(f"Seller update failed: Seller ID {seller_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seller with ID '{seller_id}' not found",
            )

        update_fields = {}
        if request.name is not None:
            update_fields["name"] = request.name
        if request.email is not None:
            update_fields["email"] = request.email
        if request.phone is not None:
            update_fields["phone"] = request.phone
        if request.is_active is not None:
            update_fields["is_active"] = request.is_active

        if not update_fields:
            return SellerResponse(
                id=existing.id,
                code=existing.code,
                name=existing.name,
                email=existing.email,
                phone=existing.phone,
                is_active=existing.is_active,
                created_at=existing.created_at,
                updated_at=existing.updated_at,
            )

        updated = await self.seller_crud.update_seller(seller_id, update_fields)
        audit_service = AuditService()
        await audit_service.record_event(
            action=AuditAction.SELLER_UPDATED,
            entity_type="SELLER",
            entity_id=updated.id,
            user_id=current_user.id if current_user else None,
            previous_state={"name": existing.name, "email": existing.email, "is_active": existing.is_active},
            new_state={"name": updated.name, "email": updated.email, "is_active": updated.is_active},
        )
        return SellerResponse(
            id=updated.id,
            code=updated.code,
            name=updated.name,
            email=updated.email,
            phone=updated.phone,
            is_active=updated.is_active,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )
