from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AddressBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Address label or name")
    street: str = Field(..., min_length=1, max_length=500, description="Street line")
    city: str = Field(..., min_length=1, max_length=255, description="City name")
    country: str = Field(..., min_length=1, max_length=255, description="Country name")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude (-90 to 90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude (-180 to 180)")

    @field_validator("name", "street", "city", "country", mode="before")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    street: str | None = Field(default=None, min_length=1, max_length=500)
    city: str | None = Field(default=None, min_length=1, max_length=255)
    country: str | None = Field(default=None, min_length=1, max_length=255)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)

    @field_validator("name", "street", "city", "country", mode="before")
    @classmethod
    def strip_whitespace(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            return value.strip()
        return value


class AddressResponse(AddressBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class NearbyQuery(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Center latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Center longitude")
    radius_km: float = Field(..., gt=0, description="Search radius in kilometers (must be > 0)")
