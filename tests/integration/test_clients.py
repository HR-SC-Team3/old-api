import time

from pathlib import Path

import pytest

import requests

from schemas import Client, Order


REPO_ROOT = Path(__file__).resolve().parents[2]

CLIENTS_MODEL_SOURCE = (
    REPO_ROOT / "api" / "models" / "clients.py"
).read_text(encoding="utf-8")


# region Shared helpers


def _get_headers(user_headers, method="get", allowed=True):
    return user_headers(
        resource="clients",
        method=method,
        allowed=allowed
    )


def _first_client(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/clients",
        headers=headers
    )

    assert response.status_code == 200

    body = response.json()

    assert body, (
        "fixture data/client.json is expected to be non-empty"
    )

    return body[0]


def _client_payload(client_id=999999):
    return {
        "id": client_id,
        "name": "Test Client",
        "address": "Test Street 1",
        "city": "Amersfoort",
        "zip_code": "1234AB",
        "province": "Utrecht",
        "country": "Netherlands",
        "contact_name": "Test Person",
        "contact_phone": "0612345678",
        "contact_email": "test@example.com"
    }


# endregion


# region GET /clients


def test_get_clients_returns_200(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/clients",
        headers=headers
    )

    assert response.status_code == 200


def test_get_clients_returns_list(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/clients",
        headers=headers
    )

    assert response.status_code == 200

    body = response.json()

    assert isinstance(body, list)


def test_get_clients_schema(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/clients",
        headers=headers
    )

    assert response.status_code == 200

    for client in response.json():
        Client.model_validate(client)


def test_get_clients_content_type_is_json(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/clients",
        headers=headers
    )

    assert response.headers.get(
        "Content-Type",
        ""
    ).startswith("application/json")


def test_get_clients_response_time(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    start = time.monotonic()

    response = requests.get(
        f"{base_url}/api/v1/clients",
        headers=headers
    )

    elapsed = time.monotonic() - start

    assert response.status_code == 200
    assert elapsed < 5


def test_get_clients_without_api_key_returns_401(base_url):
    response = requests.get(
        f"{base_url}/api/v1/clients"
    )

    assert response.status_code == 401


def test_get_clients_invalid_api_key_returns_401(base_url):
    response = requests.get(
        f"{base_url}/api/v1/clients",
        headers={
            "API_KEY": "invalid-api-key"
        }
    )

    assert response.status_code == 401


def test_get_clients_without_permission_returns_403(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        allowed=False
    )

    response = requests.get(
        f"{base_url}/api/v1/clients",
        headers=headers
    )

    assert response.status_code == 403


# endregion


# region GET /clients/{id}


def test_get_client_returns_200(base_url, user_headers):
    client = _first_client(base_url, user_headers)

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/clients/{client['id']}",
        headers=headers
    )

    assert response.status_code == 200


def test_get_client_schema(base_url, user_headers):
    client = _first_client(base_url, user_headers)

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/clients/{client['id']}",
        headers=headers
    )

    assert response.status_code == 200

    Client.model_validate(response.json())


@pytest.mark.xfail(
    strict=True,
    reason="Current API returns 200 with null instead of 404."
)
def test_get_nonexistent_client_returns_404(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/clients/999999999",
        headers=headers
    )

    assert response.status_code == 404


def test_get_nonexistent_client_current_behavior(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/clients/999999999",
        headers=headers
    )

    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.xfail(
    strict=True,
    reason="Current API converts malformed IDs to 500."
)
def test_get_client_malformed_id_returns_400(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/clients/not-an-id",
        headers=headers
    )

    assert response.status_code == 400


def test_get_client_malformed_id_current_behavior(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/clients/not-an-id",
        headers=headers
    )

    assert response.status_code == 500


def test_get_client_without_api_key_returns_401(base_url):
    response = requests.get(
        f"{base_url}/api/v1/clients/1"
    )

    assert response.status_code == 401


def test_get_client_without_permission_returns_403(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        allowed=False
    )

    response = requests.get(
        f"{base_url}/api/v1/clients/1",
        headers=headers
    )

    assert response.status_code == 403


# endregion


# region POST /clients


