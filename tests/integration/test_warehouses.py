import json
import time
from datetime import datetime
from pathlib import Path

import pytest
import requests
from pydantic import BaseModel


REPO_ROOT = Path(__file__).resolve().parents[2]
WAREHOUSES_MODEL_SOURCE = (REPO_ROOT / "api" / "models" / "warehouses.py").read_text(encoding="utf-8")


# region Shared helpers


class Warehouse(BaseModel):
    id: int
    code: str
    name: str
    address: str
    city: str
    zip_code: str
    province: str
    country: str
    contact_name: str
    contact_phone: str
    contact_email: str
    created_at: datetime
    updated_at: datetime


def _get_headers(user_headers, method="get", allowed=True):
    return user_headers(
        resource="warehouses",
        method=method,
        allowed=allowed,
    )


def _first_warehouse(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(
        f"{base_url}/api/v1/warehouses", headers=headers
    )

    assert response.status_code == 200

    body = response.json()
    assert body, "fixture data/warehouse.json is expected to be non-empty"

    return body[0]


# endregion


# region GET /warehouses (collection)


def test_get_warehouses_returns_200_with_valid_response(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/warehouses", headers=headers
    )

    assert response.status_code == 200

    body = response.json()

    assert isinstance(body, list)
    assert len(body) > 0
    assert "id" in body[0]


def test_response_body_matches_documented_schema(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/warehouses", headers=headers
    )

    assert response.status_code == 200

    body = response.json()

    for raw in body:
        Warehouse.model_validate(raw)


def test_response_content_type_is_json(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/warehouses", headers=headers
    )

    assert response.headers.get(
        "Content-Type",
        "",
    ).startswith("application/json")


def test_response_time_is_reasonable(base_url, user_headers):
    headers = _get_headers(user_headers)

    start = time.monotonic()

    response = requests.get(
        f"{base_url}/api/v1/warehouses", headers=headers
    )

    elapsed = time.monotonic() - start

    assert response.status_code == 200
    assert (
        elapsed < 0.5
    ), f"GET /warehouses took {elapsed:.2f}s, which is unreasonably slow"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "ApiRequestHandler does not strip the query string before checking "
        "endpoint permissions. A query string therefore changes paths[0] "
        "from 'warehouses' to e.g. 'warehouses?page=1' and results in 403."
    ),
)
@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"page": 1}, id="pagination-page"),
        pytest.param({"limit": 5}, id="pagination-limit"),
        pytest.param({"sort": "name"}, id="sort-name"),
        pytest.param(
            {"totally_unknown_key": "x"},
            id="unknown-key",
        ),
    ],
)
def test_query_params_are_honoured_or_gracefully_ignored(base_url, user_headers, params):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/warehouses",
        headers=headers,
        params=params
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_query_params_currently_return_403(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/warehouses",
        headers=headers,
        params={"page": 1}
    )

    assert response.status_code == 403
    assert response.text == ""



def test_missing_api_key_is_rejected_with_401(base_url):
    response = requests.get(
        f"{base_url}/api/v1/warehouses"
    )

    assert response.status_code == 401


def test_invalid_api_key_is_rejected_with_401(base_url):
    response = requests.get(
        f"{base_url}/api/v1/warehouses", headers={"API_KEY": "not-a-real-key"}
    )

    assert response.status_code == 401


# endregion


# region GET /warehouses/{id}


def test_get_warehouse_by_id_returns_200_with_correct_resource(base_url, user_headers):
    existing = _first_warehouse(
        base_url, user_headers
    )

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/warehouses/{existing['id']}", headers=headers
    )

    assert response.status_code == 200
    assert response.json() == existing


def test_get_warehouse_by_id_matches_documented_schema(base_url, user_headers):
    existing = _first_warehouse(
        base_url, user_headers
    )

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/warehouses/{existing['id']}", headers=headers
    )

    assert response.status_code == 200

    Warehouse.model_validate(response.json())


