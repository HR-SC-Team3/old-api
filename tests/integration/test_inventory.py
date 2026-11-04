import json
import time

import pytest
import requests

from schemas import Inventory

# region Shared helpers

# a helper method to get the user and check their method and if they are allowed with inventory
def _get_headers(user_headers, method="get", allowed=True):
    return user_headers(resource="inventories", method=method, allowed=allowed)

def _first_inventory(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers)
    if response.status_code >= 500:
        pytest.fail(f"Unexpected server error: {response.status_code}")
    body = response.json()
    assert body, "fixture data/inventory.json is expected to be non-empty"
    return body[0]

def _unused_inventory_pair(base_url, user_headers):
    inventory_response = requests.get(f"{base_url}/api/v1/inventories", headers=_get_headers(user_headers),)
    item_response = requests.get(f"{base_url}/api/v1/items", headers=user_headers(resource="items", method="get"),)
    location_response = requests.get(f"{base_url}/api/v1/locations", headers=user_headers(resource="locations", method="get"),)
    assert inventory_response.status_code == 200
    assert item_response.status_code == 200
    assert location_response.status_code == 200

    occupied_pairs = {(inventory["item_id"], inventory["location_id"]) for inventory in inventory_response.json()}
    for item in item_response.json():
        for location in location_response.json():
            pair = (item["id"], location["id"])
            if pair not in occupied_pairs:
                return pair

    pytest.fail("No unused item/location pair is available for an inventory test")

#endregion

#region GET Inventory
# GET / Inventory here are all the Inventory GET tests
def test_get_inventory_returns_200_with_valid_response(base_url, user_headers):
    # Gets header for user who is allowed to GET
    headers = user_headers(resource="inventories", method="get", allowed=True)
    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers)

    # Check the response of that endpoint is successful
    assert response.status_code == 200
    body = response.json()

    # it should return a list
    assert isinstance(body, list)

    # there should be at least 1 inventory in the test data
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

def test_get_inventory_requires_authentication(base_url):
    response = requests.get(f"{base_url}/api/v1/inventories")
    assert response.status_code == 401

def test_get_inventory_insufficient_permissions_returns_403(base_url, user_headers):
    headers = _get_headers(user_headers, method="get", allowed=False)
    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers)
    assert response.status_code == 403

# to check if the get is a json file
def test_response_content_type_is_json(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers)
    assert response.headers.get("Content-Type", "").startswith("application/json")

# checks if the error doesnt leak any data
def test_get_inventory_error_does_not_leak_internal_data(base_url):
    response = requests.get(f"{base_url}/api/v1/inventories")
    text_lower = response.text.lower()

    for leak in ("traceback", "exception", "stack", "internal", "sql", "file"," line"):
        assert leak not in text_lower

# is to say these test i expect to fail since there is no documented for get inventories
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Pagination is not currently documented for GET /inventories. "
        "The OpenAPI definition does not declare page, limit, page_size, "
        "cursor, or any other pagination parameters."
    ),
)
def test_get_inventories_supports_pagination(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers, params = {"page": 1, "limit": 2},)
    if response.status_code >= 500:
        pytest.fail(f"Unexpected server error: {response.status_code}")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) <= 2

@pytest.mark.xfail(
    strict=True,
    raises=AssertionError, 
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

    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers, params={filter_type: existing[filter_type]},)
    if response.status_code >= 500:
        pytest.fail(f"Unexpected server error: {response.status_code}")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert all(row[filter_type] == existing[filter_type] for row in body)

@pytest.mark.xfail(strict=True, raises=AssertionError, reason=("Not currently documented for GET /inventories. The OpenAPI definition does not declare a sorting parameter."),)

def test_get_inventories_supports_sorting(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers, params={"sort": "item_id", "order": "desc"},)
    if response.status_code >= 500:
        pytest.fail(f"Unexpected server error: {response.status_code}")
    assert response.status_code == 200
    ids = [row["item_id"] for row in response.json()]
    assert ids == sorted(ids, reverse=True)

@pytest.mark.xfail(strict=True, raises=AssertionError, reason="The API currently returns a different status code for an empty inventory result; the documented/spec behavior is 404.",)