def test_post_client_returns_201(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("client.json")

    headers = _get_headers(
        user_headers,
        method="post"
    )

    response = requests.post(
        f"{base_url}/api/v1/clients",
        headers=headers,
        json=_client_payload()
    )

    assert response.status_code == 201


@pytest.mark.xfail(
    strict=True,
    reason="Current POST endpoint returns 201 with an empty body."
)
def test_post_client_returns_created_client(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("client.json")

    headers = _get_headers(
        user_headers,
        method="post"
    )

    response = requests.post(
        f"{base_url}/api/v1/clients",
        headers=headers,
        json=_client_payload()
    )

    assert response.status_code == 201

    body = response.json()

    assert body["id"] == 999999


def test_post_client_is_saved(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("client.json")

    headers = _get_headers(
        user_headers,
        method="post"
    )

    response = requests.post(
        f"{base_url}/api/v1/clients",
        headers=headers,
        json=_client_payload(999998)
    )

    assert response.status_code == 201

    get_response = requests.get(
        f"{base_url}/api/v1/clients/999998",
        headers=_get_headers(user_headers)
    )

    assert get_response.status_code == 200

    body = get_response.json()

    assert body["id"] == 999998


def test_post_client_adds_timestamps(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("client.json")

    headers = _get_headers(
        user_headers,
        method="post"
    )

    response = requests.post(
        f"{base_url}/api/v1/clients",
        headers=headers,
        json=_client_payload(999997)
    )

    assert response.status_code == 201

    get_response = requests.get(
        f"{base_url}/api/v1/clients/999997",
        headers=_get_headers(user_headers)
    )

    assert get_response.status_code == 200

    body = get_response.json()

    assert "created_at" in body
    assert "updated_at" in body


def test_post_client_without_api_key_returns_401(base_url):
    response = requests.post(
        f"{base_url}/api/v1/clients",
        json=_client_payload()
    )

    assert response.status_code == 401


def test_post_client_without_permission_returns_403(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        method="post",
        allowed=False
    )

    response = requests.post(
        f"{base_url}/api/v1/clients",
        headers=headers,
        json=_client_payload()
    )

    assert response.status_code == 403


@pytest.mark.xfail(
    strict=True,
    reason="Current handler does not validate missing fields."
)
def test_post_client_missing_fields_returns_400(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("client.json")

    headers = _get_headers(
        user_headers,
        method="post"
    )

    response = requests.post(
        f"{base_url}/api/v1/clients",
        headers=headers,
        json={
            "id": 999996
        }
    )

    assert response.status_code == 400


@pytest.mark.xfail(
    strict=True,
    reason="Current handler does not validate field types."
)
def test_post_client_invalid_field_type_returns_400(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("client.json")

    headers = _get_headers(
        user_headers,
        method="post"
    )

    payload = _client_payload(999995)
    payload["id"] = "not-an-integer"

    response = requests.post(
        f"{base_url}/api/v1/clients",
        headers=headers,
        json=payload
    )

    assert response.status_code == 400


@pytest.mark.xfail(
    strict=True,
    reason="Current handler returns 500 for malformed JSON."
)
def test_post_client_malformed_json_returns_400(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        method="post"
    )

    response = requests.post(
        f"{base_url}/api/v1/clients",
        headers=headers,
        data="{ invalid json"
    )

    assert response.status_code == 400


# endregion


# region PUT /clients/{id}


def test_put_client_returns_200(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("client.json")

    client = _first_client(base_url, user_headers)

    headers = _get_headers(
        user_headers,
        method="put"
    )

    updated_client = dict(client)
    updated_client["name"] = "Updated Client"

    response = requests.put(
        f"{base_url}/api/v1/clients/{client['id']}",
        headers=headers,
        json=updated_client
    )

    assert response.status_code == 200


def test_put_client_update_is_persisted(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("client.json")

    client = _first_client(base_url, user_headers)

    headers = _get_headers(
        user_headers,
        method="put"
    )

    updated_client = dict(client)
    updated_client["name"] = "UPDATED-CLIENT"

    response = requests.put(
        f"{base_url}/api/v1/clients/{client['id']}",
        headers=headers,
        json=updated_client
    )

    assert response.status_code == 200

    get_response = requests.get(
        f"{base_url}/api/v1/clients/{client['id']}",
        headers=_get_headers(user_headers)
    )

    assert get_response.status_code == 200

    assert get_response.json()["name"] == "UPDATED-CLIENT"


def test_put_client_uses_full_replace():
    assert "self.data[i] = client" in CLIENTS_MODEL_SOURCE


@pytest.mark.xfail(
    strict=True,
    reason="Current API returns 200 when client does not exist."
)
def test_put_nonexistent_client_returns_404(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("client.json")

    headers = _get_headers(
        user_headers,
        method="put"
    )

    response = requests.put(
        f"{base_url}/api/v1/clients/999999999",
        headers=headers,
        json=_client_payload(999999999)
    )

    assert response.status_code == 404


def test_put_nonexistent_client_current_behavior(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("client.json")

    headers = _get_headers(
        user_headers,
        method="put"
    )

    response = requests.put(
        f"{base_url}/api/v1/clients/999999999",
        headers=headers,
        json=_client_payload(999999999)
    )

    assert response.status_code == 200


@pytest.mark.xfail(
    strict=True,
    reason="Current API converts malformed IDs to 500."
)
def test_put_client_malformed_id_returns_400(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        method="put"
    )

    response = requests.put(
        f"{base_url}/api/v1/clients/not-an-id",
        headers=headers,
        json=_client_payload()
    )

    assert response.status_code == 400


def test_put_client_malformed_id_current_behavior(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        method="put"
    )

    response = requests.put(
        f"{base_url}/api/v1/clients/not-an-id",
        headers=headers,
        json=_client_payload()
    )

    assert response.status_code == 500


def test_put_client_without_api_key_returns_401(base_url):
    response = requests.put(
        f"{base_url}/api/v1/clients/1",
        json=_client_payload(1)
    )

    assert response.status_code == 401


def test_put_client_without_permission_returns_403(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        method="put",
        allowed=False
    )

    response = requests.put(
        f"{base_url}/api/v1/clients/1",
        headers=headers,
        json=_client_payload(1)
    )

    assert response.status_code == 403


# endregion


# region DELETE /clients/{id}


def test_delete_client_returns_200(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("client.json")

    client = _first_client(base_url, user_headers)

    headers = _get_headers(
        user_headers,
        method="delete"
    )

    response = requests.delete(
        f"{base_url}/api/v1/clients/{client['id']}",
        headers=headers
    )

    assert response.status_code == 200


def test_delete_client_removes_client(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("client.json")

    client = _first_client(base_url, user_headers)

    headers = _get_headers(
        user_headers,
        method="delete"
    )

    response = requests.delete(
        f"{base_url}/api/v1/clients/{client['id']}",
        headers=headers
    )

    assert response.status_code == 200

    get_response = requests.get(
        f"{base_url}/api/v1/clients/{client['id']}",
        headers=_get_headers(user_headers)
    )

    assert get_response.status_code == 200
    assert get_response.json() is None


@pytest.mark.xfail(
    strict=True,
    reason="Current API returns 200 when client does not exist."
)
def test_delete_nonexistent_client_returns_404(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("client.json")

    headers = _get_headers(
        user_headers,
        method="delete"
    )

    response = requests.delete(
        f"{base_url}/api/v1/clients/999999999",
        headers=headers
    )

    assert response.status_code == 404


def test_delete_client_without_api_key_returns_401(base_url):
    response = requests.delete(
        f"{base_url}/api/v1/clients/1"
    )

    assert response.status_code == 401


def test_delete_client_without_permission_returns_403(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        method="delete",
        allowed=False
    )

    response = requests.delete(
        f"{base_url}/api/v1/clients/1",
        headers=headers
    )

    assert response.status_code == 403


# endregion


# region GET /clients/{id}/orders


def test_get_client_orders_returns_200(
    base_url,
    user_headers
):
    client = _first_client(base_url, user_headers)

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/clients/{client['id']}/orders",
        headers=headers
    )

    assert response.status_code == 200


def test_get_client_orders_returns_list(
    base_url,
    user_headers
):
    client = _first_client(base_url, user_headers)

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/clients/{client['id']}/orders",
        headers=headers
    )

    assert response.status_code == 200

    assert isinstance(response.json(), list)


def test_get_client_orders_schema(
    base_url,
    user_headers
):
    client = _first_client(base_url, user_headers)

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/clients/{client['id']}/orders",
        headers=headers
    )

    assert response.status_code == 200

    for order in response.json():
        Order.model_validate(order)


def test_get_client_orders_without_api_key(base_url):
    response = requests.get(
        f"{base_url}/api/v1/clients/1/orders"
    )

    assert response.status_code == 401


def test_get_client_orders_without_permission(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        allowed=False
    )

    response = requests.get(
        f"{base_url}/api/v1/clients/1/orders",
        headers=headers
    )

    assert response.status_code == 403


# endregion