@pytest.mark.xfail(
    strict=True,
    reason=(
        "get_warehouse() returns None for an unknown id and the API sends "
        "that value with status 200 instead of returning 404."
    ),
)
def test_get_warehouse_by_nonexistent_id_returns_404(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/warehouses/999999", headers=headers
    )

    assert response.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason=(
        "warehouse_id = int(paths[1]) is not protected against invalid "
        "input, so a non-numeric id results in a 500 instead of 400."
    ),
)
def test_get_warehouse_by_malformed_id_returns_400(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/warehouses/not-an-id", headers=headers
    )

    assert response.status_code == 400


def test_get_warehouse_by_id_requires_authentication(base_url):
    response = requests.get(
        f"{base_url}/api/v1/warehouses/1"
    )

    assert response.status_code == 401



def test_get_warehouse_by_id_response_content_type_is_json(base_url, user_headers):
    existing = _first_warehouse(
        base_url,
        user_headers,
    )

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/warehouses/{existing['id']}", headers=headers
    )

    assert response.headers.get(
        "Content-Type",
        "",
    ).startswith("application/json")


def test_get_warehouse_malformed_id_error_leaks_no_internal_details(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/warehouses/not-an-id", headers=headers
    )

    text_lower = response.text.lower()

    for leak_indicator in (
        "traceback",
        "exception",
        "valueerror",
        'file "',
        "line "
    ):
        assert leak_indicator not in text_lower


# endregion


# region GET /warehouses/{id}/locations


def test_get_warehouse_locations_returns_200(base_url, user_headers):
    existing = _first_warehouse(
        base_url, user_headers
    )

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/warehouses/{existing['id']}/locations", headers=headers
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_warehouse_locations_belong_to_requested_warehouse(base_url, user_headers):
    existing = _first_warehouse(
        base_url, user_headers
    )

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/warehouses/{existing['id']}/locations", headers=headers
    )

    assert response.status_code == 200

    locations = response.json()

    for location in locations:
        assert location["warehouse_id"] == existing["id"]


def test_get_warehouse_locations_requires_authentication(base_url):
    response = requests.get(
        f"{base_url}/api/v1/warehouses/1/locations"
    )

    assert response.status_code == 401



def test_get_warehouse_locations_response_content_type_is_json(base_url, user_headers ):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/warehouses/1/locations", headers=headers
    )

    assert response.headers.get(
        "Content-Type",
        "",
    ).startswith("application/json")


# endregion


# region POST /warehouses


def test_post_warehouse_valid_payload_returns_201(base_url, user_headers, preserve_data_files):
    preserve_data_files("warehouse.json")

    headers = _get_headers(
        user_headers, method="post"
    )

    payload = {
        "id": 555555,
        "code": "TEST-WH",
        "name": "Test Warehouse",
        "address": "1 Test Street",
        "city": "Testville",
        "zip_code": "0000AA",
        "province": "Test",
        "country": "Netherlands",
        "contact_name": "Test Person",
        "contact_phone": "+31000000000",
        "contact_email": "test@example.com",
    }

    response = requests.post(
        f"{base_url}/api/v1/warehouses", headers=headers, json=payload
    )

    assert response.status_code == 201


@pytest.mark.xfail(
    strict=True,
    reason=(
        "POST /warehouses returns 201 with an empty body. "
        "The API does not return the created warehouse."
    ),
)
def test_post_warehouse_returns_created_resource(base_url, user_headers, preserve_data_files):
    preserve_data_files("warehouse.json")

    headers = _get_headers(
        user_headers, method="post"
    )

    payload = {
        "id": 555556,
        "code": "TEST-WH-2",
        "name": "Test Warehouse 2",
        "address": "2 Test Street",
        "city": "Testville",
        "zip_code": "0000AA",
        "province": "Test",
        "country": "Netherlands",
        "contact_name": "Test Person",
        "contact_phone": "+31000000000",
        "contact_email": "test2@example.com",
    }

    response = requests.post(
        f"{base_url}/api/v1/warehouses", headers=headers, json=payload
    )

    assert response.status_code == 201

    body = response.json()

    Warehouse.model_validate(body)

    for key, value in payload.items():
        assert body[key] == value


