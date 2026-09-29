import json
import time
from pathlib import Path
from urllib import response

import pytest
import requests

from schemas import Location

REPO_ROOT = Path(__file__).resolve().parents[2]
INVENTORIES_MODEL_SOURCE = (REPO_ROOT / "api" / "models" / "inventories.py").read_text(
    encoding="utf-8"
)

def _get_headers(user_headers, method="get", allowed = True):
    return user_headers(resource ="locations", method = method, allowed = allowed)

def _get_locations(base_url, user_headers, params= None):
    headers = _get_headers(user_headers)
    return requests.get(f"{base_url}/api/v1/locations", headers = headers, params=params)

def _first_location(base_url, user_headers):
    response = _get_locations(base_url, user_headers)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body, "fixture data/location.json is expected to be non-empty"
    return body[0]

def _location_by_id(base_url, user_headers, location_id):
    headers = _get_headers(user_headers)
    return requests.get(f"{base_url}/api/v1/locations/{location_id}", headers=headers)

def _error_text_does_not_leak(response):
    text_lower = response.text.lower()
    for leak in ("traceback", "stack trace", "exception", "internal server", "sql", "file", "line"):
        assert leak not in text_lower

def _request_location(base_url, user_headers, method, path, allowed=True, **kwargs):
    headers = _get_headers(user_headers, method=method, allowed=allowed,)
    return requests.request(method, f"{base_url}{path}", headers=headers, **kwargs,)

def _valid_location_payload():
    return {
        "id": 999991,
        "warehouse_id": 1,
        "code": "TEST-LOC-999991",
        "name": "Test Location 999991",
    }

#region GET location
def test_get_location_returns_200_valid_response(base_url, user_headers):
    response= _get_locations(base_url, user_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_locations_response_matches_documented_schema(base_url, user_headers):
    response = _get_locations(base_url, user_headers)

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) > 0
    assert "id" in body[0]
    assert "warehouse_id" in body[0]
    assert "code" in body[0]
    assert "name" in body[0]

def test_get_location_response_matches_documented_schema(base_url, user_headers):
    response = _get_headers(base_url, user_headers)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    for location in body:
        Location.modell(location)

def test_get_locations_response_time_is_reasonable(base_url, user_headers):
    headers = _get_headers(user_headers)
    start = time.monotonic()
    response = requests.get(f"{base_url}/api/v1/locations", headers= headers)
    elapsed = time.monotonic() - start
    assert response.status_code != 500
    assert elapsed < 0.5, (f"GET /locations took {elapsed:.2f}s")

def test_get_locations_requires_authentication(base_url, user_headers):
    response = requests.get(f"{base_url}/api/v1/locations")
    assert response.status_code == 401

def test_get_locations_insufficient_permissions_returns_403(base_url, user_headers):
    response = _request_location(base_url, user_headers, method = "get", path = "/api/v1/locations", allowed=False)
    assert response.status_code == 403

def test_get_locations_response_content_type_is_json(base_url, user_headers,):
    response = _get_locations(base_url, user_headers)
    assert response.status_code == 200
    assert response.headers.get("Content-Type", "",).startswith("application/json")

def test_get_locations_error_does_not_leak_internal_data(base_url,):
    response = requests.get(f"{base_url}/api/v1/locations")
    assert response.status_code == 401
    _error_text_does_not_leak(response)

def test_get_locations_support_pagination(base_url,user_headers,):
    response = _get_locations(base_url, user_headers, params={"page": 1, "limit": 2,},)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) <= 2


@pytest.mark.parametrize("filter_type",["warehouse_id", "code",],)
def test_get_locations_support_filtering(base_url, user_headers,filter_type,):
    existing = _first_location(base_url, user_headers,)
    response = _get_locations(base_url, user_headers, params={filter_type: existing[filter_type],},)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    for location in body:
        assert location[filter_type] == existing[filter_type]

def test_get_locations_supports_sorting(base_url, user_headers,):
    response = _get_locations(base_url, user_headers, params={"sort": "id",},)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    ids = [location["id"] for location in body]
    assert ids == sorted(ids)

def test_get_locations_empty_result_returns_200_empty_array(base_url, user_headers):
    response = _get_locations(base_url, user_headers,params={"warehouse_id": 999999999,},)
    assert response.status_code == 200
    assert response.json() == []

