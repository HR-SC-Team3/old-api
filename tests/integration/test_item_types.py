import time

from pathlib import Path

import pytest

import requests

from schemas import ItemType, Item


REPO_ROOT = Path(__file__).resolve().parents[2]

ITEM_TYPES_MODEL_SOURCE = (
    REPO_ROOT / "api" / "models" / "item_types.py"
).read_text(encoding="utf-8")


# region Shared helpers


def _get_headers(user_headers, method="get", allowed=True):
    return user_headers(
        resource="item_types",
        method=method,
        allowed=allowed
    )


def _first_item_type(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/item_types",
        headers=headers
    )

    assert response.status_code == 200

    body = response.json()

    assert body, (
        "fixture data/item_type.json is expected to be non-empty"
    )

    return body[0]


def _item_type_payload(item_type_id=999999):
    return {
        "id": item_type_id,
        "name": "Test Item Type",
        "description": "Test item type description"
    }


# endregion


# region GET /item_types


def test_get_item_types_returns_200(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/item_types",
        headers=headers
    )

    assert response.status_code == 200


def test_get_item_types_returns_list(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/item_types",
        headers=headers
    )

    assert response.status_code == 200

    body = response.json()

    assert isinstance(body, list)


def test_get_item_types_schema(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/item_types",
        headers=headers
    )

    assert response.status_code == 200

    for item_type in response.json():
        ItemType.model_validate(item_type)


def test_get_item_types_content_type_is_json(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/item_types",
        headers=headers
    )

    assert response.headers.get(
        "Content-Type",
        ""
    ).startswith("application/json")


def test_get_item_types_response_time(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    start = time.monotonic()

    response = requests.get(
        f"{base_url}/api/v1/item_types",
        headers=headers
    )

    elapsed = time.monotonic() - start

    assert response.status_code == 200
    assert elapsed < 5


def test_get_item_types_without_api_key_returns_401(
    base_url
):
    response = requests.get(
        f"{base_url}/api/v1/item_types"
    )

    assert response.status_code == 401


def test_get_item_types_invalid_api_key_returns_401(
    base_url
):
    response = requests.get(
        f"{base_url}/api/v1/item_types",
        headers={
            "API_KEY": "invalid-api-key"
        }
    )

    assert response.status_code == 401


def test_get_item_types_without_permission_returns_403(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        allowed=False
    )

    response = requests.get(
        f"{base_url}/api/v1/item_types",
        headers=headers
    )

    assert response.status_code == 403


# endregion


# region GET /item_types/{id}


def test_get_item_type_returns_200(
    base_url,
    user_headers
):
    item_type = _first_item_type(
        base_url,
        user_headers
    )

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/item_types/{item_type['id']}",
        headers=headers
    )

    assert response.status_code == 200


def test_get_item_type_schema(
    base_url,
    user_headers
):
    item_type = _first_item_type(
        base_url,
        user_headers
    )

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/item_types/{item_type['id']}",
        headers=headers
    )

    assert response.status_code == 200

    ItemType.model_validate(response.json())


@pytest.mark.xfail(
    strict=True,
    reason="Current API returns 200 with null instead of 404."
)
def test_get_nonexistent_item_type_returns_404(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/item_types/999999999",
        headers=headers
    )

    assert response.status_code == 404


def test_get_nonexistent_item_type_current_behavior(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/item_types/999999999",
        headers=headers
    )

    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.xfail(
    strict=True,
    reason="Current API converts malformed IDs to 500."
)
def test_get_item_type_malformed_id_returns_400(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/item_types/not-an-id",
        headers=headers
    )

    assert response.status_code == 400


def test_get_item_type_malformed_id_current_behavior(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/item_types/not-an-id",
        headers=headers
    )

    assert response.status_code == 500


def test_get_item_type_without_api_key_returns_401(
    base_url
):
    response = requests.get(
        f"{base_url}/api/v1/item_types/1"
    )

    assert response.status_code == 401


def test_get_item_type_without_permission_returns_403(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        allowed=False
    )

    response = requests.get(
        f"{base_url}/api/v1/item_types/1",
        headers=headers
    )

    assert response.status_code == 403


# endregion


# region POST /item_types


