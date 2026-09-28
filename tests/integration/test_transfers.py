"""
/transfers endpoint tests: GET (collection), GET /{id}, POST, PUT /{id},
DELETE /{id}, GET /{id}/items, PUT /{id}/commit.

These tests exercise the checklist for "As a developer I want to know what
each endpoint does" (sub-issues: GET /transfers, POST /transfers,
GET /transfers/{id}, PUT /transfers/{id}, DELETE /transfers/{id},
GET /transfers/{id}/items, PUT /transfers/{id}/commit). Several tests are
written against the *documented*/expected behavior and are marked
`xfail(strict=True)` where the live server currently does something else.
This pins the actual, observed behavior so it shows up clearly in test
output and turns into a loud XPASS failure the moment someone "fixes" it,
prompting an update to these notes rather than a silent behavior change.

The file is split into `# region` blocks below, one per endpoint, plus a
shared-helpers region at the top, collapse/expand them in an editor that
supports region folding to jump straight to one endpoint's tests.

Root cause notes shared across the whole resource:

* `transfer_id = int(paths[1])` (GET/PUT/DELETE by id, and the nested
  `/items` and `/commit` routes) is never guarded, so a non-numeric id
  raises an uncaught `ValueError` caught only by the generic
  `except Exception: send_response(500)` wrapper in each verb's handler.
  Actual: 500. Expected: 400.
* `Transfers.get_transfer()`/`get_transfers()` return `None`/the raw list
  as-is with no existence check, and `main.py` serializes that straight
  back with a 200. A single-resource GET for an unknown id is therefore
  200 with body `null` instead of 404.
* `Transfers.add_transfer()` performs no validation whatsoever. Critically,
  it does not require an `id` field: a payload without one is appended to
  the in-memory collection and written to disk via `save()` *before* the
  handler crashes trying to log the new transfer's id for a notification,
  so the client sees a 500 (looking like a clean failure) while the
  id-less row is actually persisted. `Transfers.get_transfers()`
  unconditionally indexes `x["id"]` while iterating the whole collection,
  so that single leftover row turns *every* GET /transfers request into a
  500 until the row is removed. One malformed POST can take down the whole
  collection endpoint's read path.
"""

import json
import time
from pathlib import Path

import pytest
import requests

from schemas import ItemAmount, Transfer

REPO_ROOT = Path(__file__).resolve().parents[2]
TRANSFERS_MODEL_SOURCE = (REPO_ROOT / "api" / "models" / "transfers.py").read_text(
    encoding="utf-8"
)


# region Shared helpers
def _url(base_url, path=""):
    return f"{base_url}/api/v1/transfers{path}"


def _get_headers(user_headers, method="get", allowed=True):
    return user_headers(resource="transfers", method=method, allowed=allowed)


def _first_transfer(base_url, user_headers, status=None):
    headers = _get_headers(user_headers)
    body = requests.get(_url(base_url), headers=headers).json()
    assert body, "fixture data/transfer.json is expected to be non-empty"
    if status is not None:
        body = [t for t in body if t["transfer_status"] == status]
        assert body, f"expected at least one fixture transfer with status={status!r}"
    return body[0]


# endregion


