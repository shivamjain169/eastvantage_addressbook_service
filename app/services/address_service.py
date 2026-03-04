# Business logic layer — orchestrates repository calls, enforces rules,
# handles errors, and maps failures to appropriate HTTP exceptions.

from fastapi import HTTPException, status

from app.core.logging import get_logger
from app.models.address import Address
from app.repositories.address_repository import AddressRepository
from app.schemas.address import AddressCreate, AddressUpdate, NearbyQuery
from app.utils.geo import is_within_radius

logger = get_logger(__name__)


class AddressService:
    def __init__(self, repository: AddressRepository) -> None:
        self._repo = repository

    def create_address(self, payload: AddressCreate) -> Address:
        logger.info("Creating address: name=%r city=%r", payload.name, payload.city)
        try:
            address = self._repo.create(payload)
            logger.info("Address created successfully: id=%d", address.id)
            return address
        except Exception as exc:
            logger.error("Failed to create address: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while creating the address.",
            ) from exc

    def get_address(self, address_id: int) -> Address:
        logger.debug("Fetching address: id=%d", address_id)
        address = self._repo.get_by_id(address_id)
        # Raise 404 if the address does not exist
        if address is None:
            logger.warning("Address not found: id=%d", address_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Address with id={address_id} not found.",
            )
        return address

    def update_address(self, address_id: int, payload: AddressUpdate) -> Address:
        logger.info("Updating address: id=%d", address_id)
        address = self._repo.get_by_id(address_id)
        # Verify existence before attempting the update
        if address is None:
            logger.warning("Update failed — address not found: id=%d", address_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Address with id={address_id} not found.",
            )
        try:
            updated = self._repo.update(address, payload)
            logger.info("Address updated successfully: id=%d", address_id)
            return updated
        except Exception as exc:
            logger.error("Failed to update address id=%d: %s", address_id, exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while updating the address.",
            ) from exc

    def delete_address(self, address_id: int) -> None:
        logger.info("Deleting address: id=%d", address_id)
        address = self._repo.get_by_id(address_id)
        # Verify existence before attempting the delete
        if address is None:
            logger.warning("Delete failed — address not found: id=%d", address_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Address with id={address_id} not found.",
            )
        try:
            self._repo.delete(address)
            logger.info("Address deleted successfully: id=%d", address_id)
        except Exception as exc:
            logger.error("Failed to delete address id=%d: %s", address_id, exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while deleting the address.",
            ) from exc

    def get_nearby_addresses(self, query: NearbyQuery) -> list[Address]:
        logger.info(
            "Fetching nearby addresses: lat=%s lon=%s radius_km=%s",
            query.latitude,
            query.longitude,
            query.radius_km,
        )
        try:
            all_addresses = self._repo.get_all()
            # Filter in Python using geodesic distance — no raw SQL required
            nearby = [
                addr
                for addr in all_addresses
                if is_within_radius(query.latitude, query.longitude, addr, query.radius_km)
            ]
            logger.info(
                "Found %d address(es) within %.2f km of (%s, %s)",
                len(nearby),
                query.radius_km,
                query.latitude,
                query.longitude,
            )
            return nearby
        except Exception as exc:
            logger.error("Failed to fetch nearby addresses: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while retrieving nearby addresses.",
            ) from exc