def test_get_inventories_empty_result_returns_404(base_url, user_headers):
    headers = user_headers(app="smartglass_reader")
    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers, params={"item_id": 999999999},)
    if response.status_code >= 500:
        pytest.fail(f"Unexpected server error: {response.status_code}")
    assert response.status_code == 404
    assert response.json() == []


@pytest.mark.parametrize("params", [{"page": 1, "limit": 2}, {"sort": "item_id"}, {"item_id": 1}, {"unknown_parameter": "test"}, {"page": -1}],)
def test_get_inventories_query_params_are_ignored(base_url, user_headers, params):
    headers = _get_headers(user_headers)
    baseline = requests.get(f"{base_url}/api/v1/inventories", headers=headers)
    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers, params=params)
    assert response.status_code == 200
    assert response.json() == baseline.json()


def test_get_inventories_invalid_query_param_does_not_return_500(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/inventories", headers=headers, params={"page": -1},)
    assert response.status_code != 500

def test_error_response_has_consistent_format(base_url):
    get_response = requests.get(f"{base_url}/api/v1/inventories")

    post_response = requests.post(f"{base_url}/api/v1/inventories", json={},)

    assert get_response.status_code == 401
    assert post_response.status_code == 401

    assert get_response.headers.get("Content-Type") is None
    assert post_response.headers.get("Content-Type") is None

@pytest.mark.parametrize("suffix", ["1/totals", "1/1"])
def test_get_inventory_subroute_returns_404(base_url, user_headers, suffix):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/inventories/{suffix}", headers=headers,)
    assert response.status_code == 404

#endregion

# region GET /inventories/{id}
def test_GET_inventory_by_id_is_not_supported(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/inventories/1",headers=headers)
    assert response.status_code == 404


# endregion


# region POST /inventories

def test_post_inventory_returns_201(base_url, user_headers, preserve_data_files):
    # this is to preserve the original data before anything gets added or removed or changed
    preserve_data_files("inventory.json")
    # check authorization for the user
    headers = _get_headers(user_headers, method="post")
    item_id, location_id = _unused_inventory_pair(base_url, user_headers)
    payload = {
        "item_id": item_id,
        "location_id": location_id,
        "quantity_on_hand": 100,
        "quantity_expected": 50,
        "quantity_ordered": 25,
        "quantity_allocated": 10,
    }
    # calling the api with the user and data
    response = requests.post(f"{base_url}/api/v1/inventories", headers=headers, json=payload,)
    if response.status_code >= 500:
        pytest.fail(f"Unexpected server error: {response.status_code}")
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
    item_id, location_id = _unused_inventory_pair(base_url, user_headers)
    payload = {
        "item_id": item_id,
        "location_id": location_id,
        "quantity_on_hand": 100,
        "quantity_expected": 50,
        "quantity_ordered": 25,
        "quantity_allocated": 10,
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


def test_post_inventory_rejects_invalid_field_types(base_url, user_headers, preserve_data_files, field, payload):
    preserve_data_files("inventory.json")

    headers = _get_headers(user_headers, method="post")
    response = requests.post(f"{base_url}/api/v1/inventories", headers=headers, json=payload,)
    if response.status_code >= 500:
        pytest.fail(f"Unexpected server error: {response.status_code}")
    # it should return a bad request and unprocessable entity
    assert response.status_code in (400, 422), (f"Invalid type for {field!r} should be rejected,"f"but API returned {response.status_code}")

@pytest.mark.parametrize(
    "missing_field",
    [
        "item_id",
        "location_id",
        "quantity_on_hand",
        "quantity_expected",
        "quantity_ordered",
        "quantity_allocated",
    ],
)
def test_post_inventory_missing_rejects_invalid_values(base_url, user_headers, preserve_data_files, missing_field):
    preserve_data_files("inventory.json")
    headers = _get_headers(user_headers, method="post")
    existing = _first_inventory(base_url, user_headers)
    payload = {
        "item_id": existing["item_id"],
        "location_id": existing["location_id"],
        "quantity_on_hand": 100,
        "quantity_expected": 50,
        "quantity_ordered": 25,
        "quantity_allocated": 10,
    }
    payload.pop(missing_field)

    response = requests.post(f"{base_url}/api/v1/inventories", headers=headers, json=payload)
    assert response.status_code in (400, 422)



@pytest.mark.parametrize(
    "field",
    [
        "quantity_on_hand",
        "quantity_expected",
        "quantity_ordered",
        "quantity_allocated",
    ],
)
def test_post_inventory_rejects_negative_values(base_url, user_headers, preserve_data_files, field):
    preserve_data_files("inventory.json")
    existing = _first_inventory(base_url, user_headers)
    payload = {
        "item_id": existing["item_id"],
        "location_id": existing["location_id"],
        "quantity_on_hand": 100,
        "quantity_expected": 50,
        "quantity_ordered": 25,
        "quantity_allocated": 10,
    }
    payload[field] = -1
    headers = _get_headers(user_headers, method="post")
    response = requests.post(f"{base_url}/api/v1/inventories", headers=headers, json=payload,)
    assert response.status_code in (400, 422)



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
    if response.status_code >= 500:
        pytest.fail(f"Unexpected server error: {response.status_code}")    
    assert response.status_code in (400, 404, 422), ("Unexpected fields should be rejected, but API returned" f"{response.status_code}")


def test_post_inventory_rejects_invalid_foreign_key_references(base_url, user_headers, preserve_data_files):
    preserve_data_files("inventory.json")

    headers = _get_headers(user_headers, method="post")
    payload = {
        "item_id": 9999999999,
        "location_id": 9999999999,
        "quantity_on_hand": 100,
        "quantity_expected": 50,
        "quantity_ordered": 25,
        "quantity_allocated": 10,
    }
    response = requests.post(f"{base_url}/api/v1/inventories", headers=headers, json=payload,)
    if response.status_code >= 500:
        pytest.fail(f"Unexpected server error: {response.status_code}")
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

    response = requests.post(f"{base_url}/api/v1/inventories", headers=headers,data=json.dumps(payload),)

    assert response.status_code == 415

def test_post_inventory_accepts_application_json_content_type(base_url, user_headers, preserve_data_files):
    preserve_data_files("inventory.json")

    headers = _get_headers(user_headers, method="post")
    headers["Content-Type"] = "application/json"

    existing = _first_inventory(base_url, user_headers)
    payload = {
        "item_id": existing["item_id"],
        "location_id": existing["location_id"],
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
def test_put_inventory_by_id_is_not_supported(base_url, user_headers):
    headers = _get_headers(user_headers, method="put")
    inventory = _first_inventory(base_url, user_headers)
    response = requests.put(f"{base_url}/api/v1/inventories/1", headers=headers, json=inventory,)
    assert response.status_code == 404

def test_put_inventory_incomplete_payload_returns_422(base_url, user_headers):
    headers = _get_headers(user_headers, method="put")
    response = requests.put(f"{base_url}/api/v1/inventories/1", headers=headers, json={"item_id": 459},)
    assert response.status_code == 422

def test_PUT_inventory_requires_authentication(base_url):
    response = requests.put(f"{base_url}/api/v1/inventories/1", json={"item_id": 459})
    assert response.status_code == 401

def test_PUT_inventory_insufficient_permission(base_url, user_headers):
    headers = _get_headers(user_headers, method="put", allowed=False)
    response = requests.put(f"{base_url}/api/v1/inventories/1", headers=headers, json={"item_id": 459})
    assert response.status_code == 403

def test_put_inventory_composite_key_returns_404(base_url, user_headers):
    headers = _get_headers(user_headers, method="put")
    response = requests.put(f"{base_url}/api/v1/inventories/1/1", headers=headers, json={"item_id": 1, "location_id": 1},)
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

def test_DELETE_inventory_by_id_requires_authentication(base_url):
    response = requests.delete(f"{base_url}/api/v1/inventories/1")
    assert response.status_code == 401

def test_delete_inventory_composite_key_returns_404(base_url, user_headers):
    headers = _get_headers(user_headers, method="delete")
    response = requests.delete(f"{base_url}/api/v1/inventories/1/1", headers=headers,)
    assert response.status_code == 404
# endregion