def test_post_item_type_returns_201(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("item_type.json")

    headers = _get_headers(
        user_headers,
        method="post"
    )

    response = requests.post(
        f"{base_url}/api/v1/item_types",
        headers=headers,
        json=_item_type_payload()
    )

    assert response.status_code == 201


def test_post_item_type_is_saved(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("item_type.json")

    headers = _get_headers(
        user_headers,
        method="post"
    )

    response = requests.post(
        f"{base_url}/api/v1/item_types",
        headers=headers,
        json=_item_type_payload(999998)
    )

    assert response.status_code == 201

    get_response = requests.get(
        f"{base_url}/api/v1/item_types/999998",
        headers=_get_headers(user_headers)
    )

    assert get_response.status_code == 200

    body = get_response.json()

    assert body["id"] == 999998


def test_post_item_type_adds_timestamps(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("item_type.json")

    headers = _get_headers(
        user_headers,
        method="post"
    )

    response = requests.post(
        f"{base_url}/api/v1/item_types",
        headers=headers,
        json=_item_type_payload(999997)
    )

    assert response.status_code == 201

    get_response = requests.get(
        f"{base_url}/api/v1/item_types/999997",
        headers=_get_headers(user_headers)
    )

    assert get_response.status_code == 200

    body = get_response.json()

    assert "created_at" in body
    assert "updated_at" in body


def test_post_item_type_without_api_key_returns_401(
    base_url
):
    response = requests.post(
        f"{base_url}/api/v1/item_types",
        json=_item_type_payload()
    )

    assert response.status_code == 401


def test_post_item_type_without_permission_returns_403(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        method="post",
        allowed=False
    )

    response = requests.post(
        f"{base_url}/api/v1/item_types",
        headers=headers,
        json=_item_type_payload()
    )

    assert response.status_code == 403


@pytest.mark.xfail(
    strict=True,
    reason="Current handler does not validate missing fields."
)
def test_post_item_type_missing_fields_returns_400(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("item_type.json")

    headers = _get_headers(
        user_headers,
        method="post"
    )

    response = requests.post(
        f"{base_url}/api/v1/item_types",
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
def test_post_item_type_invalid_field_type_returns_400(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("item_type.json")

    headers = _get_headers(
        user_headers,
        method="post"
    )

    payload = _item_type_payload(999995)
    payload["id"] = "not-an-integer"

    response = requests.post(
        f"{base_url}/api/v1/item_types",
        headers=headers,
        json=payload
    )

    assert response.status_code == 400


# endregion


# region PUT /item_types/{id}


def test_put_item_type_returns_200(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("item_type.json")

    item_type = _first_item_type(
        base_url,
        user_headers
    )

    headers = _get_headers(
        user_headers,
        method="put"
    )

    updated_item_type = dict(item_type)
    updated_item_type["name"] = "Updated Item Type"

    response = requests.put(
        f"{base_url}/api/v1/item_types/{item_type['id']}",
        headers=headers,
        json=updated_item_type
    )

    assert response.status_code == 200


def test_put_item_type_update_is_persisted(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("item_type.json")

    item_type = _first_item_type(
        base_url,
        user_headers
    )

    headers = _get_headers(
        user_headers,
        method="put"
    )

    updated_item_type = dict(item_type)
    updated_item_type["name"] = "UPDATED-ITEM-TYPE"

    response = requests.put(
        f"{base_url}/api/v1/item_types/{item_type['id']}",
        headers=headers,
        json=updated_item_type
    )

    assert response.status_code == 200

    get_response = requests.get(
        f"{base_url}/api/v1/item_types/{item_type['id']}",
        headers=_get_headers(user_headers)
    )

    assert get_response.status_code == 200

    assert get_response.json()["name"] == "UPDATED-ITEM-TYPE"


def test_put_item_type_uses_full_replace():
    assert "self.data[i] = item_type" in ITEM_TYPES_MODEL_SOURCE


@pytest.mark.xfail(
    strict=True,
    reason="Current API returns 200 when item type does not exist."
)
def test_put_nonexistent_item_type_returns_404(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("item_type.json")

    headers = _get_headers(
        user_headers,
        method="put"
    )

    response = requests.put(
        f"{base_url}/api/v1/item_types/999999999",
        headers=headers,
        json=_item_type_payload(999999999)
    )

    assert response.status_code == 404


def test_put_nonexistent_item_type_current_behavior(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("item_type.json")

    headers = _get_headers(
        user_headers,
        method="put"
    )

    response = requests.put(
        f"{base_url}/api/v1/item_types/999999999",
        headers=headers,
        json=_item_type_payload(999999999)
    )

    assert response.status_code == 200


@pytest.mark.xfail(
    strict=True,
    reason="Current API converts malformed IDs to 500."
)
def test_put_item_type_malformed_id_returns_400(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        method="put"
    )

    response = requests.put(
        f"{base_url}/api/v1/item_types/not-an-id",
        headers=headers,
        json=_item_type_payload()
    )

    assert response.status_code == 400


def test_put_item_type_malformed_id_current_behavior(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        method="put"
    )

    response = requests.put(
        f"{base_url}/api/v1/item_types/not-an-id",
        headers=headers,
        json=_item_type_payload()
    )

    assert response.status_code == 500


def test_put_item_type_without_api_key_returns_401(
    base_url
):
    response = requests.put(
        f"{base_url}/api/v1/item_types/1",
        json=_item_type_payload(1)
    )

    assert response.status_code == 401


def test_put_item_type_without_permission_returns_403(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        method="put",
        allowed=False
    )

    response = requests.put(
        f"{base_url}/api/v1/item_types/1",
        headers=headers,
        json=_item_type_payload(1)
    )

    assert response.status_code == 403


# endregion


# region DELETE /item_types/{id}


def test_delete_item_type_returns_200(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("item_type.json")

    item_type = _first_item_type(
        base_url,
        user_headers
    )

    headers = _get_headers(
        user_headers,
        method="delete"
    )

    response = requests.delete(
        f"{base_url}/api/v1/item_types/{item_type['id']}",
        headers=headers
    )

    assert response.status_code == 200


def test_delete_item_type_removes_item_type(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("item_type.json")

    item_type = _first_item_type(
        base_url,
        user_headers
    )

    headers = _get_headers(
        user_headers,
        method="delete"
    )

    response = requests.delete(
        f"{base_url}/api/v1/item_types/{item_type['id']}",
        headers=headers
    )

    assert response.status_code == 200

    get_response = requests.get(
        f"{base_url}/api/v1/item_types/{item_type['id']}",
        headers=_get_headers(user_headers)
    )

    assert get_response.status_code == 200
    assert get_response.json() is None


@pytest.mark.xfail(
    strict=True,
    reason="Current API returns 200 when item type does not exist."
)
def test_delete_nonexistent_item_type_returns_404(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("item_type.json")

    headers = _get_headers(
        user_headers,
        method="delete"
    )

    response = requests.delete(
        f"{base_url}/api/v1/item_types/999999999",
        headers=headers
    )

    assert response.status_code == 404


def test_delete_nonexistent_item_type_current_behavior(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("item_type.json")

    headers = _get_headers(
        user_headers,
        method="delete"
    )

    response = requests.delete(
        f"{base_url}/api/v1/item_types/999999999",
        headers=headers
    )

    assert response.status_code == 200


def test_delete_item_type_without_api_key_returns_401(
    base_url
):
    response = requests.delete(
        f"{base_url}/api/v1/item_types/1"
    )

    assert response.status_code == 401


def test_delete_item_type_without_permission_returns_403(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        method="delete",
        allowed=False
    )

    response = requests.delete(
        f"{base_url}/api/v1/item_types/1",
        headers=headers
    )

    assert response.status_code == 403


# endregion


# region GET /item_types/{id}/items


def test_get_item_type_items_returns_200(
    base_url,
    user_headers
):
    item_type = _first_item_type(
        base_url,
        user_headers
    )

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/item_types/{item_type['id']}/items",
        headers=headers
    )

    assert response.status_code == 200


def test_get_item_type_items_returns_list(
    base_url,
    user_headers
):
    item_type = _first_item_type(
        base_url,
        user_headers
    )

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/item_types/{item_type['id']}/items",
        headers=headers
    )

    assert response.status_code == 200

    assert isinstance(
        response.json(),
        list
    )


@pytest.mark.xfail(
    strict=True,
    reason="Current API returns item IDs instead of full item objects."
)
def test_get_item_type_items_schema(
    base_url,
    user_headers
):
    item_type = _first_item_type(
        base_url,
        user_headers
    )

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/item_types/{item_type['id']}/items",
        headers=headers
    )

    assert response.status_code == 200

    for item in response.json():
        Item.model_validate(item)

def test_get_item_type_items_content_type_is_json(
    base_url,
    user_headers
):
    item_type = _first_item_type(
        base_url,
        user_headers
    )

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/item_types/{item_type['id']}/items",
        headers=headers
    )

    assert response.headers.get(
        "Content-Type",
        ""
    ).startswith("application/json")


@pytest.mark.xfail(
    strict=True,
    reason="Current API returns 200 when the parent item type does not exist."
)
def test_get_item_type_items_nonexistent_parent_returns_404(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/item_types/999999999/items",
        headers=headers
    )

    assert response.status_code == 404


def test_get_item_type_items_without_api_key_returns_401(
    base_url
):
    response = requests.get(
        f"{base_url}/api/v1/item_types/1/items"
    )

    assert response.status_code == 401


def test_get_item_type_items_without_permission_returns_403(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        allowed=False
    )

    response = requests.get(
        f"{base_url}/api/v1/item_types/1/items",
        headers=headers
    )

    assert response.status_code == 403


# endregion