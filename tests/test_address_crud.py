import pytest
from fastapi.testclient import TestClient

BASE_URL = "/api/v1/addresses"

VALID_PAYLOAD = {
    "name": "Eiffel Tower",
    "street": "Champ de Mars, 5 Av. Anatole France",
    "city": "Paris",
    "country": "France",
    "latitude": 48.8584,
    "longitude": 2.2945,
}


class TestCreateAddress:
    def test_create_returns_201(self, client: TestClient) -> None:
        response = client.post(BASE_URL + "/", json=VALID_PAYLOAD)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == VALID_PAYLOAD["name"]
        assert data["city"] == VALID_PAYLOAD["city"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_invalid_latitude_returns_422(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "latitude": 999.0}
        response = client.post(BASE_URL + "/", json=payload)
        assert response.status_code == 422

    def test_create_invalid_longitude_returns_422(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "longitude": -999.0}
        response = client.post(BASE_URL + "/", json=payload)
        assert response.status_code == 422

    def test_create_missing_field_returns_422(self, client: TestClient) -> None:
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "city"}
        response = client.post(BASE_URL + "/", json=payload)
        assert response.status_code == 422


class TestGetAddress:
    def test_get_existing_address(self, client: TestClient) -> None:
        create_resp = client.post(BASE_URL + "/", json=VALID_PAYLOAD)
        address_id = create_resp.json()["id"]

        response = client.get(f"{BASE_URL}/{address_id}")
        assert response.status_code == 200
        assert response.json()["id"] == address_id

    def test_get_nonexistent_address_returns_404(self, client: TestClient) -> None:
        response = client.get(f"{BASE_URL}/999999")
        assert response.status_code == 404


class TestUpdateAddress:
    def test_partial_update(self, client: TestClient) -> None:
        create_resp = client.post(BASE_URL + "/", json=VALID_PAYLOAD)
        address_id = create_resp.json()["id"]

        response = client.patch(f"{BASE_URL}/{address_id}", json={"city": "Lyon"})
        assert response.status_code == 200
        assert response.json()["city"] == "Lyon"
        assert response.json()["name"] == VALID_PAYLOAD["name"]

    def test_update_nonexistent_returns_404(self, client: TestClient) -> None:
        response = client.patch(f"{BASE_URL}/999999", json={"city": "Lyon"})
        assert response.status_code == 404

    def test_update_invalid_latitude_returns_422(self, client: TestClient) -> None:
        create_resp = client.post(BASE_URL + "/", json=VALID_PAYLOAD)
        address_id = create_resp.json()["id"]

        response = client.patch(f"{BASE_URL}/{address_id}", json={"latitude": 200.0})
        assert response.status_code == 422


class TestDeleteAddress:
    def test_delete_existing_returns_204(self, client: TestClient) -> None:
        create_resp = client.post(BASE_URL + "/", json=VALID_PAYLOAD)
        address_id = create_resp.json()["id"]

        response = client.delete(f"{BASE_URL}/{address_id}")
        assert response.status_code == 204

    def test_delete_nonexistent_returns_404(self, client: TestClient) -> None:
        response = client.delete(f"{BASE_URL}/999999")
        assert response.status_code == 404

    def test_deleted_address_no_longer_accessible(self, client: TestClient) -> None:
        create_resp = client.post(BASE_URL + "/", json=VALID_PAYLOAD)
        address_id = create_resp.json()["id"]

        client.delete(f"{BASE_URL}/{address_id}")
        get_resp = client.get(f"{BASE_URL}/{address_id}")
        assert get_resp.status_code == 404


class TestNearbyAddresses:
    LOUVRE = {
        "name": "Louvre Museum",
        "street": "Rue de Rivoli",
        "city": "Paris",
        "country": "France",
        "latitude": 48.8606,
        "longitude": 2.3376,
    }
    TOKYO = {
        "name": "Tokyo Tower",
        "street": "4 Chome-2-8 Shibakoen",
        "city": "Tokyo",
        "country": "Japan",
        "latitude": 35.6586,
        "longitude": 139.7454,
    }

    def test_finds_nearby_address(self, client: TestClient) -> None:
        client.post(BASE_URL + "/", json=self.LOUVRE)

        response = client.get(
            f"{BASE_URL}/nearby/search",
            params={"latitude": 48.8584, "longitude": 2.2945, "radius_km": 10},
        )
        assert response.status_code == 200
        names = [a["name"] for a in response.json()]
        assert "Louvre Museum" in names

    def test_excludes_distant_address(self, client: TestClient) -> None:
        client.post(BASE_URL + "/", json=self.TOKYO)

        response = client.get(
            f"{BASE_URL}/nearby/search",
            params={"latitude": 48.8584, "longitude": 2.2945, "radius_km": 10},
        )
        assert response.status_code == 200
        names = [a["name"] for a in response.json()]
        assert "Tokyo Tower" not in names

    def test_invalid_radius_returns_422(self, client: TestClient) -> None:
        response = client.get(
            f"{BASE_URL}/nearby/search",
            params={"latitude": 48.8584, "longitude": 2.2945, "radius_km": -5},
        )
        assert response.status_code == 422

    def test_invalid_center_latitude_returns_422(self, client: TestClient) -> None:
        response = client.get(
            f"{BASE_URL}/nearby/search",
            params={"latitude": 999, "longitude": 2.2945, "radius_km": 10},
        )
        assert response.status_code == 422
