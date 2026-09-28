import json
import time

from pathlib import Path

import pytest
import requests

from schemas import ItemAmount, Order


REPO_ROOT = Path(__file__).resolve().parents[2]

ORDERS_MODEL_SOURCE = (
    REPO_ROOT / "api" / "models" / "orders.py"
).read_text(encoding="utf-8")


# region Shared helpers


def _get_headers(user_headers, method="get", allowed=True):
    return user_headers(
        resource="orders",
        method=method,
        allowed=allowed
    )


def _first_order(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/orders",
        headers=headers
    )

    assert response.status_code == 200

    body = response.json()

    assert body, (
        "fixture data/order.json is expected to be non-empty"
    )

    return body[0]


def _order_payload(order_id=999999):
    return {
        "id": order_id,
        "client_id": 1,
        "order_date": "2026-09-21T10:42:25.283Z",
        "request_date": "2026-09-21T10:42:25.283Z",
        "reference": "TEST-ORDER",
        "customer_po_number": "PO-TEST",
        "order_status": "Pending",
        "shipping_notes": "Test order",
        "warehouse_id": 1,
        "ship_to_client_id": 1,
        "bill_to_client_id": 1,
        "items": [
            {
                "item_id": 1,
                "amount": 2,
                "unit_price": 10
            }
        ]
    }


# endregion


# region GET /orders


def test_get_orders_returns_200(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/orders",
        headers=headers
    )

    assert response.status_code == 200


def test_get_orders_returns_list(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/orders",
        headers=headers
    )

    assert response.status_code == 200

    body = response.json()

    assert isinstance(body, list)



def test_get_orders_content_type_is_json(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/orders",
        headers=headers
    )

    assert response.headers.get(
        "Content-Type",
        ""
    ).startswith("application/json")


def test_get_orders_response_time(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    start = time.monotonic()

    response = requests.get(
        f"{base_url}/api/v1/orders",
        headers=headers
    )

    elapsed = time.monotonic() - start

    assert response.status_code == 200
    assert elapsed < 5


def test_get_orders_without_api_key_returns_401(base_url):
    response = requests.get(
        f"{base_url}/api/v1/orders"
    )

    assert response.status_code == 401


def test_get_orders_invalid_api_key_returns_401(base_url):
    response = requests.get(
        f"{base_url}/api/v1/orders",
        headers={
            "API_KEY": "invalid-api-key"
        }
    )

    assert response.status_code == 401


def test_get_orders_without_permission_returns_403(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        allowed=False
    )

    response = requests.get(
        f"{base_url}/api/v1/orders",
        headers=headers
    )

    assert response.status_code == 403


# endregion


# region GET /orders/{id}


def test_get_order_returns_200(base_url, user_headers):
    order = _first_order(base_url, user_headers)

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/orders/{order['id']}",
        headers=headers
    )

    assert response.status_code == 200



def test_get_order_contains_items(base_url, user_headers):
    order = _first_order(base_url, user_headers)

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/orders/{order['id']}",
        headers=headers
    )

    assert response.status_code == 200

    body = response.json()

    assert "items" in body
    assert isinstance(body["items"], list)


@pytest.mark.xfail(
    strict=True,
    reason="Current API returns 200 with null instead of 404."
)
def test_get_nonexistent_order_returns_404(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/orders/999999999",
        headers=headers
    )

    assert response.status_code == 404


def test_get_nonexistent_order_current_behavior(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/orders/999999999",
        headers=headers
    )

    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.xfail(
    strict=True,
    reason="Current API converts malformed IDs to 500."
)
def test_get_order_malformed_id_returns_400(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/orders/not-an-id",
        headers=headers
    )

    assert response.status_code == 400


def test_get_order_malformed_id_current_behavior(
    base_url,
    user_headers
):
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/orders/not-an-id",
        headers=headers
    )

    assert response.status_code == 500


def test_get_order_without_api_key_returns_401(base_url):
    response = requests.get(
        f"{base_url}/api/v1/orders/1"
    )

    assert response.status_code == 401


def test_get_order_without_permission_returns_403(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        allowed=False
    )

    response = requests.get(
        f"{base_url}/api/v1/orders/1",
        headers=headers
    )

    assert response.status_code == 403


# endregion


# region POST /orders