# region GET /transfers (collection)
def test_get_transfers_returns_200_with_valid_response(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(_url(base_url), headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) > 0
    assert "id" in body[0]


def test_response_body_matches_documented_schema(base_url, user_headers):
    """Field names, types and nesting (the `items` sub-list) must match `Transfer`."""
    headers = _get_headers(user_headers)
    response = requests.get(_url(base_url), headers=headers)

    body = response.json()
    for raw in body:
        Transfer.model_validate(raw)


def test_response_content_type_is_json(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(_url(base_url), headers=headers)

    assert response.headers.get("Content-Type", "").startswith("application/json")


def test_response_time_is_reasonable(base_url, user_headers):
    headers = _get_headers(user_headers)

    start = time.monotonic()
    response = requests.get(_url(base_url), headers=headers)
    elapsed = time.monotonic() - start

    assert response.status_code == 200
    assert (
        elapsed < 0.5
    ), f"GET /transfers took {elapsed:.2f}s, which is unreasonably slow"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "do_GET splits the raw request path on '/' without ever stripping "
        "the query string. Any request with a '?...' on it turns paths[0] "
        "into e.g. 'transfers?page=1' instead of 'transfers', which is not "
        "a key in endpoint_access, so a fully-authorized user is rejected "
        "with 403 instead of the query string being honoured or ignored."
    ),
)
@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"page": 1}, id="pagination-page"),
        pytest.param({"limit": 5}, id="pagination-limit"),
        pytest.param({"transfer_status": "Processed"}, id="filter-status"),
        pytest.param({"sort": "reference"}, id="sort-reference"),
        pytest.param({"page": -1}, id="invalid-negative-page"),
        pytest.param({"totally_unknown_key": "x"}, id="unknown-key"),
    ],
)
def test_query_params_are_honoured_or_gracefully_ignored(
    base_url, user_headers, params
):
    headers = _get_headers(user_headers)
    response = requests.get(
        _url(base_url), headers=headers, params=params
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_query_params_currently_return_403(base_url, user_headers):
    """Pins the *actual* behavior described above."""
    headers = _get_headers(user_headers)
    response = requests.get(
        _url(base_url), headers=headers, params={"page": 1}
    )

    assert response.status_code == 403
    assert response.text == ""


@pytest.mark.skip(
    reason=(
        "GET /transfers has no implemented filtering, so there is no "
        "supported way to induce an empty result set without mutating the "
        "shared data/transfer.json fixture out from under other tests. "
        "Redesign suggestion: support a filter (e.g. ?transfer_status=) so "
        "this is testable."
    )
)
def test_empty_result_set_returns_200_with_empty_array(base_url, user_headers):
    pass


def test_insufficient_permissions_returns_403(base_url, user_headers):
    headers = _get_headers(user_headers, allowed=False)
    response = requests.get(_url(base_url), headers=headers)

    assert response.status_code == 403


def test_missing_api_key_is_rejected_with_401(base_url):
    response = requests.get(_url(base_url))

    assert response.status_code == 401


def test_invalid_api_key_is_rejected_with_401(base_url):
    response = requests.get(
        _url(base_url), headers={"API_KEY": "not-a-real-key"}
    )

    assert response.status_code == 401


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Error responses (401 here, 403 for query params above) have an "
        "empty body and no Content-Type header at all, unlike success "
        "responses which are always application/json. There is no "
        "consistent error schema across the API to assert against. "
        'Redesign suggestion: every error response should return a JSON '
        'body with a stable shape, e.g. {"error": {"code": ..., "message": ...}}.'
    ),
)
def test_error_response_has_consistent_json_schema(base_url):
    response = requests.get(_url(base_url))

    assert response.status_code == 401
    assert response.headers.get("Content-Type", "").startswith("application/json")
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


# region GET /transfers/{id}


def test_get_transfer_by_id_returns_200_with_correct_resource(base_url, user_headers):
    existing = _first_transfer(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}"), headers=headers
    )

    assert response.status_code == 200
    assert response.json() == existing


def test_get_transfer_by_id_matches_documented_schema(base_url, user_headers):
    existing = _first_transfer(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}"), headers=headers
    )

    Transfer.model_validate(response.json())


@pytest.mark.xfail(
    strict=True,
    reason=(
        "get_transfer() returns None for an unknown id, and main.py writes "
        "json.dumps(None) straight back with a 200, instead of a 404. "
        "Actual: 200 with body `null`. Expected: 404."
    ),
)
def test_get_transfer_by_nonexistent_id_returns_404(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(_url(base_url, f"/999999"), headers=headers)

    assert response.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason=(
        "transfer_id = int(paths[1]) is not guarded, so a non-numeric id "
        "raises an uncaught ValueError that bubbles up to the generic "
        "except Exception: send_response(500) in do_GET. "
        "Actual: 500 Internal Server Error. Expected: 400 Bad Request."
    ),
)
def test_get_transfer_by_malformed_id_returns_400(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(_url(base_url, f"/not-an-id"), headers=headers)

    assert response.status_code == 400


def test_get_transfer_items_are_consistent_with_nested_endpoint(base_url, user_headers):
    """
    The `items` field embedded in GET /transfers/{id} is derived from the
    same TransferItems pool as GET /transfers/{id}/items; the two should
    always agree.
    """
    existing = _first_transfer(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}/items"), headers=headers
    )

    assert response.status_code == 200
    assert response.json() == existing["items"]


