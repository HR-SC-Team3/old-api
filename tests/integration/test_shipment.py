import json
import time
from datetime import datetime
from pathlib import Path
from urllib import response

import pytest
import requests
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[2]
INVENTORIES_MODEL_SOURCE = (REPO_ROOT / "api" / "models" / "shipments.py").read_text(
    encoding="utf-8"
)

class Shipment(BaseModel):
    id: int
    reference: str
    order_id: int
    shipment_date: datetime
    shipment: type
    shipment_status: str
    carrier_name: str
    shipping_method: str
    payment_type: str
    created_at: datetime
    update_at: datetime

def _get_headers(user_headers, method="get", allowed=True):
    return user_headers(resource="shipments", method=method, allowed=allowed)

def _get_shipment(base_url, user_headers):
    headers = _get_headers(user_headers)
    body = requests.get(f"{base_url}/api/v1/shipments", headers=headers).json()
    assert body, "fixture data/inventory.json is expected to be non-empty"
    return body[0]

def _first_shipment(base_url, user_headers):
    response = _get_shipment(base_url, user_headers)

    assert response.status_code == 200
    body = response.json()

    assert isinstance(body, list)
    assert body, "fixture shipment.json is expected not to be empty"
    return body [0]

def _shipment_by_id(base_url, user_headers, shipment_id):
    headers= _get_headers(user_headers)
    return requests.get(f"{base_url}/api/v1/shipments/{shipment_id}", headers= headers)

def _error_text_does_not_leak(response):
    text_lower = response.text.lower()

    for leak in ("traceback", "stack trace", "exception", "internal server", "sql", "file","line"):
        assert leak not in text_lower

#region GET shipment

def test_get_shipment_returns_200_with_valid_response(base_url, user_headers):
    response = _get_shipment(base_url, user_headers)
    assert response.status == 200

def test_get_shipments_response_matches_documented_schema(base_url, user_headers):
    response = _get_shipment(base_url, user_headers)
    assert response.status == 200

    body = response.json()

    assert isinstance(body, list)
    assert len(body) > 0 
    
    assert "id" in body[0]
    assert "reference" in body[0]
    assert "order_id" in body[0]


def test_get_shipment_response_matches_documented_schema(base_url, user_headers):
    response = _get_shipment(base_url, user_headers)
    assert response.status == 200

    body = response.json()

    assert isinstance(body, list)
    for shipment in body:
        Shipment.model_validate(shipment)


def test_get_shipments_response_time_is_reasonable(base_url, user_headers):
    headers = _get_headers(user_headers)
    start = time.monotonic()
    response = requests.get(f"{base_url}/api/1/shipments", headers = headers)
    elapsed = time.monotonic() - start
    assert response.status_code != 500
    assert elapsed < 0.5, (f"GET /shipments took {elapsed:.2f}s")

def test_get_shipments_requires_authentiction(base_url):
    response = requests.get(f"{base_url}/api/v1/shipments")
    assert response.status_code == 401

def test_get_shipment_insufficient_permissions_returns_403(base_url, user_headers):
    headers= _get_headers(user_headers, method = "get", allowed = False)
    response = requests.get(f"{base_url}/api/1/shipments", headers = headers)
    assert response.status_code== 403

def test_get_shipment_response_content_type_is_json(base_url, user_headers):
    response = _get_headers(base_url, user_headers)
    assert response.status_code == 200
    assert response.headers.get("Content-type","",).startswith("application/json")

def test_get_shipments_error_does_not_leak_internal_data(base_url, user_headers):
    response = requests.get(f"{base_url}/api/v1/shipments")
    assert response.status_code == 401

def test_get_shipment_support_pagination(base_url, user_headers):
    headers= _get_headers(user_headers, method = "get", allowed = False)
    response = requests.get(f"{base_url}/api/1/shipments", headers = headers, params = {"page": 1, "limit": 2},)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) <= 2

@pytest.mark.parametrize(
    "filter_type", ["order_id", "shipment_status",],)

def test_get_shipment_support_filtering(base_url, user_headers, filter_type):
    existing = _first_shipment(base_url, user_headers)
    response = _get_shipment(base_url, user_headers, params ={"sort": "id"})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    for shipment in body:
        assert shipment[filter_type] == existing[filter_type]


def test_get_shipments_supports_sorting(base_url, user_headers,):
    response = _get_shipment(base_url, user_headers, params={"sort": "id",},)

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    ids = [shipment["id"] for shipment in body]
    assert ids == sorted(ids)

def test_get_shipments_empty_result_returns_200_empty_array(base_url, user_headers):
    response = _get_shipment(base_url, user_headers, params={"order_id": 99999999,},)
    assert response.status_code == 200
    assert response.json() == []


def test_get_shipment_invalid_query_param_does_not_return_500(base_url, user_headers):
    response = _get_shipment(base_url, user_headers, params ={"page": -1,},)
    assert response.status_code != 500

#endregion

# region POST shipment