def test_post_order_returns_201(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("order.json")

    headers = _get_headers(
        user_headers,
        method="post"
    )

    response = requests.post(
        f"{base_url}/api/v1/orders",
        headers=headers,
        json=_order_payload()
    )

    assert response.status_code == 201


@pytest.mark.xfail(
    strict=True,
    reason="Current POST endpoint returns 201 with an empty body."
)
def test_post_order_returns_created_order(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("order.json")

    headers = _get_headers(
        user_headers,
        method="post"
    )

    response = requests.post(
        f"{base_url}/api/v1/orders",
        headers=headers,
        json=_order_payload()
    )

    assert response.status_code == 201

    body = response.json()

    assert body["id"] == 999999


def test_post_order_is_saved(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("order.json")

    headers = _get_headers(
        user_headers,
        method="post"
    )

    response = requests.post(
        f"{base_url}/api/v1/orders",
        headers=headers,
        json=_order_payload(999998)
    )

    assert response.status_code == 201

    get_response = requests.get(
        f"{base_url}/api/v1/orders/999998",
        headers=_get_headers(user_headers)
    )

    assert get_response.status_code == 200

    body = get_response.json()

    assert body["id"] == 999998


def test_post_order_adds_timestamps(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("order.json")

    headers = _get_headers(
        user_headers,
        method="post"
    )

    requests.post(
        f"{base_url}/api/v1/orders",
        headers=headers,
        json=_order_payload(999997)
    )

    response = requests.get(
        f"{base_url}/api/v1/orders/999997",
        headers=_get_headers(user_headers)
    )

    assert response.status_code == 200

    body = response.json()

    assert "created_at" in body
    assert "updated_at" in body


def test_post_order_without_api_key_returns_401(base_url):
    response = requests.post(
        f"{base_url}/api/v1/orders",
        json=_order_payload()
    )

    assert response.status_code == 401


def test_post_order_without_permission_returns_403(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        method="post",
        allowed=False
    )

    response = requests.post(
        f"{base_url}/api/v1/orders",
        headers=headers,
        json=_order_payload()
    )

    assert response.status_code == 403


@pytest.mark.xfail(
    strict=True,
    reason="Current handler does not validate missing fields."
)
def test_post_order_missing_fields_returns_400(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("order.json")

    headers = _get_headers(
        user_headers,
        method="post"
    )

    response = requests.post(
        f"{base_url}/api/v1/orders",
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
def test_post_order_invalid_field_type_returns_400(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("order.json")

    headers = _get_headers(
        user_headers,
        method="post"
    )

    payload = _order_payload(999995)
    payload["client_id"] = "not-an-integer"

    response = requests.post(
        f"{base_url}/api/v1/orders",
        headers=headers,
        json=payload
    )

    assert response.status_code == 400


@pytest.mark.xfail(
    strict=True,
    reason="Current handler returns 500 for malformed JSON."
)
def test_post_order_malformed_json_returns_400(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        method="post"
    )

    response = requests.post(
        f"{base_url}/api/v1/orders",
        headers=headers,
        data="{ invalid json"
    )

    assert response.status_code == 400


# endregion


# region PUT /orders/{id}


def test_put_order_returns_200(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("order.json")

    order = _first_order(base_url, user_headers)

    headers = _get_headers(
        user_headers,
        method="put"
    )

    updated_order = dict(order)
    updated_order["reference"] = "UPDATED-ORDER"

    response = requests.put(
        f"{base_url}/api/v1/orders/{order['id']}",
        headers=headers,
        json=updated_order
    )

    assert response.status_code == 200

def test_put_order_update_is_persisted(
        base_url,
        user_headers,
        preserve_data_files
    ):
        preserve_data_files("order.json")
        order = _first_order(base_url, user_headers)

        headers = _get_headers(
            user_headers,
            method="put"
        )

        updated_order = dict(order)
        updated_order["reference"] = "UPDATED-REFERENCE"

        response = requests.put(
            f"{base_url}/api/v1/orders/{order['id']}",
            headers=headers,
            json=updated_order
        )

        print("STATUS:", response.status_code)
        print("BODY:", response.text)

        assert response.status_code == 200

        get_response = requests.get(
            f"{base_url}/api/v1/orders/{order['id']}",
            headers=_get_headers(user_headers)
        )

        assert get_response.status_code == 200
        assert get_response.json()["reference"] == "UPDATED-REFERENCE"


def test_put_order_uses_full_replace():
    assert "self.data[i] = order" in ORDERS_MODEL_SOURCE


@pytest.mark.xfail(
    strict=True,
    reason="Current API returns 200 when order does not exist."
)
def test_put_nonexistent_order_returns_404(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("order.json")

    headers = _get_headers(
        user_headers,
        method="put"
    )

    response = requests.put(
        f"{base_url}/api/v1/orders/999999999",
        headers=headers,
        json=_order_payload(999999999)
    )

    assert response.status_code == 404


def test_put_nonexistent_order_current_behavior(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("order.json")

    headers = _get_headers(
        user_headers,
        method="put"
    )

    response = requests.put(
        f"{base_url}/api/v1/orders/999999999",
        headers=headers,
        json=_order_payload(999999999)
    )

    assert response.status_code == 200


@pytest.mark.xfail(
    strict=True,
    reason="Current API converts malformed IDs to 500."
)
def test_put_order_malformed_id_returns_400(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        method="put"
    )

    response = requests.put(
        f"{base_url}/api/v1/orders/not-an-id",
        headers=headers,
        json=_order_payload()
    )

    assert response.status_code == 400


def test_put_order_malformed_id_current_behavior(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        method="put"
    )

    response = requests.put(
        f"{base_url}/api/v1/orders/not-an-id",
        headers=headers,
        json=_order_payload()
    )

    assert response.status_code == 500


def test_put_order_without_api_key_returns_401(base_url):
    response = requests.put(
        f"{base_url}/api/v1/orders/1",
        json=_order_payload(1)
    )

    assert response.status_code == 401


def test_put_order_without_permission_returns_403(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        method="put",
        allowed=False
    )

    response = requests.put(
        f"{base_url}/api/v1/orders/1",
        headers=headers,
        json=_order_payload(1)
    )

    assert response.status_code == 403


# endregion


# region DELETE /orders/{id}


def test_delete_order_returns_200(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("order.json")

    order = _first_order(base_url, user_headers)

    headers = _get_headers(
        user_headers,
        method="delete"
    )

    response = requests.delete(
        f"{base_url}/api/v1/orders/{order['id']}",
        headers=headers
    )

    assert response.status_code == 200


def test_delete_order_removes_order(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("order.json")

    order = _first_order(base_url, user_headers)

    headers = _get_headers(
        user_headers,
        method="delete"
    )

    response = requests.delete(
        f"{base_url}/api/v1/orders/{order['id']}",
        headers=headers
    )

    assert response.status_code == 200

    get_response = requests.get(
        f"{base_url}/api/v1/orders/{order['id']}",
        headers=_get_headers(user_headers)
    )

    assert get_response.status_code == 200
    assert get_response.json() is None


@pytest.mark.xfail(
    strict=True,
    reason="Current API returns 200 when order does not exist."
)
def test_delete_nonexistent_order_returns_404(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("order.json")

    headers = _get_headers(
        user_headers,
        method="delete"
    )

    response = requests.delete(
        f"{base_url}/api/v1/orders/999999999",
        headers=headers
    )

    assert response.status_code == 404


def test_delete_order_without_api_key_returns_401(base_url):
    response = requests.delete(
        f"{base_url}/api/v1/orders/1"
    )

    assert response.status_code == 401


def test_delete_order_without_permission_returns_403(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        method="delete",
        allowed=False
    )

    response = requests.delete(
        f"{base_url}/api/v1/orders/1",
        headers=headers
    )

    assert response.status_code == 403


# endregion


# region GET /orders/{id}/items


def test_get_order_items_returns_200(
    base_url,
    user_headers
):
    order = _first_order(base_url, user_headers)

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/orders/{order['id']}/items",
        headers=headers
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_order_items_schema(
    base_url,
    user_headers
):
    order = _first_order(base_url, user_headers)

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/orders/{order['id']}/items",
        headers=headers
    )

    assert response.status_code == 200

    for item in response.json():
        ItemAmount.model_validate(item)


def test_get_order_items_only_contains_expected_fields(
    base_url,
    user_headers
):
    order = _first_order(base_url, user_headers)

    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/orders/{order['id']}/items",
        headers=headers
    )

    assert response.status_code == 200

    for item in response.json():
        assert set(item.keys()) == {
            "item_id",
            "amount"
        }


def test_get_order_items_without_api_key(base_url):
    response = requests.get(
        f"{base_url}/api/v1/orders/1/items"
    )

    assert response.status_code == 401


def test_get_order_items_without_permission(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        allowed=False
    )

    response = requests.get(
        f"{base_url}/api/v1/orders/1/items",
        headers=headers
    )

    assert response.status_code == 403


# endregion


# region PUT /orders/{id}/items


def test_put_order_items_returns_200(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("order.json")

    order = _first_order(base_url, user_headers)

    headers = _get_headers(
        user_headers,
        method="put"
    )

    items = [
        {
            "item_id": 1,
            "amount": 2
        }
    ]

    response = requests.put(
        f"{base_url}/api/v1/orders/{order['id']}/items",
        headers=headers,
        json=items
    )

    assert response.status_code == 200


def test_put_order_items_is_persisted(
    base_url,
    user_headers,
    preserve_data_files
):
    preserve_data_files("order.json")

    order = _first_order(base_url, user_headers)

    headers = _get_headers(
        user_headers,
        method="put"
    )

    items = [
        {
            "item_id": 1,
            "amount": 5
        }
    ]

    response = requests.put(
        f"{base_url}/api/v1/orders/{order['id']}/items",
        headers=headers,
        json=items
    )

    assert response.status_code == 200

    get_response = requests.get(
        f"{base_url}/api/v1/orders/{order['id']}/items",
        headers=_get_headers(user_headers)
    )

    assert get_response.status_code == 200

    assert get_response.json() == items


def test_put_order_items_without_api_key(base_url):
    response = requests.put(
        f"{base_url}/api/v1/orders/1/items",
        json=[]
    )

    assert response.status_code == 401


def test_put_order_items_without_permission(
    base_url,
    user_headers
):
    headers = _get_headers(
        user_headers,
        method="put",
        allowed=False
    )

    response = requests.put(
        f"{base_url}/api/v1/orders/1/items",
        headers=headers,
        json=[]
    )

    assert response.status_code == 403


# endregion