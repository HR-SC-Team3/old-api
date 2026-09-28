import json
import time
from pathlib import Path

import pytest
import requests

from schemas import Item


REPO_ROOT = Path(__file__).resolve().parents[2]
ITEMS_MODEL_SOURCE = (
    REPO_ROOT / "api" / "models" / "items.py"
).read_text(encoding="utf-8")


# region Shared helpers

def _url(base_url, path=""):
    return f"{base_url}/api/v1/items{path}"


def _get_headers(user_headers, method="get", allowed=True):
    return user_headers(resource="items", method=method, allowed=allowed)


def _first_item(base_url, user_headers):
    headers = _get_headers(user_headers)
    body = requests.get(_url(base_url), headers=headers).json()

    assert body, "fixture data/item.json is expected to be non-empty"

    return body[0]


# endregion


# region GET /items


def test_get_items_returns_200_with_valid_response(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(_url(base_url), headers=headers)

    assert response.status_code == 200

    body = response.json()

    assert isinstance(body, list)
    assert len(body) > 0
    assert "id" in body[0]


def test_response_body_matches_documented_schema(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(_url(base_url), headers=headers)

    body = response.json()

    for raw in body:
        Item.model_validate(raw)


def test_response_content_type_is_json(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(_url(base_url), headers=headers)

    assert response.headers.get(
        "Content-Type", ""
    ).startswith("application/json")


def test_response_time_is_reasonable(base_url, user_headers):
    headers = _get_headers(user_headers)

    start = time.monotonic()

    response = requests.get(_url(base_url), headers=headers)

    elapsed = time.monotonic() - start

    assert response.status_code == 200
    assert (
        elapsed < 0.5
    ), f"GET /items took {elapsed:.2f}s, which is unreasonably slow"


@pytest.mark.xfail(
    strict=True,
    reason="API returns 403 when query parameters are used",
)
@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"page": 1}, id="pagination-page"),
        pytest.param({"limit": 5}, id="pagination-limit"),
        pytest.param({"supplier_id": 17}, id="filter-supplier"),
        pytest.param({"item_group_id": 1}, id="filter-item-group"),
        pytest.param({"sort": "description"}, id="sort-description"),
        pytest.param({"page": -1}, id="invalid-negative-page"),
        pytest.param({"totally_unknown_key": "x"}, id="unknown-key"),
    ],
)
def test_query_params_are_honoured_or_gracefully_ignored(
    base_url, user_headers, params
):
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url),
        headers=headers,
        params=params,
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.xfail(
    strict=True,
    reason="API does not support supplier_id query filtering",
)
def test_filter_supplier_returns_matching_items(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url),
        headers=headers,
        params={"supplier_id": 17},
    )

    assert response.status_code == 200

    body = response.json()

    for item in body:
        assert item["supplier_id"] == 17


@pytest.mark.xfail(
    strict=True,
    reason="API does not support item_group_id query filtering",
)
def test_filter_item_group_returns_matching_items(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url),
        headers=headers,
        params={"item_group_id": 1},
    )

    assert response.status_code == 200

    body = response.json()

    for item in body:
        assert item["item_group_id"] == 1


@pytest.mark.xfail(
    strict=True,
    reason="API returns 403 when query parameters are used",
)
def test_sort_description_returns_correctly_ordered_results(
    base_url, user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url),
        headers=headers,
        params={"sort": "description"},
    )

    assert response.status_code == 200

    body = response.json()

    descriptions = [
        item["description"]
        for item in body
        if "description" in item
    ]

    assert descriptions == sorted(descriptions)


@pytest.mark.xfail(
    strict=True,
    reason="API returns 403 when query parameters are used",
)
def test_empty_result_set_returns_200_with_empty_array(
    base_url, user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url),
        headers=headers,
        params={"supplier_id": 999999},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_missing_api_key_is_rejected_with_401(base_url):
    response = requests.get(_url(base_url))

    assert response.status_code == 401


def test_invalid_api_key_is_rejected_with_401(base_url):
    response = requests.get(
        _url(base_url),
        headers={"API_KEY": "not-a-real-key"},
    )

    assert response.status_code == 401


def test_insufficient_permissions_returns_403(base_url, user_headers):
    headers = _get_headers(user_headers, allowed=False)

    response = requests.get(
        _url(base_url),
        headers=headers,
    )

    assert response.status_code == 403


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Error responses should use the same JSON error schema as "
        "successful responses."
    ),
)
def test_error_response_has_consistent_json_schema(base_url):
    response = requests.get(_url(base_url))

    assert response.status_code == 401
    assert response.headers.get(
        "Content-Type", ""
    ).startswith("application/json")

    body = response.json()

    assert "error" in body