def _valid_shipment_payload():
    return {
        "reference": "TEST-SHP-999991",
        "order_id": 1,
        "shipment_date": "2025-03-05T18:51:53Z",
        "shipment_type": "Outgoing",
        "shipment_status": "Scheduled",
        "carrier_name": "Test Carrier",
        "shipping_method": "Standard",
        "payment_type": "Automated",
        }


def test_post_shipment_returns_201(base_url, user_headers, preserve_data_files):
    preserve_data_files("shipment.json")

    headers = _get_headers(user_headers, method="post")
    payload = _valid_shipment_payload

    response = requests.post( f"{base_url}/api/v1/shipments", headers=headers, json=payload,)
    assert response.status_code == 201
    assert response.headers.get("Location") or response.content

    if response.content:
        body = response.json()
        assert isinstance(body, dict)
        assert "id" in body

def test_post_shipments_requires_authentication(base_url):
    response = requests.post(f"{base_url}/api/v1/shipments", json=_valid_shipment_payload(),)

    assert response.status_code == 401

def test_post_shipment_insufficient_permission_returns_403(base_url, user_headers):
    headers = _get_headers(user_headers, method="post", allowed =False)
    response = requests.post(f"{base_url}/api/v1/shipments", headers=headers, json=_valid_shipment_payload(),)
    assert response.status_code == 403


def test_post_shipment_requires_application_json(base_url, user_headers, preserve_data_files):
    preserve_data_files("shipment.json")
    headers = _get_headers(user_headers, method = "post")
    headers["Content-Type"] ="text/plain"
    response = requests.post(f"{base_url}/api/v1/shipments", headers=headers, data="this is not json",)
    assert response.status_code in (400, 415, 422)

def test_post_shipment_accepts_application_json(base_url, user_headers, preserve_data_files):
    preserve_data_files("shipment.json")
    headers = _get_headers(user_headers, method = "post")
    headers["Content-Type"] ="application/json"
    response = requests.post(f"{base_url}/api/v1/shipments", headers=headers, json= _valid_shipment_payload,)
    assert response.status_code != 415

def test_post_shipment_missing_required_field_is_rejected(base_url, user_headers, preserve_data_files):
    preserve_data_files("shipment.json")
    headers = _get_headers(user_headers, method = "post")
    payload = _valid_shipment_payload()
    payload.pop("reference")
    response = requests.post(f"{base_url}/api/v1/shipments", headers=headers, json=payload,)
    assert response.status_code in (400, 422)

def test_post_shipment_rejects_invalid_value(base_url, user_headers, preserve_data_files):
    preserve_data_files("shipment.json")
    headers = _get_headers(user_headers, method = "post")
    payload = _valid_shipment_payload()
    payload["shipment_status"] = "NOT_A_REAL_STATUS"
    response = requests.post(f"{base_url}/api/v1/shipments", headers=headers, json=payload,)
    assert response.status_code in (400, 422)

def test_post_shipment_duplicate_reference_is_handled(base_url, user_headers, preserve_data_files):
    preserve_data_files("shipment.json")
    headers = _get_headers(user_headers, method="post")
    existing = _first_shipment(base_url, user_headers)
    payload = _valid_shipment_payload()
    payload["reference"] = existing["reference"]
    response = requests.post(f"{base_url}/api/v1/shipments", headers=headers, json=payload,)
    assert response.status_code in (400, 409, 422)

def test_post_shipment_unexpected_field_is_handled_consistently(base_url, user_headers, preserve_data_files):
    preserve_data_files("shipment.json")
    headers = _get_headers(user_headers, method = "post")
    payload = _valid_shipment_payload()
    payload.pop["reference"] = "should-not-be-accepted"
    response = requests.post(f"{base_url}/api/v1/shipments", headers=headers, json=payload,)
    assert response.status_code in (201, 400, 422)

def test_post_shipment_reject_invalid_foreign_key(base_url, user_headers, preserve_data_files):
    preserve_data_files("shipment.json")
    headers = _get_headers(user_headers, method = "post")
    payload = _valid_shipment_payload()
    payload.pop["order_id"] = 99999999999
    response = requests.post(f"{base_url}/api/v1/shipments", headers=headers, json=payload,)
    assert response.status_code in (400, 404, 409, 422)

def test_post_shipment_is_immendiately_retrieveable(base_url, user_headers, preserve_data_files):
    preserve_data_files("shipment.json")
    headers = _get_headers(user_headers, method = "post")
    payload = _valid_shipment_payload()
    response = requests.post(f"{base_url}/api/v1/shipments", headers=headers, json=payload,)
    assert response.status_code == 201
    created_id = None

    if response.content:
        body = response.json()
        if isinstance(body, dict):
            created_id = body.get("id")
    if created_id is None:
        location = response.headers.get("Location")
        assert location, ("Created shipment must expose its id in the response body or Location header.")
        created_id = int(location.rstrip("/").split("/")[-1])

    get_response = _shipment_by_id(base_url, user_headers, created_id,)
    assert get_response.status_code == 200
    created = get_response.json()
    assert created["id"] == created_id
    assert created["reference"] == payload["reference"]
    assert created["order_id"] == payload["order_id"]

#endregion

#region GET shipment id