@pytest.mark.xfail(
    strict=True,
    reason=(
        "The warehouse model does not validate required fields. "
        "An empty payload is accepted and stored instead of returning 400/422."
    ),
)
def test_post_warehouse_missing_required_fields_returns_400(base_url, user_headers, preserve_data_files):
    preserve_data_files("warehouse.json")

    headers = _get_headers(
        user_headers, method="post"
    )

    response = requests.post(
        f"{base_url}/api/v1/warehouses", headers=headers, json={}
    )

    assert response.status_code in (400, 422)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "The API stores JSON values without validating their types. "
        "An invalid id type is accepted instead of returning 400/422."
    ),
)
def test_post_warehouse_invalid_field_type_is_rejected(base_url, user_headers, preserve_data_files):
    preserve_data_files("warehouse.json")

    headers = _get_headers(
        user_headers, method="post"
    )

    response = requests.post(
        f"{base_url}/api/v1/warehouses", headers=headers,
        json={
            "id": "not-an-int",
            "name": "Bad Type Warehouse"
        }
    )

    assert response.status_code in (400, 422)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Warehouses.add_warehouse() does not check for duplicate ids or "
        "codes, so a duplicate warehouse is accepted instead of 409/400."
    ),
)
def test_post_warehouse_duplicate_id_returns_conflict(base_url, user_headers, preserve_data_files):
    preserve_data_files("warehouse.json")

    existing = _first_warehouse(
        base_url, user_headers
    )

    headers = _get_headers(
        user_headers, method="post"
    )

    response = requests.post(
        f"{base_url}/api/v1/warehouses", headers=headers,
        json={
            **existing,
            "name": "Duplicate Warehouse"
        }
    )

    assert response.status_code == 409


@pytest.mark.xfail(
    strict=True,
    reason="API does not add new warehouse because save() uses a newly loaded Warehouses instance"
)
def test_post_warehouse_is_immediately_retrievable(base_url, user_headers, preserve_data_files):
    preserve_data_files("warehouse.json")

    headers = _get_headers(
        user_headers, method="post"
    )

    payload = {
        "id": 555557,
        "code": "TEST-555557",
        "name": "Retrievable Warehouse",
        "address": "Teststraat 1",
        "city": "Veghel",
        "zip_code": "5461AA",
        "province": "Noord-Brabant",
        "country": "Netherlands",
        "contact_name": "Test Contact",
        "contact_phone": "0612345678",
        "contact_email": "test@example.com",
        "created_at": "",
        "updated_at": "",
    }

    create_response = requests.post(
        f"{base_url}/api/v1/warehouses", headers=headers, json=payload
    )

    assert create_response.status_code == 201

    get_headers = _get_headers(user_headers)

    get_response = requests.get(
        f"{base_url}/api/v1/warehouses/555557", headers=get_headers
    )

    assert get_response.status_code == 200
    assert get_response.json() is not None
    assert get_response.json()["name"] == "Retrievable Warehouse"


def test_post_warehouse_requires_authentication(base_url):
    response = requests.post(
        f"{base_url}/api/v1/warehouses",
        json={"name": "No Auth Warehouse"},
    )

    assert response.status_code == 401


def test_post_warehouse_insufficient_permissions_returns_403(base_url, user_headers):
    headers = _get_headers(
        user_headers, method="post", allowed=False
    )

    response = requests.post(
        f"{base_url}/api/v1/warehouses", headers=headers, json={"name": "Forbidden Warehouse"}
    )

    assert response.status_code == 403


