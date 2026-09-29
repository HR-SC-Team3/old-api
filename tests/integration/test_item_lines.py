import json
import time

import pytest
import requests

from schemas import ItemLine


# region Shared helpers


def _url(base_url, path=""):
    return f"{base_url}/api/v1/item_lines{path}"


def _get_headers(user_headers, method="get", allowed=True):
    return user_headers(resource="item_lines", method=method, allowed=allowed)


def _first_item_line(base_url, user_headers):
    headers = _get_headers(user_headers)
    body = requests.get(_url(base_url), headers=headers).json()

    assert body, "fixture data/item_line.json is expected to be non-empty"

    return body[0]


# endregion


# region GET /item_lines


def test_get_item_lines_returns_200_with_valid_response(
    base_url, user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(_url(base_url), headers=headers)

    assert response.status_code == 200

    body = response.json()

    assert isinstance(body, list)
    assert len(body) > 0
    assert "id" in body[0]


def test_response_body_matches_documented_schema(
    base_url, user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(_url(base_url), headers=headers)

    body = response.json()

    for raw in body:
        ItemLine.model_validate(raw)


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
    ), f"GET /item_lines took {elapsed:.2f}s, which is unreasonably slow"


@pytest.mark.xfail(
    strict=True,
    reason="API does not support query parameters for item_lines",
)
@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"page": 1}, id="pagination-page"),
        pytest.param({"limit": 5}, id="pagination-limit"),
        pytest.param({"name": "Bier en wijn"}, id="filter-name"),
        pytest.param({"description": "Jumbo assortment line: Diepvries"}, id="filter-description"),
        pytest.param({"sort": "name"}, id="sort-name"),
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
    reason="API does not support name query filtering",
)
def test_filter_name_returns_matching_item_lines(
    base_url, user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url),
        headers=headers,
        params={"name": "Bier en wijn"},
    )

    assert response.status_code == 200

    body = response.json()

    for item_line in body:
        assert item_line["name"] == "Bier en wijn"


@pytest.mark.xfail(
    strict=True,
    reason="API does not support description query filtering",
)
def test_filter_description_returns_matching_item_lines(
    base_url, user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url),
        headers=headers,
        params={
            "description": "Jumbo assortment line: Diepvries"
        },
    )

    assert response.status_code == 200

    body = response.json()

    for item_line in body:
        assert item_line["description"] == (
            "Jumbo assortment line: Diepvries"
        )


@pytest.mark.xfail(
    strict=True,
    reason="API does not support sorting item_lines",
)
def test_sort_name_returns_correctly_ordered_results(
    base_url, user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url),
        headers=headers,
        params={"sort": "name"},
    )

    assert response.status_code == 200

    body = response.json()

    names = [
        item_line["name"]
        for item_line in body
        if "name" in item_line
    ]

    assert names == sorted(names)


@pytest.mark.xfail(
    strict=True,
    reason="API does not support filtering item_lines",
)
def test_empty_result_set_returns_200_with_empty_array(
    base_url, user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url),
        headers=headers,
        params={"name": "This Item Line Does Not Exist"},
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


# region GET /item_lines/{id}


def test_get_item_line_by_id_returns_200_with_correct_resource(
    base_url, user_headers
):
    existing = _first_item_line(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}"),
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == existing


def test_get_item_line_by_id_matches_documented_schema(
    base_url, user_headers
):
    existing = _first_item_line(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}"),
        headers=headers,
    )

    ItemLine.model_validate(response.json())


@pytest.mark.xfail(
    strict=True,
    reason="API returns 200 for a nonexistent item_line instead of 404",
)
def test_get_item_line_by_nonexistent_id_returns_404(
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
    reason="API returns 500 for a malformed item_line ID instead of 400",
)
def test_get_item_line_by_malformed_id_returns_400(
    base_url, user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url, "/not-an-id"),
        headers=headers,
    )

    assert response.status_code == 400


def test_get_item_line_requires_authentication(base_url):
    response = requests.get(_url(base_url, "/1"))

    assert response.status_code == 401


def test_get_item_line_insufficient_permissions_returns_403(
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


def test_get_item_line_response_content_type_is_json(
    base_url, user_headers
):
    existing = _first_item_line(base_url, user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}"),
        headers=_get_headers(user_headers),
    )

    assert response.headers.get(
        "Content-Type", ""
    ).startswith("application/json")