def test_get_transfer_by_id_requires_authentication(base_url):
    response = requests.get(_url(base_url, f"/1"))

    assert response.status_code == 401


def test_get_transfer_by_id_insufficient_permissions_returns_403(
    base_url, user_headers
):
    headers = _get_headers(user_headers, allowed=False)
    response = requests.get(_url(base_url, f"/1"), headers=headers)

    assert response.status_code == 403


def test_get_transfer_by_id_response_content_type_is_json(base_url, user_headers):
    existing = _first_transfer(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}"), headers=headers
    )

    assert response.headers.get("Content-Type", "").startswith("application/json")


def test_get_transfer_by_malformed_id_error_leaks_no_internal_details(
    base_url, user_headers
):
    headers = _get_headers(user_headers)
    response = requests.get(_url(base_url, f"/not-an-id"), headers=headers)

    text_lower = response.text.lower()
    for leak_indicator in ("traceback", "exception", "valueerror", 'file "', "line "):
        assert leak_indicator not in text_lower


# endregion


# region POST /transfers


def test_post_transfer_valid_payload_returns_201(base_url, user_headers, preserve_data_files):
    preserve_data_files("transfer.json", "transfer_item.json")
    headers = _get_headers(user_headers, method="post")
    payload = {
        "id": 555555,
        "reference": "TRF-TEST-1",
        "from_location_id": 369,
        "to_location_id": 320,
        "items": [{"item_id": 190, "amount": 5}],
    }

    response = requests.post(
        _url(base_url), headers=headers, json=payload
    )

    assert response.status_code == 201