def test_get_shipment_by_id_returns_200(base_url, user_headers):
    existing = _first_shipment(base_url, user_headers)
    response = _shipment_by_id(base_url, user_headers, existing["id"])
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)
    assert body["id"] == existing["id"]

def test_get_shipment_by_id_matches_schema(base_url, user_headers):
    existing = _first_shipment(base_url, user_headers)
    response = _shipment_by_id(base_url, user_headers, existing["id"])
    assert response.status_code == 200
    Shipment.model_validate(response.json())

def test_get_shipment_by_id_nonexistent_returns_404(base_url, user_headers,):
    response = _shipment_by_id(base_url, user_headers, 999999999,)
    assert response.status_code == 404

def test_get_shipment_by_id_malformed_id_does_not_return_500(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/shipment/not-an-id", headers = headers)
    assert response.status_code != 500

def test_get_shipment_by_id_response_content_type_is_json(base_url, user_headers):
    existing = _first_shipment(base_url, user_headers)
    response = _shipment_by_id(base_url, user_headers, existing["id"])
    assert response.status_code == 200
    assert response.headers.get("Content-Type", "",).startswith("application/json")


def test_get_shipment_by_id_requires_authentication(base_url):
    response = requests.get(f"{base_url}/api/v1/shipments/1")
    assert response.status_code == 401

def test_get_shipment_by_id_insufficient_permissions_return_403(base_url, user_headers):
    headers =_get_headers(user_headers, method="get", allowed=False)
    response =requests.get(f"{base_url}/api/v1/shipments/1", headers=headers,)
    assert response.status_code ==403


def test_get_shipment_by_id_error_does_not_leak_internal_data(base_url, user_headers,):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/shipments/999999999", headers=headers,)
    assert response.status_code == 404
    _error_text_does_not_leak(response)

#endregion

#region PUT shipment id
def test_put_shipment_requires_authentication(base_url):
    response = requests.put(f"{base_url}/api/v1/shipments/1", json={},)
    assert response.status_code == 401


def test_put_shipment_insufficient_permissions_returns_403(base_url, user_headers):
    headers = _get_headers(user_headers, method="put", allowed=False,)
    response = requests.put(f"{base_url}/api/v1/shipments/1", headers=headers, json={},)
    assert response.status_code == 403

def test_put_shipment_valid_payload_returns_200(base_url, user_headers, preserve_data_files):
    preserve_data_files("shipment.json")
    existing = _first_shipment(base_url, user_headers)
    headers = _get_headers(user_headers, user_headers)
    payload = {
        "reference": existing["reference"],
        "order_id": existing["order_id"],
        "shipment_date": existing["shipment_date"],
        "shipment_type": existing["shipment_type"],
        "shipment_status": existing["shipment_status"],
        "carrier_name": existing["carrier_name"],
        "shipping_method": existing["shipping_method"],
        "payment_type": existing["payment_type"],
    }
    response = requests.post(f"{base_url}/api/v1/shipments", headers=headers, json=payload,)
    assert response.status_code == 200

def test_put_shipment_nonexistent_id_returns_404(base_url, user_headers):
    headers = _get_headers(user_headers, method="put",)
    response = requests.put(f"{base_url}/api/v1/shipments/999999999", headers=headers, json={},)
    assert response.status_code == 404

def test_put_shipment_invalid_id_does_not_return_500(base_url, user_headers):
    headers = _get_headers(user_headers, method="put",)
    response = requests.put(f"{base_url}/api/v1/shipments/not-an-id", headers=headers, json={},)
    assert response.status_code != 500

def test_put_shipment_rejects_invalid_field_value(base_url, user_headers, preserve_data_files,):
    preserve_data_files("shipment.json")
    existing = _first_shipment(base_url, user_headers,)
    headers = _get_headers(user_headers, method="put",)
    payload = {
        "reference": existing["reference"],
        "order_id": "not-an-int",
        "shipment_date": existing["shipment_date"],
        "shipment_type": existing["shipment_type"],
        "shipment_status": existing["shipment_status"],
        "carrier_name": existing["carrier_name"],
        "shipping_method": existing["shipping_method"],
        "payment_type": existing["payment_type"],
    }
    response = requests.put(f"{base_url}/api/v1/shipments/{existing['id']}", headers=headers, json=payload,)
    assert response.status_code in (400, 422)

def test_put_shipment_rejects_invalid_foreign_key(base_url, user_headers, preserve_data_files):
    preserve_data_files("shipment.json")
    existing = _first_shipment(base_url, user_headers,)
    headers = _get_headers(user_headers, method="put",)
    payload = {
        "reference": existing["reference"],
        "order_id": 9999999999,
        "shipment_date": existing["shipment_date"],
        "shipment_type": existing["shipment_type"],
        "shipment_status": existing["shipment_status"],
        "carrier_name": existing["carrier_name"],
        "shipping_method": existing["shipping_method"],
        "payment_type": existing["payment_type"],
    }
    response = requests.put(f"{base_url}/api/v1/shipments/{existing['id']}", headers=headers, json=payload,)
    assert response.status_code in (400, 404, 409, 422)

#endregion

#region DELETE shipment id


#endregion