@pytest.mark.xfail(
    strict=True,
    reason=(
        "do_POST does not inspect Content-Type before parsing the body. "
        "text/plain is accepted like application/json."
    ),
)
def test_post_warehouse_wrong_content_type_is_rejected(base_url, user_headers, preserve_data_files):
    preserve_data_files("warehouse.json")

    headers = {
        **_get_headers(
            user_headers,
            method="post",
        ),
        "Content-Type": "text/plain",
    }

    response = requests.post(
        f"{base_url}/api/v1/warehouses", headers=headers,
        data=json.dumps(
            {"name": "Plain Text Warehouse"}
        )
    )

    assert response.status_code in (400, 415)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Malformed JSON raises JSONDecodeError and is caught by the "
        "generic 500 handler instead of returning 400/422."
    ),
)
def test_post_warehouse_malformed_json_body_returns_400(base_url, user_headers, preserve_data_files):
    preserve_data_files("warehouse.json")

    headers = {
        **_get_headers(
            user_headers,
            method="post",
        ),
        "Content-Type": "application/json"
    }

    response = requests.post(
        f"{base_url}/api/v1/warehouses", headers=headers, data="{not valid json"
    )

    assert response.status_code in (400, 422)


def test_post_warehouse_malformed_json_body_leaks_no_internal_details(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("warehouse.json")

    headers = {
        **_get_headers(
            user_headers,
            method="post",
        ),
        "Content-Type": "application/json",
    }

    response = requests.post(
        f"{base_url}/api/v1/warehouses",
        headers=headers,
        data="{not valid json",
    )

    text_lower = response.text.lower()

    for leak_indicator in (
        "traceback",
        "exception",
        "jsondecodeerror",
        'file "',
        "line ",
    ):
        assert leak_indicator not in text_lower


# endregion


# region PUT /warehouses/{id}


def test_put_warehouse_valid_payload_returns_200(base_url, user_headers, preserve_data_files):
    preserve_data_files("warehouse.json")

    existing = _first_warehouse(
        base_url, user_headers
    )

    headers = _get_headers(
        user_headers, method="put"
    )

    updated = {
        **existing, "name": "Updated Warehouse Name"
    }

    response = requests.put(
        f"{base_url}/api/v1/warehouses/{existing['id']}", headers=headers, json=updated
    )

    assert response.status_code == 200


def test_put_warehouse_update_is_persisted(base_url, user_headers, preserve_data_files):
    preserve_data_files("warehouse.json")

    existing = _first_warehouse(
        base_url, user_headers
    )

    headers = _get_headers(
        user_headers, method="put"
    )

    updated = {
        **existing, "name": "Persisted Warehouse Name"
    }

    put_response = requests.put(
        f"{base_url}/api/v1/warehouses/{existing['id']}", headers=headers, json=updated
    )

    assert put_response.status_code == 200

    get_headers = _get_headers(user_headers)

    get_response = requests.get(
        f"{base_url}/api/v1/warehouses/{existing['id']}", headers=get_headers
    )

    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Persisted Warehouse Name"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "update_warehouse() does nothing when the id does not exist, "
        "while the API still responds with 200. Expected behavior: 404."
    ),
)
def test_put_warehouse_nonexistent_id_returns_404(base_url, user_headers, preserve_data_files):
    preserve_data_files("warehouse.json")

    headers = _get_headers(
        user_headers, method="put"
    )

    response = requests.put(
        f"{base_url}/api/v1/warehouses/999999", headers=headers,
        json={
            "id": 999999,
            "name": "Ghost Warehouse",
        },
    )

    assert response.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason=(
        "int(paths[1]) is not guarded, so a malformed warehouse id "
        "causes 500 instead of the expected 400."
    ),
)
def test_put_warehouse_malformed_id_returns_400(base_url, user_headers, preserve_data_files):
    preserve_data_files("warehouse.json")

    headers = _get_headers(
        user_headers, method="put"
    )

    response = requests.put(
        f"{base_url}/api/v1/warehouses/not-an-id", headers=headers, json={"name": "Invalid ID Warehouse"}
    )

    assert response.status_code == 400


def test_put_warehouse_replaces_the_whole_record_per_source():
    assert "self.data[i] = warehouse" in WAREHOUSES_MODEL_SOURCE


def test_put_warehouse_requires_authentication(base_url):
    response = requests.put(
        f"{base_url}/api/v1/warehouses/1", json={"name": "No Auth Warehouse"}
    )

    assert response.status_code == 401