def test_get_item_line_malformed_id_error_leaks_no_internal_details(
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


# region POST /item_lines


@pytest.mark.xfail(
    strict=True,
    reason="POST /item_lines returns 201 with an empty response body",
)
def test_post_item_line_returns_created_resource_with_id(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

    existing = _first_item_line(base_url, user_headers)

    payload = {
        **existing,
        "id": 555555,
        "name": "Test Item Line",
        "description": "Test Item Line Description",
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
    assert body["name"] == "Test Item Line"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "POST /item_lines returns 201 without a Location header "
        "or response body"
    ),
)
def test_post_item_line_response_points_to_new_resource(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

    existing = _first_item_line(base_url, user_headers)

    payload = {
        **existing,
        "id": 555556,
        "name": "Location Test Item Line",
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
    reason="API accepts an empty item_line payload and returns 201",
)
def test_post_item_line_missing_required_fields_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

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
def test_post_item_line_invalid_field_type_is_rejected(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

    headers = _get_headers(
        user_headers,
        method="post",
    )

    response = requests.post(
        _url(base_url),
        headers=headers,
        json={
            "id": "not-an-int",
            "name": "Bad Type Item Line",
            "description": "Bad Type Description",
        },
    )

    assert response.status_code in (400, 422)


@pytest.mark.xfail(
    strict=True,
    reason="API accepts duplicate item_line IDs and returns 201",
)
def test_post_item_line_duplicate_id_returns_conflict(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

    existing = _first_item_line(base_url, user_headers)

    headers = _get_headers(
        user_headers,
        method="post",
    )

    response = requests.post(
        _url(base_url),
        headers=headers,
        json={
            **existing,
            "name": "Duplicate Item Line",
        },
    )

    assert response.status_code in (400, 409, 422)


def test_post_item_line_is_immediately_retrievable(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

    existing = _first_item_line(base_url, user_headers)

    payload = {
        **existing,
        "id": 555557,
        "name": "Retrievable Item Line",
        "description": "Retrievable Item Line Description",
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
    assert get_response.json()["name"] == "Retrievable Item Line"


def test_post_item_line_requires_authentication(base_url):
    response = requests.post(
        _url(base_url),
        json={"name": "No Auth Item Line"},
    )

    assert response.status_code == 401


def test_post_item_line_insufficient_permissions_returns_403(
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
        json={"name": "Forbidden Item Line"},
    )

    assert response.status_code == 403


@pytest.mark.xfail(
    strict=True,
    reason="API accepts text/plain content and returns 201",
)
def test_post_item_line_wrong_content_type_is_rejected(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

    headers = {
        **_get_headers(user_headers, method="post"),
        "Content-Type": "text/plain",
    }

    response = requests.post(
        _url(base_url),
        headers=headers,
        data=json.dumps({"name": "Plain Text Item Line"}),
    )

    assert response.status_code in (400, 415)


@pytest.mark.xfail(
    strict=True,
    reason="API returns 500 for malformed JSON instead of 400",
)
def test_post_item_line_malformed_json_body_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

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


def test_post_item_line_malformed_json_body_leaks_no_internal_details(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

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


# region PUT /item_lines/{id}


def test_put_item_line_valid_payload_returns_200(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

    existing = _first_item_line(base_url, user_headers)

    updated = {
        **existing,
        "name": "Updated Item Line",
        "description": "Updated Item Line Description",
    }

    response = requests.put(
        _url(base_url, f"/{existing['id']}"),
        headers=_get_headers(user_headers, method="put"),
        json=updated,
    )

    assert response.status_code == 200


def test_put_item_line_update_is_persisted(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

    existing = _first_item_line(base_url, user_headers)

    updated = {
        **existing,
        "name": "Persisted Item Line",
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

    assert get_response.json()["name"] == "Persisted Item Line"


@pytest.mark.xfail(
    strict=True,
    reason="API returns 200 for a nonexistent item_line instead of 404",
)
def test_put_item_line_nonexistent_id_returns_404(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

    existing = _first_item_line(base_url, user_headers)

    updated = {
        **existing,
        "id": 999999,
        "name": "Ghost Item Line",
    }

    response = requests.put(
        _url(base_url, "/999999"),
        headers=_get_headers(user_headers, method="put"),
        json=updated,
    )

    assert response.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason="API returns 500 for a malformed item_line ID instead of 400",
)
def test_put_item_line_malformed_id_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

    existing = _first_item_line(base_url, user_headers)

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
def test_put_item_line_invalid_field_type_is_rejected(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

    existing = _first_item_line(base_url, user_headers)

    updated = {
        **existing,
        "id": "not-an-int",
    }

    response = requests.put(
        _url(base_url, f"/{existing['id']}"),
        headers=_get_headers(user_headers, method="put"),
        json=updated,
    )

    assert response.status_code in (400, 422)


def test_put_item_line_requires_authentication(base_url):
    response = requests.put(
        _url(base_url, "/1"),
        json={"name": "No Auth Item Line"},
    )

    assert response.status_code == 401


def test_put_item_line_insufficient_permissions_returns_403(
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
        json={"name": "Forbidden Item Line"},
    )

    assert response.status_code == 403


# endregion


# region DELETE /item_lines/{id}


def test_delete_item_line_valid_id_returns_200(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

    existing = _first_item_line(base_url, user_headers)

    response = requests.delete(
        _url(base_url, f"/{existing['id']}"),
        headers=_get_headers(user_headers, method="delete"),
    )

    assert response.status_code in (200, 204)


@pytest.mark.xfail(
    strict=True,
    reason="Returns 200 from GET instead of 404",
)
def test_delete_item_line_resource_is_actually_gone(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

    existing = _first_item_line(base_url, user_headers)

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


@pytest.mark.xfail(
    reason="Returns 200 when it should return 404.",
)
def test_delete_item_line_nonexistent_id_returns_404(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

    response = requests.delete(
        _url(base_url, "/999999"),
        headers=_get_headers(user_headers, method="delete"),
    )

    assert response.status_code == 404


@pytest.mark.xfail(
    reason="Returns 200 when it should return 400.",
)
def test_delete_item_line_malformed_id_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

    response = requests.delete(
        _url(base_url, "/not-an-id"),
        headers=_get_headers(user_headers, method="delete"),
    )

    assert response.status_code == 400


@pytest.mark.xfail(
    reason="Returns 200 despite item_line being deleted already.",
)
def test_delete_item_line_repeated_delete_returns_404(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_line.json")

    existing = _first_item_line(base_url, user_headers)

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


def test_delete_item_line_requires_authentication(base_url):
    response = requests.delete(
        _url(base_url, "/1"),
    )

    assert response.status_code == 401


def test_delete_item_line_insufficient_permissions_returns_403(
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


# region GET /item_lines/{id}/items


def test_get_item_line_items_returns_200(
    base_url, user_headers
):
    existing = _first_item_line(base_url, user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}/items"),
        headers=_get_headers(user_headers),
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_item_line_items_only_returns_correct_items(
    base_url, user_headers
):
    existing = _first_item_line(base_url, user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}/items"),
        headers=_get_headers(user_headers),
    )

    assert response.status_code == 200

    body = response.json()

    for item in body:
        if isinstance(item, dict):
            if "item_line_id" in item:
                assert item["item_line_id"] == existing["id"]


@pytest.mark.xfail(
    strict=True,
    reason="API returns 200 for nonexistent item_line instead of 404",
)
def test_get_item_line_items_nonexistent_item_line_returns_404(
    base_url, user_headers
):
    response = requests.get(
        _url(base_url, "/999999/items"),
        headers=_get_headers(user_headers),
    )

    assert response.status_code == 404


def test_get_item_line_items_empty_result_returns_200(
    base_url, user_headers
):
    response = requests.get(
        _url(base_url, "/999999/items"),
        headers=_get_headers(user_headers),
    )

    if response.status_code == 200:
        assert response.json() == []


def test_get_item_line_items_requires_authentication(base_url):
    response = requests.get(
        _url(base_url, "/1/items"),
    )

    assert response.status_code == 401


def test_get_item_line_items_insufficient_permissions_returns_403(
    base_url, user_headers
):
    headers = _get_headers(
        user_headers,
        allowed=False,
    )

    response = requests.get(
        _url(base_url, "/1/items"),
        headers=headers,
    )

    assert response.status_code == 403


def test_get_item_line_items_response_content_type_is_json(
    base_url, user_headers
):
    existing = _first_item_line(base_url, user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}/items"),
        headers=_get_headers(user_headers),
    )

    assert response.headers.get(
        "Content-Type", ""
    ).startswith("application/json")


# endregion