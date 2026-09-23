import json
import time
from datetime import datetime
from pathlib import Path

import pytest
import requests
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[2]
INVENTORIES_MODEL_SOURCE = (REPO_ROOT / "api" / "models" / "inventories.py").read_text(
    encoding="utf-8"
)

# region Shared helpers
class Inventory(BaseModel):
    item_id: int
    location_id: int
    quantity_on_hand: int
    quantity_expected: int
    quantity_ordered: int
    quantity_allocated: int
    created_at: datetime
    updated_at: datetime

# a helper method to get the user and check their method and if they are allowed with inventory
def _get_headers(user_headers, method="get", allowed=True):
    return user_headers(resource="inventories", method=method, allowed=allowed)

def _first_inventory(base_url, user_headers):
    headers = _get_headers(user_headers)
    body = requests.get(f"{base_url}/api/v1/inventories", headers=headers).json()
    assert body, "fixture data/inventory.json is expected to be non-empty"
    return body[0]

#endregion

#region GET Inventory
# GET / Inventory here are all the Inventory GET tests
def test_get_inventory_returns_200_with_valid_response(base_url, user_headers):
    # Gets header for user who is allowed to GET
    headers = user_headers(resource="inventories", method="get", allowed=True)
    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers)

    # Check the response of that endpoint is successfull
    assert response.status_code == 200
    body = response.json()

    # it should return a list
    assert isinstance(body, list)

    # there should be atleast 1 inventory in the test data
    assert len(body) > 0

    # the two fields to identify the inventory
    assert "item_id" in body[0]
    assert "location_id" in body[0]

def test_response_body_matches_documented_schema(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers)
    assert response.status_code == 200
    for r in response.json():
        Inventory.model_validate(r)

def test_response_time_is_reasonable(base_url, user_headers):
    headers = _get_headers(user_headers)
    start = time.monotonic()
    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers)
    elapsed = time.monotonic() - start
    assert response.status_code != 500
    assert (elapsed < 0.5), f"GET /inventories took {elapsed:.2f}s"

def test_get_inventory_requires_authentcation(base_url):
    response = requests.get(f"{base_url}/api/v1/inventories")
    assert response.status_code == 401

def test_get_inventor_insufficient_permissions_returns_403(base_url, user_headers):
    headers = _get_headers(user_headers, method="get", allowed=False)
    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers)
    assert response.status_code == 403

# to check if the get is a json file
def test_response_content_type_is_json(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers)
    assert response.headers.get("Content-Type", "").startswith("application/json")

# checks if the error doesnt leka any data
def test_get_inventory_error_does_not_leak_internal_data(base_url):
    response = requests.get(f"{base_url}/api/v1/inventories")
    text_lower = response.text.lower()

    for leak in ("traceback", "exception", "stack", "internal", "sql", "file"," line"):
        assert leak not in text_lower

# is to say these test i expect to fail since there is no documented for get inventories
@pytest.mark.xfail(
    strict=True,
    reason=(
        "Pagination is not currently documented for GET /inventories. "
        "The OpenAPI definition does not declare page, limit, page_size, "
        "cursor, or any other pagination parameters."
    ),
)

def test_get_inventories_supports_pagination(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers, params = {"page": 1, "limit": 2},)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) <= 2

@pytest.mark.xfail(
    strict=True,
    reason=(
        "Not currently documented for GET /inventories. The OpenAPI definition"
        "does not declare any query parameters for filtering inventory rows."
    ),
)

@pytest.mark.parametrize(
    "filter_type",
    ["item_id", "location_id"],
)

def test_get_inventories_supports_filtering(base_url, user_headers, filter_type):
    headers = _get_headers(user_headers)
    existing = _first_inventory(base_url, user_headers)

    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers, params={filter_type: existing[filter_type]},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.xfail(
    strict=True,
    reason=(
       "Not currently documented for GET /inventories. The OpenAPI definition"
        "does not declare a sorting parameter."
    ),
)

