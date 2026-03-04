from sqlalchemy.orm import Session

from app.models.address import Address
from app.schemas.address import AddressCreate, AddressUpdate


class AddressRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, payload: AddressCreate) -> Address:
        address = Address(**payload.model_dump())
        self._db.add(address)
        self._db.commit()
        self._db.refresh(address)
        return address

    def get_by_id(self, address_id: int) -> Address | None:
        return self._db.get(Address, address_id)

    def get_all(self) -> list[Address]:
        return self._db.query(Address).all()

    def update(self, address: Address, payload: AddressUpdate) -> Address:
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(address, field, value)
        self._db.commit()
        self._db.refresh(address)
        return address

    def delete(self, address: Address) -> None:
        self._db.delete(address)
        self._db.commit()