def test_get_locations_invalid_query_param_does_not_return_500(base_url, user_headers,):
    response = _get_locations(base_url, user_headers,params={"page": -1,},)
    assert response.status_code != 500


def test_get_locations_unknown_query_param_is_handled(base_url, user_headers,):
    response = _get_locations(base_url, user_headers, params={"unknown_parameter": "test",},)
    assert response.status_code in (200, 400, 422)
    assert response.status_code != 500

#endregion

#region GET location id
def test_get_location_by_id_returns_200(base_url, user_headers):
    existing = _first_location(base_url, user_headers)
    response = _location_by_id(base_url, user_headers, existing["id"])
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)
    assert body["id"] == existing["id"]

def test_get_location_by_id_matches_schema(base_url, user_headers):
    existing = _first_location(base_url, user_headers)
    response = _location_by_id(base_url, user_headers, existing["id"])
    assert response.status_code == 200
    body = response.json()
    Location.model_validate(body)
    assert body["id"] == existing["id"]

def test_get_location_by_id_nonexistent_returns_404(base_url, user_headers):
    response = _location_by_id(base_url, user_headers, 99999999)
    assert response.statu
    
def test_get_location_by_id_malformed_id_does_not_return_500(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/locations/not-an-id",headers=headers)
    assert response.status_code != 500

def test_get_location_by_id_response_contains_documented_fields(base_url, user_headers,):
    existing = _first_location(base_url, user_headers,)
    response = _location_by_id(base_url, user_headers, existing["id"],)
    assert response.status_code == 200
    body = response.json()
    assert "id" in body
    assert "warehouse_id" in body
    assert "code" in body
    assert "name" in body
    assert "created_at" in body
    assert "updated_at" in body

def test_get_location_by_id_response_content_type_is_json(base_url, user_headers):
    existing = _first_location(base_url, user_headers)
    response = _location_by_id(base_url, user_headers, existing["id"],)
    assert response.status_code == 200
    assert response.headers.get("Content-Type", "").startswith("application.json")

def test_get_location_by_id_requires_authentication(base_url):
    response = requests.get(f"{base_url}/api/v1/locations/1")
    assert response.status_code == 401

def test_get_location_by_id_insufficient_permissions_returns_403(base_url, user_headers):
    response = _request_location(base_url, user_headers, method="get", path="/api/v1/locations/1", allowed=False)
    assert response.status_code == 403

def test_get_location_by_id_error_does_not_leak_internal_data(base_url, user_headers):
    response = _location_by_id(base_url, user_headers, 999999999)
    assert response.status_code == 404
    _error_text_does_not_leak(response)

#endregion


#region POST location
def test_post_location_returns_201(base_url, user_headers, preserve_data_files):
    preserve_data_files("location.json")
    headers = _get_headers(user_headers, method="post")
    payload = _valid_location_payload()
    response = requests.post(f"{base_url}/api/v1/locations", headers=headers, json=payload)
    assert response.status_code == 201
    assert (response.headers.get("Location") or response.content)
    if response.content:
        body = response.json()
        assert isinstance(body, dict)
        assert "id" in body

def test_post_location_requires_authentication(base_url):
    response = requests.post(f"{base_url}/api/v1/locations", json=_valid_location_payload())
    assert response.status_code == 401

def test_post_location_insufficient_permission_returns_403(base_url, user_headers,):
    response = _request_location(base_url, user_headers, method="post", path="/api/v1/locations", allowed=False, json=_valid_location_payload(),)
    assert response.status_code == 403

def test_post_location_requires_application_json(base_url, user_headers, preserve_data_files):
    preserve_data_files("location.json")
    headers = _get_headers(user_headers, method="post")
    headers["Content-Type"] = "text/plain"
    response = requests.post(f"{base_url}/api/v1/locations", headers=headers, data="This is not a json file")
    assert response.status_code in (400, 415, 422)

def test_post_location_accepts_application_json(base_url, user_headers, preserve_data_files,):
    preserve_data_files("location.json")
    headers = _get_headers(user_headers, method="post",)
    headers["Content-Type"] = "application/json"
    response = requests.post(f"{base_url}/api/v1/locations", headers=headers, json=_valid_location_payload(),)
    assert response.status_code != 415

def test_post_location_missing_required_field_is_rejected(base_url, user_headers, preserve_data_files,):
    preserve_data_files("location.json")
    headers = _get_headers(user_headers, method="post",)
    payload = _valid_location_payload()
    payload.pop("code")
    response = requests.post(f"{base_url}/api/v1/locations", headers=headers, json=payload,)
    assert response.status_code in (400, 422,)


@pytest.mark.parametrize("field,value",[("id", "not-an-int"), ("warehouse_id", "not-an-int"), ("code", 12345), ("name", 12345),],)
def test_post_location_rejects_invalid_field_type(base_url, user_headers, preserve_data_files, field, value,):
    preserve_data_files("location.json")
    headers = _get_headers(user_headers, method="post",)
    payload = _valid_location_payload()
    payload[field] = value
    response = requests.post(f"{base_url}/api/v1/locations", headers=headers,json=payload,)
    assert response.status_code in (400, 422,)

def test_post_location_duplicate_id_is_handled(base_url, user_headers,preserve_data_files):
    preserve_data_files("location.json")
    existing = _first_location(base_url, user_headers,)
    headers = _get_headers(user_headers, method="post",)
    payload = _valid_location_payload()
    payload["id"] = existing["id"]
    response = requests.post(f"{base_url}/api/v1/locations", headers=headers, json=payload,)
    assert response.status_code in (400, 409, 422,)

def test_post_location_unexpected_field_is_handled_consistently(base_url,user_headers, preserve_data_files,):
    preserve_data_files("location.json")
    headers = _get_headers(user_headers, method="post",)
    payload = _valid_location_payload()
    payload["unexpected_field"] = ("should-not-be-accepted")
    response = requests.post(f"{base_url}/api/v1/locations", headers=headers,json=payload,)
    assert response.status_code in (201, 400, 422,)


def test_post_location_invalid_foreign_key_is_rejected(base_url, user_headers, preserve_data_files,):
    preserve_data_files("location.json")
    headers = _get_headers(user_headers, method="post",)
    payload = _valid_location_payload()
    payload["warehouse_id"] = 999999999
    response = requests.post(f"{base_url}/api/v1/locations", headers=headers, json=payload,)
    assert response.status_code in (400, 404, 409, 422,)


def test_post_location_is_immediately_retrievable(base_url, user_headers, preserve_data_files,):
    preserve_data_files("location.json")
    headers = _get_headers(user_headers, method="post",)
    payload = _valid_location_payload()
    response = requests.post(f"{base_url}/api/v1/locations", headers=headers, json=payload,)
    assert response.status_code == 201
    created_id = None
    if response.content:
        body = response.json()
        if isinstance(body, dict):
            created_id = body.get("id")

    if created_id is None:
        location = response.headers.get("Location")
        assert location, ("Created location must expose its id in the response body or Location header.")
        created_id = int(location.rstrip("/").split("/")[-1])

    get_response = _location_by_id(base_url, user_headers, created_id,)
    assert get_response.status_code == 200
    created = get_response.json()
    assert created["id"] == created_id
    assert created["warehouse_id"] == payload["warehouse_id"]
    assert created["code"] == payload["code"]
    assert created["name"] == payload["name"]

def test_post_location_response_content_type_is_json(base_url, user_headers, preserve_data_files,):
    preserve_data_files("location.json")
    headers = _get_headers(user_headers, method="post",)
    response = requests.post(f"{base_url}/api/v1/locations", headers=headers, json=_valid_location_payload(),)
    if response.status_code == 201:
        assert response.headers.get("Content-Type", "",).startswith("application/json")

#endregion

#region PUT location id
def test_put_location_requires_authentication(base_url):
    response = requests.put(f"{base_url}/api/v1/locations/1", json={})
    assert response.status_code == 401

def test_put_location_insufficient_permissions_return_403(base_url, user_headers):
    response = requests.location(base_url, user_headers, method ="put", path="/api/v1/locations/1", allowed = False, json= {})
    assert response.status_code == 403

def test_pit_location_valid_payload_returns_200(base_url, user_headers, preserve_data_files):
    preserve_data_files("location.json")
    existing = _first_location(base_url, user_headers)
    headers = _get_headers(user_headers, method="put")
    payload = {
        "id": existing["id"],
        "warehouse_id": existing["warehouse_id"],
        "code": existing["code"],
        "name": "Updated Location Test",
        "created_at": existing["created_at"],
        "updated_at": existing["updated_at"],
    }
    response = requests.put(f"{base_url}/api/v1/locations/{existing['id']}", headers=headers, json=payload,)
    assert response.status_code == 200

def test_put_location_nonexistent_id_returns_404(base_url, user_headers):
    headers = _get_headers(user_headers, method="put")
    response = requests.put(f"{base_url}/api/v1/locations/99999999", headers = headers, json=_valid_location_payload())

def test_put_locations_malformed_id_does_not_return_500(base_url, user_headers):
    headers = _get_headers(user_headers, method="put")
    response = requests.put(f"{base_url}/api/v1/locations/not-an-id", headers=headers, json = _valid_location_payload())
    assert response.status_code != 500

def test_put_location_rejects_invalid_field_value(base_url, user_headers, preserve_data_files,):
    preserve_data_files("location.json")
    existing = _first_location(base_url, user_headers,)
    headers = _get_headers(user_headers, method="put",)
    payload = {
        "id": existing["id"],
        "warehouse_id": "not-an-int",
        "code": existing["code"],
        "name": existing["name"],
        "created_at": existing["created_at"],
        "updated_at": existing["updated_at"],
    }
    response = requests.put(f"{base_url}/api/v1/locations/{existing['id']}", headers=headers, json=payload,)
    assert response.status_code in (400, 422,)

def test_put_location_rejects_invalid_foreign_key(base_url, user_headers,preserve_data_files,):
    preserve_data_files("location.json")
    existing = _first_location(base_url, user_headers,)
    headers = _get_headers(user_headers, method="put",)
    payload = {
        "id": existing["id"],
        "warehouse_id": 999999999,
        "code": existing["code"],
        "name": existing["name"],
        "created_at": existing["created_at"],
        "updated_at": existing["updated_at"],
    }
    response = requests.put(f"{base_url}/api/v1/locations/{existing['id']}",headers=headers, json=payload,)
    assert response.status_code in (400, 404, 409, 422,)

def test_put_location_update_is_persisted(base_url, user_headers, preserve_data_files,):
    preserve_data_files("location.json")
    existing = _first_location(base_url, user_headers,)
    headers = _get_headers(user_headers, method="put",)
    payload = {
        "id": existing["id"],
        "warehouse_id": existing["warehouse_id"],
        "code": existing["code"],
        "name": "UPDATED-LOCATION-TEST-999",
        "created_at": existing["created_at"],
        "updated_at": existing["updated_at"],
    }
    response = requests.put(f"{base_url}/api/v1/locations/{existing['id']}", headers=headers, json=payload,)
    assert response.status_code == 200
    get_response = _location_by_id(base_url, user_headers, existing["id"],)
    assert get_response.status_code == 200
    updated = get_response.json()
    assert updated["id"] == existing["id"]
    assert updated["name"] == "UPDATED-LOCATION-TEST-999"

def test_put_location_partial_payload_behavior(base_url, user_headers, preserve_data_files,):
    preserve_data_files("location.json")
    existing = _first_location(base_url, user_headers,)
    headers = _get_headers(user_headers, method="put",)
    payload = {"name": "PARTIAL-UPDATE-TEST",}
    response = requests.put(f"{base_url}/api/v1/locations/{existing['id']}", headers=headers, json=payload,)
    assert response.status_code in (200, 400, 422,)

def test_put_location_response_content_type_is_json(base_url, user_headers, preserve_data_files,):
    preserve_data_files("location.json")
    existing = _first_location(base_url, user_headers,)
    headers = _get_headers(user_headers, method="put",)
    payload = {
        "id": existing["id"],
        "warehouse_id": existing["warehouse_id"],
        "code": existing["code"],
        "name": "Updated Location",
        "created_at": existing["created_at"],
        "updated_at": existing["updated_at"],
    }
    response = requests.put(f"{base_url}/api/v1/locations/{existing['id']}", headers=headers, json=payload,)
    if response.status_code == 200:
        assert response.headers.get("Content-Type", "",).startswith("application/json")

#endregion


#region PUT location id
def test_put_location_requires_authentication(base_url, user_headers):
    response = requests.put(f"{base_url}/api/v1/locations/1", json={})
    assert response.status_code == 401

def test_put_locations_insufficient_permissions_returns_403(base_url, user_headers):
    response = _request_location(base_url, user_headers, method ="put",path="/api/v1/loctions/1", allowed =False, json ={})
    assert response.status_code == 403

#endregion