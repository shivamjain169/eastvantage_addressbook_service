from geopy.distance import geodesic

from app.models.address import Address


def is_within_radius(
    center_lat: float,
    center_lon: float,
    address: Address,
    radius_km: float,
) -> bool:
    """Return True if address coordinates fall within radius_km of the given center point."""
    center = (center_lat, center_lon)
    point = (address.latitude, address.longitude)
    distance_km = geodesic(center, point).kilometers
    return distance_km <= radius_km
