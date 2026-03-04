from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import get_db
from app.repositories.address_repository import AddressRepository
from app.schemas.address import AddressCreate, AddressResponse, AddressUpdate, NearbyQuery
from app.services.address_service import AddressService

router = APIRouter(prefix="/addresses", tags=["Addresses"])
logger = get_logger(__name__)


def get_address_service(db: Session = Depends(get_db)) -> AddressService:
    return AddressService(AddressRepository(db))


@router.post(
    "/",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new address",
)
def create_address(
    payload: AddressCreate,
    service: AddressService = Depends(get_address_service),
) -> AddressResponse:
    logger.info("POST /addresses — creating address")
    return service.create_address(payload)


@router.get(
    "/{address_id}",
    response_model=AddressResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a single address by ID",
)
def get_address(
    address_id: int,
    service: AddressService = Depends(get_address_service),
) -> AddressResponse:
    logger.info("GET /addresses/%d", address_id)
    return service.get_address(address_id)


@router.patch(
    "/{address_id}",
    response_model=AddressResponse,
    status_code=status.HTTP_200_OK,
    summary="Partially update an address",
)
def update_address(
    address_id: int,
    payload: AddressUpdate,
    service: AddressService = Depends(get_address_service),
) -> AddressResponse:
    logger.info("PATCH /addresses/%d", address_id)
    return service.update_address(address_id, payload)


@router.delete(
    "/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an address",
)
def delete_address(
    address_id: int,
    service: AddressService = Depends(get_address_service),
) -> None:
    logger.info("DELETE /addresses/%d", address_id)
    service.delete_address(address_id)


@router.get(
    "/nearby/search",
    response_model=list[AddressResponse],
    status_code=status.HTTP_200_OK,
    summary="Find addresses within a given radius",
)
def get_nearby_addresses(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Center latitude"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Center longitude"),
    radius_km: float = Query(..., gt=0, description="Search radius in kilometers"),
    service: AddressService = Depends(get_address_service),
) -> list[AddressResponse]:
    logger.info(
        "GET /addresses/nearby/search — lat=%s lon=%s radius_km=%s",
        latitude,
        longitude,
        radius_km,
    )
    query = NearbyQuery(latitude=latitude, longitude=longitude, radius_km=radius_km)
    return service.get_nearby_addresses(query)
