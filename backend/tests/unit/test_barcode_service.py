import pytest
from fastapi import HTTPException
from core.utils.barcode import normalize_barcode
from core.services.barcode_service import BarcodeService
from unittest.mock import patch, MagicMock, AsyncMock

def test_normalize_barcode_valid():
    assert normalize_barcode("012345678905") == "012345678905"
    assert isinstance(normalize_barcode("012345678905"), str)

def test_normalize_barcode_whitespace():
    assert normalize_barcode(" 012345678905 ") == "012345678905"
    assert normalize_barcode("\t012345678905\n") == "012345678905"

def test_normalize_barcode_empty():
    with pytest.raises(ValueError):
        normalize_barcode("")
    with pytest.raises(ValueError):
        normalize_barcode("   ")
    with pytest.raises(ValueError):
        normalize_barcode(None)

@pytest.mark.asyncio
@patch("core.services.barcode_service.ProductCRUD")
async def test_resolve_barcode_success(mock_product_crud_class):
    mock_crud = MagicMock()
    # Mock lookup returning a ProductModel
    mock_product = MagicMock()
    mock_crud.get_by_upc = AsyncMock(return_value=mock_product)
    mock_product_crud_class.return_value = mock_crud

    service = BarcodeService()
    resolved = await service.resolve_barcode("  012345678905  ")
    
    assert resolved == mock_product
    mock_crud.get_by_upc.assert_called_once_with("012345678905")

@pytest.mark.asyncio
@patch("core.services.barcode_service.ProductCRUD")
async def test_resolve_barcode_not_found(mock_product_crud_class):
    mock_crud = MagicMock()
    mock_crud.get_by_upc = AsyncMock(return_value=None)
    mock_product_crud_class.return_value = mock_crud

    service = BarcodeService()
    with pytest.raises(HTTPException) as exc_info:
        await service.resolve_barcode("012345678905")
        
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail

@pytest.mark.asyncio
async def test_resolve_barcode_invalid_input():
    service = BarcodeService()
    with pytest.raises(HTTPException) as exc_info:
        await service.resolve_barcode("   ")
        
    assert exc_info.value.status_code == 422
    assert "empty" in exc_info.value.detail