def test_put_warehouse_insufficient_permissions_returns_403(base_url, user_headers):
    headers = _get_headers(
        user_headers, method="put", allowed=False
    )

    response = requests.put(
        f"{base_url}/api/v1/warehouses/1", headers=headers, json={"name": "Forbidden Warehouse"}
    )

    assert response.status_code == 403


# endregion


# region DELETE /warehouses/{id}

@pytest.mark.xfail(
    strict=True,
    reason="API returns 500 when deleting a warehouse with a valid ID"
)
def test_delete_warehouse_valid_id_returns_200(base_url, user_headers, preserve_data_files):
    preserve_data_files("warehouse.json")

    existing = _first_warehouse(
        base_url, user_headers
    )

    headers = _get_headers(
        user_headers, method="delete"
    )

    response = requests.delete(
        f"{base_url}/api/v1/warehouses/{existing['id']}", headers=headers
    )

    assert response.status_code in (200, 204)


@pytest.mark.xfail(
    strict=True,
    reason="API does not persist warehouse changes because save() uses a newly loaded Warehouses instance"
)
def test_delete_warehouse_resource_is_actually_gone(base_url, user_headers, preserve_data_files):
    preserve_data_files("warehouse.json")

    existing = _first_warehouse(
        base_url, user_headers
    )

    delete_headers = _get_headers(
        user_headers, method="delete"
    )

    delete_response = requests.delete(
        f"{base_url}/api/v1/warehouses/{existing['id']}", headers=delete_headers
    )

    assert delete_response.status_code in (200, 204)

    get_headers = _get_headers(user_headers)

    get_response = requests.get(
        f"{base_url}/api/v1/warehouses/{existing['id']}", headers=get_headers
    )

    assert get_response.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason=(
        "remove_warehouse() silently does nothing for a nonexistent id "
        "and the API still returns 200. Expected behavior: 404."
    ),
)
def test_delete_warehouse_nonexistent_id_returns_404(base_url, user_headers, preserve_data_files):
    preserve_data_files("warehouse.json")

    headers = _get_headers(
        user_headers, method="delete"
    )

    response = requests.delete(
        f"{base_url}/api/v1/warehouses/999999", headers=headers
    )

    assert response.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason=(
        "int(paths[1]) is not guarded, so a malformed warehouse id "
        "causes 500 instead of the expected 400."
    ),
)
def test_delete_warehouse_malformed_id_returns_400(base_url, user_headers, preserve_data_files):
    preserve_data_files("warehouse.json")

    headers = _get_headers(
        user_headers, method="delete"
    )

    response = requests.delete(
        f"{base_url}/api/v1/warehouses/not-an-id", headers=headers
    )

    assert response.status_code == 400


@pytest.mark.xfail(
    strict=True,
    reason=(
        "The second DELETE is expected to return 404, but "
        "remove_warehouse() silently does nothing and the handler "
        "always responds with 200."
    ),
)
def test_delete_warehouse_repeated_delete_returns_404_not_200(base_url, user_headers, preserve_data_files):
    preserve_data_files("warehouse.json")

    existing = _first_warehouse(
        base_url, user_headers,
    )

    headers = _get_headers(
        user_headers, method="delete"
    )

    first = requests.delete(
        f"{base_url}/api/v1/warehouses/{existing['id']}", headers=headers
    )

    second = requests.delete(
        f"{base_url}/api/v1/warehouses/{existing['id']}", headers=headers
    )

    assert first.status_code in (200, 204)
    assert second.status_code == 404


def test_delete_warehouse_requires_authentication(base_url):
    response = requests.delete(
        f"{base_url}/api/v1/warehouses/1"
    )

    assert response.status_code == 401


def test_delete_warehouse_insufficient_permissions_returns_403(base_url, user_headers):
    headers = _get_headers(user_headers, method="delete", allowed=False)

    response = requests.delete(
        f"{base_url}/api/v1/warehouses/1", headers=headers
    )

    assert response.status_code == 403


# endregion