def test_get_inventories_supports_sorting(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers, params = {"sort": "item_id"},)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.xfail(strict=True, reason="The API currently returns a different status code for an empty inventory result; the documented/spec behavior is 404.",)

def test_get_inventories_empty_result_returns_404(base_url, user_headers):
    headers = user_headers(app="smartglass_reader")
    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers, params={"item_id": 999999999},)
    assert response.status_code == 404
    assert response.json() == []


def test_get_inventories_invalid_query_param_does_not_return_500(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers, params={"page": -1},)
    assert response.status_code != 500

def test_error_respone_have_constint_format(base_url):
    get_response = requests.get(f"{base_url}/api/v1/inventories")

    post_respone = requests.post(f"{base_url}/api/v1/inventories", json={},)

    assert get_response.status_code == 401
    assert post_respone.status_code == 401

    assert get_response.headers.get("Content-Type", "").startswith("application/json")
    assert post_respone.headers.get("Content-Type", "").startswith("application/json")

    get_error = get_response.json()
    post_error = post_respone.json()

    assert isinstance(get_error, dict)
    assert isinstance(post_error, dict)

    assert set(get_error.keys()) == set(post_error.keys())

#endregion

# region GET /inventories/{id}
def test_GET_inventory_by_id_is_not_supported(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/inventories/1",headers=headers)
    assert response.status_code == 404


# endregion


# region POST /inventories

@pytest.mark.xfail(
        strict = True,
        reason = ("POST inventories should return 201 but it doesn't return it right now")
)

def test_post_inventory_returns_201(base_url, user_headers, preserve_data_files):
    # this is to preserve the original data before anything gets added or removed or changed
    preserve_data_files("inventory.json")
    # check autherization for the user
    headers = _get_headers(user_headers, method="post")
    # creating the inventory data for testing
    payload = {"item_id" : 999991,
               "location_id": 999991,
               "quantity_on_hand": 100,
               "quantity_expected": 50,
               "quantity_ordered": 25,
               "quantity_allocated": 10
               }
    # calling the api with the user and data
    response = requests.post(f"{base_url}/api/v1/inventories", headers=headers, json=payload,)
    # checking if the status is correct 
    assert response.status_code == 201

    has_location = bool(response.headers.get("Location"))
    has_body = False
    if response.content:
        try:
            body = response.json()
            has_body = bool(body)
        except ValueError:
            has_body = False

    assert has_body or has_location,("201 Created response must expose the newly created resource through a response body or Location header.")

def test_post_inventory_is_immediately_retrievable(base_url, user_headers, preserve_data_files):
    # this part is to post something into the data
    preserve_data_files("inventory.json")
    post_headers = _get_headers(user_headers, method="post")
    payload = {"item_id" : 999992,
               "location_id": 999992,
               "quantity_on_hand": 100,
               "quantity_expected": 50,
               "quantity_ordered": 25,
               "quantity_allocated": 10
               }
    create_response = requests.post(f"{base_url}/api/v1/inventories", headers=post_headers, json=payload,)
    assert create_response.status_code == 201

    # this part is to retrieve that new made data 
    get_headers = _get_headers(user_headers)
    get_response = requests.get(f"{base_url}/api/v1/inventories", headers=get_headers)
    assert get_response.status_code == 200

    # get the json file
    inventories = get_response.json()

    # loop through it and find the right id of the new made item
    created = None
    for inventory in inventories:
            if (
                inventory["item_id"] == payload["item_id"]
                and inventory["location_id"] == payload["location_id"]
            ):
                created = inventory
                break

    # check if it matches the actual data that we use to make it
    assert created is not None
    assert created["quantity_on_hand"] == 100
    assert created["quantity_expected"] == 50
    assert created["quantity_ordered"] == 25
    assert created["quantity_allocated"] == 10

def test_post_inventory_existing_pair_is_upserted(base_url, user_headers, preserve_data_files):
    preserve_data_files("inventory.json")
    # get the first inventory
    existing = _first_inventory(base_url, user_headers)
    post_headers = _get_headers(user_headers, method="post")
    # make the exact same data in post
    payload = {"item_id" : existing["item_id"],
               "location_id": existing["location_id"],
               "quantity_on_hand": 100,
               "quantity_expected": 50,
               "quantity_ordered": 25,
               "quantity_allocated": 10
               }
    # post it into the api
    response = requests.post(f"{base_url}/api/v1/inventories", headers=post_headers, json=payload,)

    # check if its actually done
    assert response.status_code== 201

    # get everything again
    get_headers = _get_headers(user_headers)
    get_response = requests.get(f"{base_url}/api/v1/inventories", headers=get_headers)
    assert get_response.status_code == 200

    # get the json
    inventories = get_response.json()

    # now to find the matching item and where the location is
    matching = [
            inventory
            for inventory in inventories
            if inventory["item_id"] == existing["item_id"]
            and inventory["location_id"] == existing["location_id"]
            ]

    # to check everything if it matches or not
    assert len(matching) == 1

    assert matching[0]["quantity_on_hand"] == 100
    assert matching[0]["quantity_expected"] == 50
    assert matching[0]["quantity_ordered"] == 25
    assert matching[0]["quantity_allocated"] == 10

@pytest.mark.xfail(
        strict = True,
        reason = ("POST inventories should reject references to missing fields but it doesn't reject it right now")
)
@pytest.mark.parametrize(
    "field,payload",
    [
        (
            "item_id",
            {
                "item_id": "not-an-int",
                "location_id": 999996,
                "quantity_on_hand": 100,
                "quantity_expected": 50,
                "quantity_ordered": 25,
                "quantity_allocated": 10,
            },
        ),
        (
            "location_id",
            {
                "item_id": 999996,
                "location_id": "not-an-int",
                "quantity_on_hand": 100,
                "quantity_expected": 50,
                "quantity_ordered": 25,
                "quantity_allocated": 10,
            },
        ),
        (
            "quantity_on_hand",
            {
                "item_id": 999996,
                "location_id": 999996,
                "quantity_on_hand": "not-an-int",
                "quantity_expected": 50,
                "quantity_ordered": 25,
                "quantity_allocated": 10,
            },
        ),
    ],
)

def test_post_inventory_missing_requiring_fields_is_handled(base_url, user_headers, preserve_data_files, field, payload):
    preserve_data_files("inventory.json")

    headers = _get_headers(user_headers, method="post")
    response = requests.post(f"{base_url}/api/v1/inventories", headers=headers, json=payload,)
    # it should return a bad request and unprocessable entity
    assert response.status_code in (400, 422), (f"Invalid type for {field!r} should be rejected,"f"but API returned {response.status_code}")

@pytest.mark.xfail(
        strict = True,
        reason = ("POST inventories should reject references invalid values but right now it accepts it")
)

@pytest.mark.parametrize(
    "payload",
    [
        {
            "item_id": -1,
            "location_id": 999997,
            "quantity_on_hand": 100,
            "quantity_expected": 50,
            "quantity_ordered": 25,
            "quantity_allocated": 10,
        },
        {
            "item_id": 999997,
            "location_id": -1,
            "quantity_on_hand": 100,
            "quantity_expected": 50,
            "quantity_ordered": 25,
            "quantity_allocated": 10,
        },
        {
            "item_id": 999997,
            "location_id": 999997,
            "quantity_on_hand": -1,
            "quantity_expected": 50,
            "quantity_ordered": 25,
            "quantity_allocated": 10,
        },
    ],
)

def test_post_inventory_missing_rejects_invalid_values(base_url, user_headers, preserve_data_files, payload):
    preserve_data_files("inventory.json")

    headers = _get_headers(user_headers, method="post")
    response = requests.post(f"{base_url}/api/v1/inventories", headers=headers, json=payload,)
    # it should return a bad request and unprocessable entity
    assert response.status_code in (400, 422)

@pytest.mark.xfail(
        strict = True,
        reason = ("POST inventories should reject unexpected fields, but current way may accept or just ignore them")
)

def test_post_inventory_rejects_unexpected_fields(base_url, user_headers, preserve_data_files):
    preserve_data_files("inventory.json")

    headers = _get_headers(user_headers, method="post")
    payload = {
        "item_id": 999998,
        "location_id": 999998,
        "quantity_on_hand": 100,
        "quantity_expected": 50,
        "quantity_ordered": 25,
        "quantity_allocated": 10,
        "unexpected_field": "should-not-be-accepted",
    }
    response = requests.post(f"{base_url}/api/v1/inventories", headers=headers, json=payload,)
    assert response.status_code in (400, 404, 422), ("Unexpected fields should be rejected, but API returned" f"{response.status_code}")

@pytest.mark.xfail(
        strict = True,
        reason = ("POST inventories should reject references to non-existent items or locations")
)

def test_post_inventory_rejects_invalid_foreign_key_references(base_url, user_headers, preserve_data_files):
    preserve_data_files("inventory.json")

    headers = _get_headers(user_headers, method="post")
    payload = {
        "item_id": 9999999999999,
        "location_id": 9999999999999,
        "quantity_on_hand": 100,
        "quantity_expected": 50,
        "quantity_ordered": 25,
        "quantity_allocated": 10,
    }
    response = requests.post(f"{base_url}/api/v1/inventories", headers=headers, json=payload,)
    assert response.status_code in (400, 404, 422)

def test_post_inventory_requires_json_content_type(base_url, user_headers, preserve_data_files):
    preserve_data_files("inventory.json")

    headers = _get_headers(user_headers, method="post")
    headers["Content-Type"] = "text/plain"
    payload = {
        "item_id": 999999,
        "location_id": 999999,
        "quantity_on_hand": 100,
        "quantity_expected": 50,
        "quantity_ordered": 25,
        "quantity_allocated": 10,
    }

    response = requests.post(f"{base_url}/api/v1/inventories", headers=headers,data=payload,)

    assert response.status_code in (400, 415, 422)

def test_post_inventory_accepts_application_json_content_type(base_url, user_headers, preserve_data_files):
    preserve_data_files("inventory.json")

    headers = _get_headers(user_headers, method="post")
    headers["Content-Type"] = "application/json"

    payload = {
        "item_id": 999999,
        "location_id": 999999,
        "quantity_on_hand": 100,
        "quantity_expected": 50,
        "quantity_ordered": 25,
        "quantity_allocated": 10,
    }

    response = requests.post(
        f"{base_url}/api/v1/inventories",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 201

def test_post_inventory_requires_authentication(base_url):
    # a request without a header
    response = requests.post(f"{base_url}/api/v1/inventories",
        json={
            "item_id": 999993,
            "location_id": 999993,
            },)
    # should return that the user isnt authenticated 
    assert response.status_code == 401

def test_post_inventory_insufficient_permissions_returns_403(base_url, user_headers):
    headers = _get_headers(user_headers, method = "post", allowed = False)

    response = requests.post(f"{base_url}/api/v1/inventories",
        headers=headers,
        json={
            "item_id": 999994,
            "location_id": 999994,
        },
    )
    # should return that the user doesnt have post permission
    assert response.status_code == 403

# endregion


# region PUT /inventories/{id}
def test_PUT_inventory_by_id_is_not_supported(base_url, user_headers):
    headers = _get_headers(user_headers, method= "put")
    response = requests.put(f"{base_url}/api/v1/inventories/1",headers=headers, json={"item_id": 459})
    assert response.status_code == 404
# endregion


# region DELETE /inventories/{id}
def test_delete_inventory_insufficient_permissions_returns_403(base_url, user_headers):
    headers = _get_headers(user_headers, method="delete", allowed=False,)
    response = requests.delete(f"{base_url}/api/v1/inventories/1", headers=headers,)
    assert response.status_code == 403


def test_DELETE_inventory_by_id_is_not_supported(base_url, user_headers):
    headers = _get_headers(user_headers, method="delete")
    response = requests.delete(f"{base_url}/api/v1/inventories/1", headers=headers,)
    assert response.status_code == 404

# endregion



    