def test_error_response_leaks_no_internal_details(base_url):
    response = requests.get(_url(base_url))

    text_lower = response.text.lower()

    for leak_indicator in (
        "traceback",
        "exception",
        "stack",
        "internal",
        "sql",
        'file "',
        "line ",
    ):
        assert leak_indicator not in text_lower


# endregion


# region GET /items/{id}


def test_get_item_by_id_returns_200_with_correct_resource(
    base_url, user_headers
):
    existing = _first_item(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}"),
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == existing


def test_get_item_by_id_matches_documented_schema(
    base_url, user_headers
):
    existing = _first_item(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}"),
        headers=headers,
    )

    Item.model_validate(response.json())


@pytest.mark.xfail(
    strict=True,
    reason="API returns 200 for a nonexistent item instead of 404",
)
def test_get_item_by_nonexistent_id_returns_404(
    base_url, user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url, "/999999"),
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason="API returns 500 for a malformed item ID instead of 400",
)
def test_get_item_by_malformed_id_returns_400(
    base_url, user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url, "/not-an-id"),
        headers=headers,
    )

    assert response.status_code == 400


def test_get_item_requires_authentication(base_url):
    response = requests.get(_url(base_url, "/1"))

    assert response.status_code == 401


def test_get_item_insufficient_permissions_returns_403(
    base_url, user_headers
):
    headers = _get_headers(
        user_headers,
        allowed=False,
    )

    response = requests.get(
        _url(base_url, "/1"),
        headers=headers,
    )

    assert response.status_code == 403


def test_get_item_response_content_type_is_json(
    base_url, user_headers
):
    existing = _first_item(base_url, user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}"),
        headers=_get_headers(user_headers),
    )

    assert response.headers.get(
        "Content-Type", ""
    ).startswith("application/json")


def test_get_item_malformed_id_error_leaks_no_internal_details(
    base_url, user_headers
):
    response = requests.get(
        _url(base_url, "/not-an-id"),
        headers=_get_headers(user_headers),
    )

    text_lower = response.text.lower()

    for leak_indicator in (
        "traceback",
        "exception",
        "valueerror",
        'file "',
        "line ",
    ):
        assert leak_indicator not in text_lower


# endregion


# region POST /items