@pytest.mark.xfail(
    strict=True,
    reason=(
        "POST /transfers returns 201 with an empty body: no created "
        "resource, no generated id, nothing. Redesign suggestion: return "
        "the created resource (with its id) in the body."
    ),
)
def test_post_transfer_returns_created_resource(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    headers = _get_headers(user_headers, method="post")
    payload = {
        "id": 555556,
        "reference": "TRF-TEST-2",
        "from_location_id": 369,
        "to_location_id": 320,
        "items": [{"item_id": 190, "amount": 5}],
    }

    response = requests.post(
        _url(base_url), headers=headers, json=payload
    )

    assert response.status_code == 201
    body = response.json()
    Transfer.model_validate(body)
    for key, value in payload.items():
        assert body[key] == value


@pytest.mark.xfail(
    strict=True,
    reason=(
        "No Location header and no body are returned on 201, so there is "
        "no way for a client to discover the URL of the resource it just "
        "created."
    ),
)
def test_post_transfer_response_points_to_new_resource(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    headers = _get_headers(user_headers, method="post")

    response = requests.post(
        _url(base_url),
        headers=headers,
        json={
            "id": 555557,
            "reference": "TRF-LOCATE",
            "from_location_id": 369,
            "to_location_id": 320,
        },
    )

    assert response.status_code == 201
    assert "Location" in response.headers


@pytest.mark.xfail(
    strict=True,
    reason=(
        "No request validation exists at all: an empty payload missing "
        "every documented required-looking field (including `id`) is not "
        "rejected up front. add_transfer() happily stores it (and "
        "Transfers.save() persists it to disk) *before* the handler tries "
        "to log f\"...{new_transfer['id']}\" for the notification, which "
        "raises an uncaught KeyError since there never was an `id`. Actual: "
        "500, but only *after* the malformed row was already saved -- see "
        "test_post_transfer_missing_id_corrupts_the_whole_collection below "
        "for the fallout. Expected: 400/422 up front, with nothing persisted."
    ),
)
def test_post_transfer_missing_required_fields_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    headers = _get_headers(user_headers, method="post")

    response = requests.post(_url(base_url), headers=headers, json={})

    assert response.status_code in (400, 422)


def test_post_transfer_missing_id_corrupts_the_whole_collection(
    base_url, user_headers, preserve_data_files
):
    """
    Documents the actual, observed blast radius of the validation gap above.
    An empty POST body reports 500 (see test_post_transfer_missing_required_
    fields_returns_400), which looks like the request simply failed -- but
    add_transfer() already appended the id-less row and Transfers.save()
    already wrote it to disk *before* the KeyError is raised. Because
    get_transfers() indexes x["id"] while iterating the *whole* collection,
    that one leftover row breaks every subsequent GET /transfers request
    with a 500, even though the client that caused it already moved on
    believing its request failed cleanly. (get_transfer(id) is spared for
    any id that appears earlier in the list than the leftover row, since it
    returns as soon as it finds a match -- the leftover row is always
    appended last -- so this is demonstrated against the collection
    endpoint rather than GET /transfers/{id}.)
    """
    preserve_data_files("transfer.json", "transfer_item.json")
    headers = _get_headers(user_headers, method="post")

    post_response = requests.post(
        _url(base_url), headers=headers, json={}
    )
    assert post_response.status_code == 500

    get_headers = _get_headers(user_headers)

    collection_response = requests.get(
        _url(base_url), headers=get_headers
    )
    assert collection_response.status_code == 500


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Field values are stored as-is with no type checking: an `id` of "
        "type string is accepted with 201 instead of being rejected. "
        "Expected: 400/422 for a type mismatch against the documented "
        "integer id."
    ),
)
def test_post_transfer_invalid_field_type_is_rejected(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    headers = _get_headers(user_headers, method="post")

    response = requests.post(
        _url(base_url),
        headers=headers,
        json={"id": "not-an-int", "reference": "TRF-BADTYPE"},
    )

    assert response.status_code in (400, 422)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "There is no id uniqueness check anywhere in Transfers.add_transfer: "
        "POSTing a second transfer with an id that already exists is "
        "accepted with 201 instead of a 409/400 conflict."
    ),
)
def test_post_transfer_duplicate_id_returns_conflict(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    existing = _first_transfer(base_url, user_headers)
    headers = _get_headers(user_headers, method="post")

    response = requests.post(
        _url(base_url),
        headers=headers,
        json={**existing, "reference": "Duplicate of " + existing["reference"]},
    )

    assert response.status_code == 409


def test_post_transfer_is_immediately_retrievable(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    headers = _get_headers(user_headers, method="post")
    payload = {
        "id": 555558,
        "reference": "TRF-RETRIEVABLE",
        "from_location_id": 369,
        "to_location_id": 320,
        "items": [{"item_id": 190, "amount": 3}],
    }

    create_response = requests.post(
        _url(base_url), headers=headers, json=payload
    )
    assert create_response.status_code == 201

    get_headers = _get_headers(user_headers)
    get_response = requests.get(
        _url(base_url, f"/555558"), headers=get_headers
    )

    assert get_response.status_code == 200
    assert get_response.json() is not None
    assert get_response.json()["reference"] == "TRF-RETRIEVABLE"
    assert get_response.json()["items"] == [{"item_id": 190, "amount": 3}]


@pytest.mark.xfail(
    strict=True,
    reason=(
        "add_transfer() never checks that from_location_id/to_location_id "
        "reference an existing location. A payload pointing at nonexistent "
        "location ids is accepted with 201 instead of being rejected."
    ),
)
def test_post_transfer_invalid_foreign_key_is_rejected(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    headers = _get_headers(user_headers, method="post")

    response = requests.post(
        _url(base_url),
        headers=headers,
        json={
            "id": 555559,
            "reference": "TRF-BADFK",
            "from_location_id": 999999999,
            "to_location_id": 999999998,
        },
    )

    assert response.status_code in (400, 422)


def test_post_transfer_requires_authentication(base_url):
    response = requests.post(
        _url(base_url), json={"reference": "No Auth Transfer"}
    )

    assert response.status_code == 401


def test_post_transfer_insufficient_permissions_returns_403(base_url, user_headers):
    headers = _get_headers(user_headers, method="post", allowed=False)
    response = requests.post(
        _url(base_url),
        headers=headers,
        json={"reference": "Forbidden Transfer"},
    )

    assert response.status_code == 403


@pytest.mark.xfail(
    strict=True,
    reason=(
        "do_POST never inspects the Content-Type header before "
        "json.loads()-ing the body, so a request sent as text/plain is "
        "accepted exactly like application/json. Expected: a non-JSON "
        "Content-Type should be rejected."
    ),
)
def test_post_transfer_wrong_content_type_is_rejected(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    headers = {
        **_get_headers(user_headers, method="post"),
        "Content-Type": "text/plain",
    }

    response = requests.post(
        _url(base_url),
        headers=headers,
        data=json.dumps({"reference": "Plain Text Transfer"}),
    )

    assert response.status_code in (400, 415)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "A malformed (non-JSON) body makes json.loads() raise, which is "
        "caught only by the generic except Exception: send_response(500) "
        "wrapper in do_POST. Actual: 500. Expected: 400/422."
    ),
)
def test_post_transfer_malformed_json_body_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    headers = {
        **_get_headers(user_headers, method="post"),
        "Content-Type": "application/json",
    }

    response = requests.post(
        _url(base_url), headers=headers, data="{not valid json"
    )

    assert response.status_code in (400, 422)


def test_post_transfer_malformed_json_body_leaks_no_internal_details(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    headers = {
        **_get_headers(user_headers, method="post"),
        "Content-Type": "application/json",
    }

    response = requests.post(
        _url(base_url), headers=headers, data="{not valid json"
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


# region PUT /transfers/{id}


def test_put_transfer_valid_payload_returns_200(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    existing = _first_transfer(base_url, user_headers)
    headers = _get_headers(user_headers, method="put")

    updated = {**existing, "reference": "TRF-UPDATED"}
    response = requests.put(
        _url(base_url, f"/{existing['id']}"), headers=headers, json=updated
    )

    assert response.status_code == 200


def test_put_transfer_update_is_persisted(base_url, user_headers, preserve_data_files):
    preserve_data_files("transfer.json", "transfer_item.json")
    existing = _first_transfer(base_url, user_headers)
    headers = _get_headers(user_headers, method="put")

    updated = {**existing, "reference": "TRF-PERSISTED", "items": [{"item_id": 190, "amount": 42}]}
    put_response = requests.put(
        _url(base_url, f"/{existing['id']}"), headers=headers, json=updated
    )
    assert put_response.status_code == 200

    get_headers = _get_headers(user_headers)
    get_response = requests.get(
        _url(base_url, f"/{existing['id']}"), headers=get_headers
    )
    assert get_response.json()["reference"] == "TRF-PERSISTED"
    assert get_response.json()["items"] == [{"item_id": 190, "amount": 42}]


@pytest.mark.xfail(
    strict=True,
    reason=(
        "update_transfer() loops over the data looking for a matching id "
        "and simply does nothing if none is found; handle_put_version_1 "
        "always sends 200 regardless. Actual: 200 for a nonexistent id. "
        "Expected: 404."
    ),
)
def test_put_transfer_nonexistent_id_returns_404(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    headers = _get_headers(user_headers, method="put")

    response = requests.put(
        _url(base_url, f"/999999"),
        headers=headers,
        json={"id": 999999, "reference": "Ghost Transfer"},
    )

    assert response.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Same unguarded int(paths[1]) as GET/DELETE by id: a non-numeric "
        "id raises an uncaught ValueError caught only by the generic 500 "
        "handler. Actual: 500. Expected: 400."
    ),
)
def test_put_transfer_malformed_id_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    headers = _get_headers(user_headers, method="put")

    response = requests.put(
        _url(base_url, f"/not-an-id"),
        headers=headers,
        json={"reference": "x"},
    )

    assert response.status_code == 400


def test_put_transfer_replaces_the_whole_record_per_source():
    """
    Transfers.update_transfer() does `self.data[i] = transfer`, i.e. a full
    replace of the stored record with whatever the client sent (items are
    handled separately via the TransferItems pool). Not a merge of only the
    provided fields: a client that PUTs a partial payload would silently
    drop every top-level field it omitted.
    """
    assert "self.data[i] = transfer" in TRANSFERS_MODEL_SOURCE


@pytest.mark.xfail(
    strict=True,
    reason=(
        "update_transfer() never checks that from_location_id/to_location_id "
        "reference an existing location. Updating a transfer to point at "
        "nonexistent location ids is accepted with 200 instead of being "
        "rejected."
    ),
)
def test_put_transfer_invalid_foreign_key_is_rejected(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    existing = _first_transfer(base_url, user_headers)
    headers = _get_headers(user_headers, method="put")

    response = requests.put(
        _url(base_url, f"/{existing['id']}"),
        headers=headers,
        json={
            **existing,
            "from_location_id": 999999999,
            "to_location_id": 999999998,
        },
    )

    assert response.status_code in (400, 422)


def test_put_transfer_requires_authentication(base_url):
    response = requests.put(
        _url(base_url, f"/1"), json={"reference": "No Auth Transfer"}
    )

    assert response.status_code == 401


def test_put_transfer_insufficient_permissions_returns_403(base_url, user_headers):
    headers = _get_headers(user_headers, method="put", allowed=False)
    response = requests.put(
        _url(base_url, f"/1"),
        headers=headers,
        json={"reference": "Forbidden Transfer"},
    )

    assert response.status_code == 403


# endregion


# region DELETE /transfers/{id}


def test_delete_transfer_valid_id_returns_200(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    existing = _first_transfer(base_url, user_headers)
    headers = _get_headers(user_headers, method="delete")

    response = requests.delete(
        _url(base_url, f"/{existing['id']}"), headers=headers
    )

    assert response.status_code in (200, 204)


def test_delete_transfer_resource_is_actually_gone(
    base_url, user_headers, preserve_data_files
):
    """
    remove_transfer() does delete the row from the in-memory/on-disk
    collection, but get_transfer() still returns 200 with a `null` body
    instead of 404 for the now-missing id (same gap as GET-by-nonexistent-id
    above), so "gone" is only observable as `null`, not as a 404.
    """
    preserve_data_files("transfer.json", "transfer_item.json")
    existing = _first_transfer(base_url, user_headers)
    delete_headers = _get_headers(user_headers, method="delete")

    delete_response = requests.delete(
        _url(base_url, f"/{existing['id']}"), headers=delete_headers
    )
    assert delete_response.status_code in (200, 204)

    get_headers = _get_headers(user_headers)
    get_response = requests.get(
        _url(base_url, f"/{existing['id']}"), headers=get_headers
    )
    assert get_response.json() is None


def test_delete_transfer_also_removes_its_items(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    existing = _first_transfer(base_url, user_headers)
    assert existing["items"], "fixture transfer is expected to have items"
    delete_headers = _get_headers(user_headers, method="delete")

    delete_response = requests.delete(
        _url(base_url, f"/{existing['id']}"), headers=delete_headers
    )
    assert delete_response.status_code in (200, 204)

    get_headers = _get_headers(user_headers)
    items_response = requests.get(
        _url(base_url, f"/{existing['id']}/items"), headers=get_headers
    )
    assert items_response.status_code == 200
    assert items_response.json() == []


@pytest.mark.xfail(
    strict=True,
    reason=(
        "remove_transfer() is a silent no-op if the id doesn't match "
        "anything, and handle_delete_version_1 always sends 200 regardless. "
        "Actual: 200 for a nonexistent id. Expected: 404."
    ),
)
def test_delete_transfer_nonexistent_id_returns_404(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    headers = _get_headers(user_headers, method="delete")

    response = requests.delete(_url(base_url, f"/999999"), headers=headers)

    assert response.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Same unguarded int(paths[1]) as GET/PUT by id. Actual: 500. "
        "Expected: 400."
    ),
)
def test_delete_transfer_malformed_id_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    headers = _get_headers(user_headers, method="delete")

    response = requests.delete(
        _url(base_url, f"/not-an-id"), headers=headers
    )

    assert response.status_code == 400


@pytest.mark.xfail(
    strict=True,
    reason=(
        "First DELETE is expected to remove the resource (200/204) and a "
        "second DELETE on the same, now-gone id is expected to 404. "
        "remove_transfer() is a silent no-op when the id isn't found, and "
        "handle_delete_version_1 always sends 200 regardless of whether "
        "anything was removed. The second delete still gets 200 instead of "
        "404 because there is no existence check before responding."
    ),
)
def test_delete_transfer_repeated_delete_returns_404_not_200(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json")
    existing = _first_transfer(base_url, user_headers)
    headers = _get_headers(user_headers, method="delete")

    first = requests.delete(
        _url(base_url, f"/{existing['id']}"), headers=headers
    )
    second = requests.delete(
        _url(base_url, f"/{existing['id']}"), headers=headers
    )

    assert first.status_code in (200, 204)
    assert second.status_code == 404


def test_delete_transfer_requires_authentication(base_url):
    response = requests.delete(_url(base_url, f"/1"))

    assert response.status_code == 401


def test_delete_transfer_insufficient_permissions_returns_403(base_url, user_headers):
    headers = _get_headers(user_headers, method="delete", allowed=False)
    response = requests.delete(_url(base_url, f"/1"), headers=headers)

    assert response.status_code == 403


# endregion


# region GET /transfers/{id}/items


def test_get_transfer_items_returns_200(base_url, user_headers):
    existing = _first_transfer(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}/items"), headers=headers
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_transfer_items_schema(base_url, user_headers):
    existing = _first_transfer(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}/items"), headers=headers
    )

    for raw in response.json():
        ItemAmount.model_validate(raw)


def test_get_transfer_items_only_contains_expected_fields(base_url, user_headers):
    """
    get_items_in_transfer() explicitly projects each row down to
    {item_id, amount}: no transfer_id, no surrogate row id should leak
    through the nested endpoint.
    """
    existing = _first_transfer(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}/items"), headers=headers
    )

    for raw in response.json():
        assert set(raw.keys()) == {"item_id", "amount"}


@pytest.mark.xfail(
    strict=True,
    reason=(
        "get_items_in_transfer() filters TransferItems by transfer_id with "
        "no existence check on the parent transfer at all. A nonexistent "
        "parent id returns 200 with an empty array (indistinguishable from "
        "a real transfer that simply has no items) instead of 404."
    ),
)
def test_get_transfer_items_nonexistent_parent_returns_404(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url, f"/999999/items"), headers=headers
    )

    assert response.status_code == 404


def test_get_transfer_items_requires_authentication(base_url):
    response = requests.get(_url(base_url, f"/1/items"))

    assert response.status_code == 401


def test_get_transfer_items_insufficient_permissions_returns_403(
    base_url, user_headers
):
    headers = _get_headers(user_headers, allowed=False)
    response = requests.get(_url(base_url, f"/1/items"), headers=headers)

    assert response.status_code == 403


def test_get_transfer_items_response_content_type_is_json(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(_url(base_url, f"/1/items"), headers=headers)

    assert response.headers.get("Content-Type", "").startswith("application/json")


# endregion


# region PUT /transfers/{id}/commit


def test_put_transfer_commit_valid_transfer_returns_200_and_marks_processed(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json", "inventory.json")
    existing = _first_transfer(base_url, user_headers, status="Scheduled")
    headers = _get_headers(user_headers, method="put")

    response = requests.put(
        _url(base_url, f"/{existing['id']}/commit"), headers=headers
    )
    assert response.status_code == 200

    get_headers = _get_headers(user_headers)
    get_response = requests.get(
        _url(base_url, f"/{existing['id']}"), headers=get_headers
    )
    assert get_response.json()["transfer_status"] == "Processed"


def test_put_transfer_commit_moves_stock_between_locations(
    base_url, user_headers, preserve_data_files
):
    """
    Business rule from the checklist: committing a transfer should move
    stock from from_location_id to to_location_id and update inventory
    counts (including items/{id}/inventory) accordingly.
    """
    preserve_data_files("transfer.json", "transfer_item.json", "inventory.json")
    existing = _first_transfer(base_url, user_headers, status="Scheduled")
    assert existing["items"], "fixture transfer is expected to have items"
    item_id = existing["items"][0]["item_id"]
    amount = existing["items"][0]["amount"]

    inventory_headers = user_headers(resource="items", method="get", allowed=True)
    before = requests.get(
        f"{base_url}/api/v1/items/{item_id}/inventory", headers=inventory_headers
    ).json()
    dst_before = next(
        (x for x in before if x["location_id"] == existing["to_location_id"]), None
    )
    dst_on_hand_before = dst_before["quantity_on_hand"] if dst_before else 0

    headers = _get_headers(user_headers, method="put")
    response = requests.put(
        _url(base_url, f"/{existing['id']}/commit"), headers=headers
    )
    assert response.status_code == 200

    after = requests.get(
        f"{base_url}/api/v1/items/{item_id}/inventory", headers=inventory_headers
    ).json()
    dst_after = next(
        x for x in after if x["location_id"] == existing["to_location_id"]
    )
    assert dst_after["quantity_on_hand"] == dst_on_hand_before + amount


@pytest.mark.xfail(
    strict=True,
    reason=(
        "The commit handler pops 'items' off the in-memory transfer dict "
        "before saving, but never removes the rows from the TransferItems "
        "pool itself, and get_transfer() always re-derives 'items' from "
        "that pool. A second commit on an already-Processed transfer "
        "therefore reprocesses the same items a second time, applying the "
        "stock movement twice instead of being rejected or being a no-op. "
        "Actual: 200, and quantity_on_hand at the destination is "
        "double-counted. Expected: the second commit should be rejected "
        "(e.g. 409/400 for an invalid state transition)."
    ),
)
def test_put_transfer_commit_on_already_processed_transfer_is_rejected(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("transfer.json", "transfer_item.json", "inventory.json")
    existing = _first_transfer(base_url, user_headers, status="Scheduled")
    headers = _get_headers(user_headers, method="put")

    first = requests.put(
        _url(base_url, f"/{existing['id']}/commit"), headers=headers
    )
    assert first.status_code == 200

    second = requests.put(
        _url(base_url, f"/{existing['id']}/commit"), headers=headers
    )
    assert second.status_code in (400, 409)


def test_put_transfer_commit_on_already_processed_transfer_double_counts_stock(
    base_url, user_headers, preserve_data_files
):
    """Pins the *actual* (buggy) behavior described above."""
    preserve_data_files("transfer.json", "transfer_item.json", "inventory.json")
    existing = _first_transfer(base_url, user_headers, status="Scheduled")
    item_id = existing["items"][0]["item_id"]
    amount = existing["items"][0]["amount"]
    headers = _get_headers(user_headers, method="put")

    requests.put(_url(base_url, f"/{existing['id']}/commit"), headers=headers)
    second = requests.put(
        _url(base_url, f"/{existing['id']}/commit"), headers=headers
    )
    assert second.status_code == 200

    inventory_headers = user_headers(resource="items", method="get", allowed=True)
    after = requests.get(
        f"{base_url}/api/v1/items/{item_id}/inventory", headers=inventory_headers
    ).json()
    dst_after = next(
        x for x in after if x["location_id"] == existing["to_location_id"]
    )
    assert dst_after["quantity_on_hand"] == 2 * amount


@pytest.mark.xfail(
    strict=True,
    reason=(
        "get_transfer() returns None for an unknown id and the commit "
        "handler immediately does transfer['from_location_id'] on it with "
        "no None-check, raising an uncaught TypeError caught only by the "
        "generic 500 handler. Actual: 500. Expected: 404."
    ),
)
def test_put_transfer_commit_nonexistent_transfer_returns_404(
    base_url, user_headers
):
    headers = _get_headers(user_headers, method="put")

    response = requests.put(
        _url(base_url, f"/999999/commit"), headers=headers
    )

    assert response.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Same unguarded int(paths[1]) as the other by-id routes. Actual: "
        "500. Expected: 400."
    ),
)
def test_put_transfer_commit_malformed_id_returns_400(base_url, user_headers):
    headers = _get_headers(user_headers, method="put")

    response = requests.put(
        _url(base_url, f"/not-an-id/commit"), headers=headers
    )

    assert response.status_code == 400


def test_put_transfer_commit_requires_authentication(base_url):
    response = requests.put(_url(base_url, f"/1/commit"))

    assert response.status_code == 401


def test_put_transfer_commit_insufficient_permissions_returns_403(
    base_url, user_headers
):
    headers = _get_headers(user_headers, method="put", allowed=False)
    response = requests.put(_url(base_url, f"/1/commit"), headers=headers)

    assert response.status_code == 403


# endregion