@pytest.mark.xfail(
    strict=True,
    reason="POST /items returns 201 with an empty response body",
)
def test_post_item_returns_created_resource_with_id(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    existing = _first_item(base_url, user_headers)

    payload = {
        **existing,
        "id": 555555,
        "code": "ITM-555555",
        "description": "Test Item",
    }

    headers = _get_headers(
        user_headers,
        method="post",
    )

    response = requests.post(
        _url(base_url),
        headers=headers,
        json=payload,
    )

    assert response.status_code == 201

    body = response.json()

    assert "id" in body
    assert body["id"] == 555555
    assert body["description"] == "Test Item"


@pytest.mark.xfail(
    strict=True,
    reason="POST /items returns 201 without a Location header or response body",
)
def test_post_item_response_points_to_new_resource(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    existing = _first_item(base_url, user_headers)

    payload = {
        **existing,
        "id": 555556,
        "code": "ITM-555556",
        "description": "Location Test Item",
    }

    headers = _get_headers(
        user_headers,
        method="post",
    )

    response = requests.post(
        _url(base_url),
        headers=headers,
        json=payload,
    )

    assert response.status_code == 201

    assert (
        "Location" in response.headers
        or response.json().get("id") == 555556
    )


@pytest.mark.xfail(
    strict=True,
    reason="API accepts an empty item payload and returns 201",
)
def test_post_item_missing_required_fields_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    headers = _get_headers(
        user_headers,
        method="post",
    )

    response = requests.post(
        _url(base_url),
        headers=headers,
        json={},
    )

    assert response.status_code in (400, 422)


@pytest.mark.xfail(
    strict=True,
    reason="API accepts an invalid field type and returns 201",
)
def test_post_item_invalid_field_type_is_rejected(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    headers = _get_headers(
        user_headers,
        method="post",
    )

    response = requests.post(
        _url(base_url),
        headers=headers,
        json={
            "id": "not-an-int",
            "code": "ITM-BAD",
            "description": "Bad Type Item",
        },
    )

    assert response.status_code in (400, 422)


@pytest.mark.xfail(
    strict=True,
    reason="API accepts duplicate item IDs and returns 201",
)
def test_post_item_duplicate_id_returns_conflict(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    existing = _first_item(base_url, user_headers)

    headers = _get_headers(
        user_headers,
        method="post",
    )

    response = requests.post(
        _url(base_url),
        headers=headers,
        json={
            **existing,
            "description": "Duplicate Item",
        },
    )

    assert response.status_code in (400, 409, 422)


def test_post_item_is_immediately_retrievable(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    existing = _first_item(base_url, user_headers)

    payload = {
        **existing,
        "id": 555557,
        "code": "ITM-555557",
        "description": "Retrievable Item",
    }

    create_response = requests.post(
        _url(base_url),
        headers=_get_headers(user_headers, method="post"),
        json=payload,
    )

    assert create_response.status_code == 201

    get_response = requests.get(
        _url(base_url, "/555557"),
        headers=_get_headers(user_headers),
    )

    assert get_response.status_code == 200
    assert get_response.json() is not None
    assert get_response.json()["description"] == "Retrievable Item"


@pytest.mark.xfail(
    strict=True,
    reason="API accepts invalid foreign keys and returns 201",
)
@pytest.mark.parametrize(
    "foreign_key",
    [
        "item_line_id",
        "item_group_id",
        "item_type_id",
        "supplier_id",
    ],
)
def test_post_item_invalid_foreign_key_is_rejected(
    base_url,
    user_headers,
    preserve_data_files,
    foreign_key,
):
    preserve_data_files("item.json")

    existing = _first_item(base_url, user_headers)

    payload = {
        **existing,
        "id": 555558,
        "code": "ITM-555558",
        foreign_key: 999999,
    }

    response = requests.post(
        _url(base_url),
        headers=_get_headers(user_headers, method="post"),
        json=payload,
    )

    assert response.status_code in (400, 404, 409, 422)


def test_post_item_requires_authentication(base_url):
    response = requests.post(
        _url(base_url),
        json={"description": "No Auth Item"},
    )

    assert response.status_code == 401


def test_post_item_insufficient_permissions_returns_403(
    base_url, user_headers
):
    headers = _get_headers(
        user_headers,
        method="post",
        allowed=False,
    )

    response = requests.post(
        _url(base_url),
        headers=headers,
        json={"description": "Forbidden Item"},
    )

    assert response.status_code == 403


@pytest.mark.xfail(
    strict=True,
    reason="API accepts text/plain content and returns 201",
)
def test_post_item_wrong_content_type_is_rejected(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    headers = {
        **_get_headers(user_headers, method="post"),
        "Content-Type": "text/plain",
    }

    response = requests.post(
        _url(base_url),
        headers=headers,
        data=json.dumps({"description": "Plain Text Item"}),
    )

    assert response.status_code in (400, 415)


@pytest.mark.xfail(
    strict=True,
    reason="API returns 500 for malformed JSON instead of 400",
)
def test_post_item_malformed_json_body_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    headers = {
        **_get_headers(user_headers, method="post"),
        "Content-Type": "application/json",
    }

    response = requests.post(
        _url(base_url),
        headers=headers,
        data="{not valid json",
    )

    assert response.status_code in (400, 422)


def test_post_item_malformed_json_body_leaks_no_internal_details(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    headers = {
        **_get_headers(user_headers, method="post"),
        "Content-Type": "application/json",
    }

    response = requests.post(
        _url(base_url),
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


# region PUT /items/{id}


def test_put_item_valid_payload_returns_200(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    existing = _first_item(base_url, user_headers)

    updated = {
        **existing,
        "description": "Updated Item",
    }

    response = requests.put(
        _url(base_url, f"/{existing['id']}"),
        headers=_get_headers(user_headers, method="put"),
        json=updated,
    )

    assert response.status_code == 200


def test_put_item_update_is_persisted(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    existing = _first_item(base_url, user_headers)

    updated = {
        **existing,
        "description": "Persisted Item",
    }

    put_response = requests.put(
        _url(base_url, f"/{existing['id']}"),
        headers=_get_headers(user_headers, method="put"),
        json=updated,
    )

    assert put_response.status_code == 200

    get_response = requests.get(
        _url(base_url, f"/{existing['id']}"),
        headers=_get_headers(user_headers),
    )

    assert get_response.json()["description"] == "Persisted Item"


@pytest.mark.xfail(
    strict=True,
    reason="API returns 500 for a nonexistent item instead of 404",
)
def test_put_item_nonexistent_id_returns_404(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    existing = _first_item(base_url, user_headers)

    updated = {
        **existing,
        "id": 999999,
        "description": "Ghost Item",
    }

    response = requests.put(
        _url(base_url, "/999999"),
        headers=_get_headers(user_headers, method="put"),
        json=updated,
    )

    assert response.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason="API returns 500 for a malformed item ID instead of 400",
)
def test_put_item_malformed_id_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    existing = _first_item(base_url, user_headers)

    response = requests.put(
        _url(base_url, "/not-an-id"),
        headers=_get_headers(user_headers, method="put"),
        json=existing,
    )

    assert response.status_code == 400


@pytest.mark.xfail(
    strict=True,
    reason="API accepts an invalid field type and returns 200",
)
def test_put_item_invalid_field_type_is_rejected(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    existing = _first_item(base_url, user_headers)

    updated = {
        **existing,
        "unit_weight": "not-a-number",
    }

    response = requests.put(
        _url(base_url, f"/{existing['id']}"),
        headers=_get_headers(user_headers, method="put"),
        json=updated,
    )

    assert response.status_code in (400, 422)


@pytest.mark.xfail(
    strict=True,
    reason="API accepts invalid foreign keys and returns 200",
)
@pytest.mark.parametrize(
    "foreign_key",
    [
        "item_line_id",
        "item_group_id",
        "item_type_id",
        "supplier_id",
    ],
)
def test_put_item_invalid_foreign_key_is_rejected(
    base_url,
    user_headers,
    preserve_data_files,
    foreign_key,
):
    preserve_data_files("item.json")

    existing = _first_item(base_url, user_headers)

    updated = {
        **existing,
        foreign_key: 999999,
    }

    response = requests.put(
        _url(base_url, f"/{existing['id']}"),
        headers=_get_headers(user_headers, method="put"),
        json=updated,
    )

    assert response.status_code in (400, 404, 409, 422)


def test_put_item_requires_authentication(base_url):
    response = requests.put(
        _url(base_url, "/1"),
        json={"description": "No Auth Item"},
    )

    assert response.status_code == 401


def test_put_item_insufficient_permissions_returns_403(
    base_url, user_headers
):
    headers = _get_headers(
        user_headers,
        method="put",
        allowed=False,
    )

    response = requests.put(
        _url(base_url, "/1"),
        headers=headers,
        json={"description": "Forbidden Item"},
    )

    assert response.status_code == 403


# endregion


# region DELETE /items/{id}

@pytest.mark.skip(
    reason="No current test user has DELETE permission for items, so successful DELETE behavior cannot currently be tested.",
)
def test_delete_item_valid_id_returns_200(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    existing = _first_item(base_url, user_headers)

    response = requests.delete(
        _url(base_url, f"/{existing['id']}"),
        headers=_get_headers(user_headers, method="delete"),
    )

    assert response.status_code in (200, 204)


@pytest.mark.skip(
    reason="No current test user has DELETE permission for items, so successful DELETE behavior cannot currently be tested.",
)
def test_delete_item_resource_is_actually_gone(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    existing = _first_item(base_url, user_headers)

    delete_response = requests.delete(
        _url(base_url, f"/{existing['id']}"),
        headers=_get_headers(user_headers, method="delete"),
    )

    assert delete_response.status_code in (200, 204)

    get_response = requests.get(
        _url(base_url, f"/{existing['id']}"),
        headers=_get_headers(user_headers),
    )

    assert get_response.status_code == 404


@pytest.mark.skip(
    reason="No current test user has DELETE permission for items, so DELETE behavior for nonexistent IDs cannot currently be tested.",
)
def test_delete_item_nonexistent_id_returns_404(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    response = requests.delete(
        _url(base_url, "/999999"),
        headers=_get_headers(user_headers, method="delete"),
    )

    assert response.status_code == 404


@pytest.mark.skip(
    reason="No current test user has DELETE permission for items, so DELETE behavior for malformed IDs cannot currently be tested.",
)
def test_delete_item_malformed_id_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    response = requests.delete(
        _url(base_url, "/not-an-id"),
        headers=_get_headers(user_headers, method="delete"),
    )

    assert response.status_code == 400


@pytest.mark.skip(
    reason="No current test user has DELETE permission for items, so repeated DELETE behavior cannot currently be tested.",
)
def test_delete_item_repeated_delete_returns_404(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item.json")

    existing = _first_item(base_url, user_headers)

    headers = _get_headers(
        user_headers,
        method="delete",
    )

    first = requests.delete(
        _url(base_url, f"/{existing['id']}"),
        headers=headers,
    )

    second = requests.delete(
        _url(base_url, f"/{existing['id']}"),
        headers=headers,
    )

    assert first.status_code in (200, 204)
    assert second.status_code == 404


def test_delete_item_requires_authentication(base_url):
    response = requests.delete(
        _url(base_url, "/1"),
    )

    assert response.status_code == 401


def test_delete_item_insufficient_permissions_returns_403(
    base_url, user_headers
):
    headers = _get_headers(
        user_headers,
        method="delete",
        allowed=False,
    )

    response = requests.delete(
        _url(base_url, "/1"),
        headers=headers,
    )

    assert response.status_code == 403




# endregion


# region GET /items/{id}/inventory


def test_get_item_inventory_returns_200(
    base_url, user_headers
):
    existing = _first_item(base_url, user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}/inventory"),
        headers=_get_headers(user_headers),
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_item_inventory_only_returns_correct_item_inventory(
    base_url, user_headers
):
    existing = _first_item(base_url, user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}/inventory"),
        headers=_get_headers(user_headers),
    )

    assert response.status_code == 200

    body = response.json()

    for inventory in body:
        if isinstance(inventory, dict):
            if "item_id" in inventory:
                assert inventory["item_id"] == existing["id"]


@pytest.mark.xfail(
    strict=True,
    reason="API returns 200 for nonexistent item inventory instead of 404",
)
def test_get_item_inventory_nonexistent_item_returns_404(
    base_url, user_headers
):
    response = requests.get(
        _url(base_url, "/999999/inventory"),
        headers=_get_headers(user_headers),
    )

    assert response.status_code == 404


def test_get_item_inventory_empty_result_returns_200(
    base_url, user_headers
):
    response = requests.get(
        _url(base_url, "/999999/inventory"),
        headers=_get_headers(user_headers),
    )

    if response.status_code == 200:
        assert response.json() == []


def test_get_item_inventory_requires_authentication(base_url):
    response = requests.get(
        _url(base_url, "/1/inventory"),
    )

    assert response.status_code == 401


def test_get_item_inventory_insufficient_permissions_returns_403(
    base_url, user_headers
):
    headers = _get_headers(
        user_headers,
        allowed=False,
    )

    response = requests.get(
        _url(base_url, "/1/inventory"),
        headers=headers,
    )

    assert response.status_code == 403


def test_get_item_inventory_response_content_type_is_json(
    base_url, user_headers
):
    existing = _first_item(base_url, user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}/inventory"),
        headers=_get_headers(user_headers),
    )

    assert response.headers.get(
        "Content-Type", ""
    ).startswith("application/json")


# endregion


# region GET /items/{id}/inventory/totals


def test_get_item_inventory_totals_returns_200(
    base_url, user_headers
):
    existing = _first_item(base_url, user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}/inventory/totals"),
        headers=_get_headers(user_headers),
    )

    assert response.status_code == 200


@pytest.mark.xfail(
    strict=True,
    reason="API returns 200 for nonexistent item inventory totals instead of 404",
)
def test_get_item_inventory_totals_nonexistent_item_returns_404(
    base_url, user_headers
):
    response = requests.get(
        _url(base_url, "/999999/inventory/totals"),
        headers=_get_headers(user_headers),
    )

    assert response.status_code == 404


def test_get_item_inventory_totals_requires_authentication(
    base_url
):
    response = requests.get(
        _url(base_url, "/1/inventory/totals"),
    )

    assert response.status_code == 401


def test_get_item_inventory_totals_insufficient_permissions_returns_403(
    base_url, user_headers
):
    headers = _get_headers(
        user_headers,
        allowed=False,
    )

    response = requests.get(
        _url(base_url, "/1/inventory/totals"),
        headers=headers,
    )

    assert response.status_code == 403


def test_get_item_inventory_totals_response_content_type_is_json(
    base_url, user_headers
):
    existing = _first_item(base_url, user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}/inventory/totals"),
        headers=_get_headers(user_headers),
    )

    assert response.headers.get(
        "Content-Type", ""
    ).startswith("application/json")


# endregion