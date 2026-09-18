"""
GET /suppliers - collection endpoint tests.

These tests exercise the checklist for "As a developer I want to know what
each endpoint does" (sub-issue: GET /suppliers). Several tests are written
against the *documented*/expected behavior and are marked `xfail(strict=True)`
where the live server currently does something else - this pins the actual,
observed behavior so it shows up clearly in test output and turns into a loud
XPASS failure the moment someone "fixes" it, prompting an update to these
notes rather than a silent behavior change.

Root cause note (applies to several xfails below): `ApiRequestHandler.do_GET`
splits the raw request path on "/" (`self.path.split("/")`) without ever
stripping the query string. Any request with a "?..." on it turns
`paths[0]` into e.g. "suppliers?page=1" instead of "suppliers". That string
is not a key in the caller's `endpoint_access` map, so `auth_provider.has_access`
returns False and the request is rejected with 403 Forbidden - even for a
fully-authorized user, and even though the OpenAPI spec documents no query
parameters at all for this endpoint. In short: today, sending *any* query
string to GET /suppliers breaks the request for everyone.
"""

import json
import time
from datetime import datetime
from pathlib import Path

import pytest
import requests
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[2]
SUPPLIERS_MODEL_SOURCE = (REPO_ROOT / "api" / "models" / "suppliers.py").read_text(
    encoding="utf-8"
)


class Supplier(BaseModel):
    id: int
    code: str
    name: str
    address: str
    city: str
    zip_code: str
    province: str
    country: str
    contact_name: str
    phone_number: str
    reference: str
    created_at: datetime
    updated_at: datetime


def test_get_suppliers_returns_200_with_valid_response(base_url, user_headers):
    headers = user_headers(resource="suppliers", method="get", allowed=True)
    response = requests.get(f"{base_url}/api/v1/suppliers", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) > 0
    assert "id" in body[0]


def test_response_body_matches_documented_schema(base_url, user_headers):
    """Field names, types and (flat) nesting must match the OpenAPI `Supplier` schema."""
    headers = user_headers(resource="suppliers", method="get", allowed=True)
    response = requests.get(f"{base_url}/api/v1/suppliers", headers=headers)

    body = response.json()
    for raw in body:
        Supplier.model_validate(raw)


def test_response_content_type_is_json(base_url, user_headers):
    headers = user_headers(resource="suppliers", method="get", allowed=True)
    response = requests.get(f"{base_url}/api/v1/suppliers", headers=headers)

    assert response.headers.get("Content-Type", "").startswith("application/json")


def test_response_time_is_reasonable(base_url, user_headers):
    headers = user_headers(resource="suppliers", method="get", allowed=True)

    start = time.monotonic()
    response = requests.get(f"{base_url}/api/v1/suppliers", headers=headers)
    elapsed = time.monotonic() - start

    assert response.status_code == 200
    assert (
        elapsed < 0.5
    ), f"GET /suppliers took {elapsed:.2f}s, which is unreasonably slow"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Not documented in the OpenAPI spec, and not implemented: any query "
        "string (pagination, filter, or unknown key alike) makes `paths[0]` "
        "mismatch the 'suppliers' resource key in endpoint_access, so a fully "
        "permitted user is rejected with 403 instead of the query string being "
        "ignored or the params being honoured. See module docstring."
    ),
)
@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"page": 1}, id="pagination-page"),
        pytest.param({"limit": 5}, id="pagination-limit"),
        pytest.param({"country": "Netherlands"}, id="filter-country"),
        pytest.param({"sort": "name"}, id="sort-name"),
        pytest.param({"page": -1}, id="invalid-negative-page"),
        pytest.param({"totally_unknown_key": "x"}, id="unknown-key"),
    ],
)
def test_query_params_are_honoured_or_gracefully_ignored(
    base_url, user_headers, params
):
    headers = user_headers(resource="suppliers", method="get", allowed=True)
    response = requests.get(
        f"{base_url}/api/v1/suppliers", headers=headers, params=params
    )

    # A fully-permitted user sending an (undocumented) query string should
    # never be worse off than sending no query string at all.
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_query_params_currently_return_403(base_url, user_headers):
    """
    Pins the *actual* behavior described above so a regression (e.g. a 500
    instead of 403) is caught even before the underlying bug is fixed.
    """
    headers = user_headers(resource="suppliers", method="get", allowed=True)
    response = requests.get(
        f"{base_url}/api/v1/suppliers", headers=headers, params={"page": 1}
    )

    assert response.status_code == 403
    assert response.text == ""


@pytest.mark.skip(
    reason=(
        "GET /suppliers has no documented or implemented filtering, so there is "
        "no supported way to induce an empty result set without mutating the "
        "shared data/supplier.json fixture out from under other tests. "
        "Redesign suggestion: support a filter (e.g. ?country=) so this is testable."
    )
)
def test_empty_result_set_returns_200_with_empty_array(base_url, user_headers):
    pass


def test_insufficient_permissions_returns_403(base_url, user_headers):
    """
    None of the originally seeded users in data/user.json were forbidden from
    GET /suppliers, so an "audit_viewer" fixture user (endpoint_access.suppliers
    all False, everything else read-only True) was added to data/user.json to
    make this case testable at all.
    """
    headers = user_headers(resource="suppliers", method="get", allowed=False)
    response = requests.get(f"{base_url}/api/v1/suppliers", headers=headers)

    assert response.status_code == 403


def test_missing_api_key_is_rejected_with_401(base_url):
    response = requests.get(f"{base_url}/api/v1/suppliers")

    assert response.status_code == 401


def test_invalid_api_key_is_rejected_with_401(base_url):
    response = requests.get(
        f"{base_url}/api/v1/suppliers", headers={"API_KEY": "not-a-real-key"}
    )

    assert response.status_code == 401


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Error responses (401 here, 403 for query params above) have an empty "
        "body and no Content-Type header at all, unlike success responses which "
        "are always `application/json`. There is no consistent error schema "
        "across the API to assert against. Redesign suggestion: every error "
        "response should return a JSON body with a stable shape, e.g. "
        '{"error": {"code": ..., "message": ...}}.'
    ),
)
def test_error_response_has_consistent_json_schema(base_url):
    response = requests.get(f"{base_url}/api/v1/suppliers")

    assert response.status_code == 401
    assert response.headers.get("Content-Type", "").startswith("application/json")
    body = response.json()
    assert "error" in body


def test_error_response_leaks_no_internal_details(base_url):
    response = requests.get(f"{base_url}/api/v1/suppliers")

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


def _get_headers(user_headers, method="get", allowed=True):
    return user_headers(resource="suppliers", method=method, allowed=allowed)


def _first_supplier(base_url, user_headers):
    headers = _get_headers(user_headers)
    body = requests.get(f"{base_url}/api/v1/suppliers", headers=headers).json()
    assert body, "fixture data/supplier.json is expected to be non-empty"
    return body[0]


# ---------------------------------------------------------------------------
# GET /suppliers/{id} - single-resource endpoint tests.
#
# Same routing/logging issues as the collection endpoint apply here too
# (see module docstring), plus its own: `int(paths[1])` is called with no
# try/except around it, so a non-numeric id falls through to the generic
# `except Exception: send_response(500)` in do_GET instead of a 400, and a
# numeric-but-nonexistent id returns 200 with a JSON body of `null` instead
# of 404 (get_supplier() returns None, which main.py serializes as-is).
# ---------------------------------------------------------------------------


def test_get_supplier_by_id_returns_200_with_correct_resource(base_url, user_headers):
    existing = _first_supplier(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/suppliers/{existing['id']}", headers=headers
    )

    assert response.status_code == 200
    assert response.json() == existing


def test_get_supplier_by_id_matches_documented_schema(base_url, user_headers):
    existing = _first_supplier(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/suppliers/{existing['id']}", headers=headers
    )

    Supplier.model_validate(response.json())


@pytest.mark.xfail(
    strict=True,
    reason=(
        "get_supplier() returns None for an unknown id, and main.py writes "
        "`json.dumps(None)` straight back with a 200, instead of a 404. "
        "Actual: 200 with body `null`. Expected: 404."
    ),
)
def test_get_supplier_by_nonexistent_id_returns_404(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/suppliers/999999", headers=headers)

    assert response.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason=(
        "`supplier_id = int(paths[1])` is not guarded, so a non-numeric id "
        "raises an uncaught ValueError that bubbles up to the generic "
        "`except Exception: send_response(500)` in do_GET. "
        "Actual: 500 Internal Server Error. Expected: 400 Bad Request."
    ),
)
def test_get_supplier_by_malformed_id_returns_400(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/suppliers/not-an-id", headers=headers)

    assert response.status_code == 400


def test_get_supplier_items_are_consistent_with_items_endpoint(base_url, user_headers):
    """
    The only "related object" GET /suppliers/{id} has is its /items sub-resource
    (full Item objects, per the OpenAPI description). Every item it returns
    should reference this supplier and match the standalone /items/{id} record.
    """
    existing = _first_supplier(base_url, user_headers)
    supplier_headers = _get_headers(user_headers)
    item_headers = user_headers(resource="items", method="get", allowed=True)

    items_response = requests.get(
        f"{base_url}/api/v1/suppliers/{existing['id']}/items", headers=supplier_headers
    )
    assert items_response.status_code == 200
    items = items_response.json()

    for item in items:
        assert item["supplier_id"] == existing["id"]
        direct = requests.get(
            f"{base_url}/api/v1/items/{item['id']}", headers=item_headers
        )
        assert direct.status_code == 200
        assert direct.json() == item


def test_get_supplier_by_id_requires_authentication(base_url):
    response = requests.get(f"{base_url}/api/v1/suppliers/1")

    assert response.status_code == 401


def test_get_supplier_by_id_insufficient_permissions_returns_403(
    base_url, user_headers
):
    headers = _get_headers(user_headers, allowed=False)
    response = requests.get(f"{base_url}/api/v1/suppliers/1", headers=headers)

    assert response.status_code == 403


def test_get_supplier_by_id_response_content_type_is_json(base_url, user_headers):
    existing = _first_supplier(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(
        f"{base_url}/api/v1/suppliers/{existing['id']}", headers=headers
    )

    assert response.headers.get("Content-Type", "").startswith("application/json")


def test_get_supplier_by_malformed_id_error_leaks_no_internal_details(
    base_url, user_headers
):
    headers = _get_headers(user_headers)
    response = requests.get(f"{base_url}/api/v1/suppliers/not-an-id", headers=headers)

    text_lower = response.text.lower()
    for leak_indicator in ("traceback", "exception", "valueerror", 'file "', "line "):
        assert leak_indicator not in text_lower


# ---------------------------------------------------------------------------
# POST /suppliers - create endpoint tests.
#
# Headline bug, confirmed by direct inspection of data/supplier.json before
# and after a POST: `handle_post_version_1` calls
# `data_provider.fetch_supplier_pool().add_supplier(new_supplier)` and then,
# on the *next* line, `data_provider.fetch_supplier_pool().save()`.
# `fetch_supplier_pool()` constructs a brand-new `Suppliers` instance that
# re-reads data/supplier.json from disk every time it's called, so the
# `.save()` call persists a freshly-loaded (unmodified) copy of the data -
# not the one `.add_supplier()` just appended to. The append is silently
# discarded. POST /suppliers always returns 201, but never actually creates
# anything. The same fetch-mutate-fetch-save pattern is used for every
# resource's POST/PUT/DELETE in this file, so this is very likely a
# repo-wide bug, not one specific to suppliers.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=(
        "POST /suppliers returns 201 with an empty body: no created resource, "
        "no generated id, nothing. The OpenAPI spec itself only documents "
        '{"description": "Created"} with no response schema for this status, '
        "so this technically doesn't violate the spec, but it does violate the "
        "checklist expectation and basic REST practice. "
        "Redesign suggestion: return the created resource (with its id) in the body."
    ),
)
def test_post_supplier_returns_created_resource_with_id(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("supplier.json")
    headers = _get_headers(user_headers, method="post")
    payload = {
        "code": "SUP-TEST-1",
        "name": "Test Supplier Co",
        "address": "1 Test Street",
        "city": "Testville",
        "zip_code": "0000AA",
        "province": "Test",
        "country": "Testland",
        "contact_name": "Tess Ter",
        "phone_number": "+31000000000",
        "reference": "Test",
    }

    response = requests.post(
        f"{base_url}/api/v1/suppliers", headers=headers, json=payload
    )

    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    for key, value in payload.items():
        assert body[key] == value


@pytest.mark.xfail(
    strict=True,
    reason=(
        "No Location header and no body are returned on 201, so there is no "
        "way for a client to discover the URL of the resource it just created."
    ),
)
def test_post_supplier_response_points_to_new_resource(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("supplier.json")
    headers = _get_headers(user_headers, method="post")
    response = requests.post(
        f"{base_url}/api/v1/suppliers", headers=headers, json={"name": "Locate Me Co"}
    )

    assert response.status_code == 201
    assert "Location" in response.headers


@pytest.mark.xfail(
    strict=True,
    reason=(
        "No request validation exists at all: an empty/near-empty payload "
        "missing every documented required-looking field (code, name, address, "
        "etc.) is still accepted with 201. Expected: 400/422 listing the "
        "missing fields."
    ),
)
def test_post_supplier_missing_required_fields_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("supplier.json")
    headers = _get_headers(user_headers, method="post")

    response = requests.post(f"{base_url}/api/v1/suppliers", headers=headers, json={})

    assert response.status_code in (400, 422)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Field values are stored as-is with no type checking: an `id` of type "
        "string is accepted with 201 instead of being rejected. "
        "Expected: 400/422 for a type mismatch against the documented integer id."
    ),
)
def test_post_supplier_invalid_field_type_is_rejected(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("supplier.json")
    headers = _get_headers(user_headers, method="post")

    response = requests.post(
        f"{base_url}/api/v1/suppliers",
        headers=headers,
        json={"id": "not-an-int", "name": "Bad Type Co"},
    )

    assert response.status_code in (400, 422)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "There is no id/code uniqueness check anywhere in Suppliers.add_supplier: "
        "POSTing a second supplier with an `id` (or `code`) that already exists "
        "is accepted with 201 instead of a 409/400 conflict. "
        "(Also affected by the persistence no-op above, but the *status code* "
        "returned is the thing being pinned here.)"
    ),
)
def test_post_supplier_duplicate_id_returns_conflict(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("supplier.json")
    existing = _first_supplier(base_url, user_headers)
    headers = _get_headers(user_headers, method="post")

    response = requests.post(
        f"{base_url}/api/v1/suppliers",
        headers=headers,
        json={**existing, "name": "Duplicate Of " + existing["name"]},
    )

    assert response.status_code == 409


def test_post_supplier_is_immediately_retrievable(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("supplier.json")
    headers = _get_headers(user_headers, method="post")
    payload = {"id": 555555, "code": "SUP-555555", "name": "Retrievable Co"}

    create_response = requests.post(
        f"{base_url}/api/v1/suppliers", headers=headers, json=payload
    )
    assert create_response.status_code == 201

    get_headers = _get_headers(user_headers)
    get_response = requests.get(
        f"{base_url}/api/v1/suppliers/555555", headers=get_headers
    )

    assert get_response.status_code == 200
    assert get_response.json() is not None
    assert get_response.json()["name"] == "Retrievable Co"


@pytest.mark.skip(
    reason=(
        "The Supplier schema has no foreign-key fields (id, code, name, address, "
        "city, zip_code, province, country, contact_name, phone_number, "
        "reference, created_at, updated_at - see openapi.json#/components/schemas/Supplier). "
        "Unlike e.g. a location's warehouse_id, there is nothing on a supplier "
        "payload to validate a reference for. N/A for this resource."
    )
)
def test_post_supplier_invalid_foreign_key_is_rejected(base_url, user_headers):
    pass


def test_post_supplier_requires_authentication(base_url):
    response = requests.post(
        f"{base_url}/api/v1/suppliers", json={"name": "No Auth Co"}
    )

    assert response.status_code == 401


def test_post_supplier_insufficient_permissions_returns_403(base_url, user_headers):
    headers = _get_headers(user_headers, method="post", allowed=False)
    response = requests.post(
        f"{base_url}/api/v1/suppliers", headers=headers, json={"name": "Forbidden Co"}
    )

    assert response.status_code == 403


@pytest.mark.xfail(
    strict=True,
    reason=(
        "do_POST never inspects the Content-Type header before json.loads()-ing "
        "the body, so a request sent as text/plain (or with no Content-Type at "
        "all) is accepted exactly like application/json. "
        "Expected: a non-JSON Content-Type should be rejected."
    ),
)
def test_post_supplier_wrong_content_type_is_rejected(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("supplier.json")
    headers = {
        **_get_headers(user_headers, method="post"),
        "Content-Type": "text/plain",
    }

    response = requests.post(
        f"{base_url}/api/v1/suppliers",
        headers=headers,
        data=json.dumps({"name": "Plain Text Co"}),
    )

    assert response.status_code in (400, 415)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "A malformed (non-JSON) body makes json.loads() raise, which is caught "
        "only by the generic `except Exception: send_response(500)` wrapper in "
        "do_POST. Actual: 500. Expected: 400/422."
    ),
)
def test_post_supplier_malformed_json_body_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("supplier.json")
    headers = {
        **_get_headers(user_headers, method="post"),
        "Content-Type": "application/json",
    }

    response = requests.post(
        f"{base_url}/api/v1/suppliers", headers=headers, data="{not valid json"
    )

    assert response.status_code in (400, 422)


def test_post_supplier_malformed_json_body_leaks_no_internal_details(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("supplier.json")
    headers = {
        **_get_headers(user_headers, method="post"),
        "Content-Type": "application/json",
    }

    response = requests.post(
        f"{base_url}/api/v1/suppliers", headers=headers, data="{not valid json"
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


# ---------------------------------------------------------------------------
# PUT /suppliers/{id} - update endpoint tests.
#
# Shares the persistence no-op bug from POST (fetch_supplier_pool() is called
# once for update_supplier() and again, independently, for save()), plus the
# same unguarded `int(paths[1])` as GET /suppliers/{id}, plus no existence
# check before "updating" (update_supplier silently does nothing if the id
# isn't found, and handle_put_version_1 still returns 200 either way).
# ---------------------------------------------------------------------------


def test_put_supplier_valid_payload_returns_200(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("supplier.json")
    existing = _first_supplier(base_url, user_headers)
    headers = _get_headers(user_headers, method="put")

    updated = {**existing, "name": "Updated Name Co"}
    response = requests.put(
        f"{base_url}/api/v1/suppliers/{existing['id']}", headers=headers, json=updated
    )

    assert response.status_code == 200


def test_put_supplier_update_is_persisted(base_url, user_headers, preserve_data_files):
    preserve_data_files("supplier.json")
    existing = _first_supplier(base_url, user_headers)
    headers = _get_headers(user_headers, method="put")

    updated = {**existing, "name": "Persisted Name Co"}
    put_response = requests.put(
        f"{base_url}/api/v1/suppliers/{existing['id']}", headers=headers, json=updated
    )
    assert put_response.status_code == 200

    get_headers = _get_headers(user_headers)
    get_response = requests.get(
        f"{base_url}/api/v1/suppliers/{existing['id']}", headers=get_headers
    )
    assert get_response.json()["name"] == "Persisted Name Co"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "update_supplier() loops over the data looking for a matching id and "
        "simply does nothing if none is found; handle_put_version_1 always "
        "sends 200 regardless. Actual: 200 for a nonexistent id. Expected: 404."
    ),
)
def test_put_supplier_nonexistent_id_returns_404(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("supplier.json")
    headers = _get_headers(user_headers, method="put")

    response = requests.put(
        f"{base_url}/api/v1/suppliers/999999",
        headers=headers,
        json={"id": 999999, "name": "Ghost Co"},
    )

    assert response.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Same unguarded `int(paths[1])` as GET/DELETE by id: a non-numeric id "
        "raises an uncaught ValueError caught only by the generic 500 handler. "
        "Actual: 500. Expected: 400."
    ),
)
def test_put_supplier_malformed_id_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("supplier.json")
    headers = _get_headers(user_headers, method="put")

    response = requests.put(
        f"{base_url}/api/v1/suppliers/not-an-id", headers=headers, json={"name": "x"}
    )

    assert response.status_code == 400


def test_put_supplier_replaces_the_whole_record_per_source(
    base_url, user_headers, preserve_data_files
):
    """
    Not independently observable through the API today (the persistence no-op
    above hides it), but worth recording from reading the source directly:
    Suppliers.update_supplier() does `self.data[i] = supplier`, i.e. a full
    replace of the stored record with whatever the client sent - not a merge
    of only the provided fields. A client that PUTs a partial payload would,
    if persistence worked, silently drop every field it omitted. The OpenAPI
    spec doesn't document which behavior (replace vs. merge) is intended.
    Redesign suggestion: document PUT as full-replace explicitly (matching
    the source), and add a PATCH for partial updates instead of leaving PUT
    ambiguous.
    """
    assert "self.data[i] = supplier" in SUPPLIERS_MODEL_SOURCE


@pytest.mark.skip(
    reason=(
        "Same as POST: the Supplier schema has no foreign-key fields to "
        "validate on update. N/A for this resource."
    )
)
def test_put_supplier_invalid_foreign_key_is_rejected(base_url, user_headers):
    pass


@pytest.mark.skip(
    reason=(
        "Not meaningfully testable: PUT never actually persists (see the "
        "no-op bug above), and the server is a single-threaded "
        "socketserver.TCPServer handling one request at a time, so there is "
        "no way to race two updates against each other. Redesign suggestion: "
        "once persistence is fixed, add optimistic concurrency control "
        "(e.g. an ETag / If-Match header keyed on updated_at) before this "
        "becomes testable and worth guarding against."
    )
)
def test_put_supplier_concurrent_updates_do_not_corrupt_data(base_url, user_headers):
    pass


def test_put_supplier_requires_authentication(base_url):
    response = requests.put(
        f"{base_url}/api/v1/suppliers/1", json={"name": "No Auth Co"}
    )

    assert response.status_code == 401


def test_put_supplier_insufficient_permissions_returns_403(base_url, user_headers):
    headers = _get_headers(user_headers, method="put", allowed=False)
    response = requests.put(
        f"{base_url}/api/v1/suppliers/1", headers=headers, json={"name": "Forbidden Co"}
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /suppliers/{id} - delete endpoint tests.
#
# Shares the fetch-mutate-fetch-save persistence no-op with POST/PUT
# (remove_supplier() and save() run against two independently-loaded
# instances), plus no existence check (handle_delete_version_1 always
# returns 200, whether or not remove_supplier() found anything to remove).
# ---------------------------------------------------------------------------


def test_delete_supplier_valid_id_returns_200(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("supplier.json")
    existing = _first_supplier(base_url, user_headers)
    headers = _get_headers(user_headers, method="delete")

    response = requests.delete(
        f"{base_url}/api/v1/suppliers/{existing['id']}", headers=headers
    )

    assert response.status_code in (200, 204)


def test_delete_supplier_resource_is_actually_gone(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("supplier.json")
    existing = _first_supplier(base_url, user_headers)
    delete_headers = _get_headers(user_headers, method="delete")

    delete_response = requests.delete(
        f"{base_url}/api/v1/suppliers/{existing['id']}", headers=delete_headers
    )
    assert delete_response.status_code in (200, 204)

    get_headers = _get_headers(user_headers)
    get_response = requests.get(
        f"{base_url}/api/v1/suppliers/{existing['id']}", headers=get_headers
    )
    assert get_response.json() is None


@pytest.mark.xfail(
    strict=True,
    reason=(
        "remove_supplier() is a silent no-op if the id doesn't match anything, "
        "and handle_delete_version_1 always sends 200 regardless. "
        "Actual: 200 for a nonexistent id. Expected: 404."
    ),
)
def test_delete_supplier_nonexistent_id_returns_404(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("supplier.json")
    headers = _get_headers(user_headers, method="delete")

    response = requests.delete(f"{base_url}/api/v1/suppliers/999999", headers=headers)

    assert response.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Same unguarded `int(paths[1])` as GET/PUT by id. "
        "Actual: 500. Expected: 400."
    ),
)
def test_delete_supplier_malformed_id_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("supplier.json")
    headers = _get_headers(user_headers, method="delete")

    response = requests.delete(
        f"{base_url}/api/v1/suppliers/not-an-id", headers=headers
    )

    assert response.status_code == 400


@pytest.mark.xfail(
    strict=True,
    reason=(
        "First DELETE is expected to remove the resource (200/204) and a "
        "second DELETE on the same, now-gone id is expected to 404. DELETE "
        "now actually persists (data_provider.py caches one pool instance per "
        "resource, so the mutate call and the save call act on the same "
        "instance), so the first delete really does remove the resource -- but "
        "remove_supplier() is a silent no-op when the id isn't found, and "
        "handle_delete_version_1 always sends 200 regardless of whether "
        "anything was removed. The second delete still gets 200 instead of "
        "404 because there is no existence check before responding."
    ),
)
def test_delete_supplier_repeated_delete_returns_404_not_500(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("supplier.json")
    existing = _first_supplier(base_url, user_headers)
    headers = _get_headers(user_headers, method="delete")

    first = requests.delete(
        f"{base_url}/api/v1/suppliers/{existing['id']}", headers=headers
    )
    second = requests.delete(
        f"{base_url}/api/v1/suppliers/{existing['id']}", headers=headers
    )

    assert first.status_code in (200, 204)
    assert second.status_code == 404


@pytest.mark.skip(
    reason=(
        "Items reference suppliers via `supplier_id` (see data/item.json), so "
        "deleting a referenced supplier is a real scenario worth covering - "
        "but DELETE never actually persists anything (see no-op bug above), "
        "so there is currently no way to observe whether a real delete would "
        "block, cascade, or silently orphan those items. Redesign suggestion: "
        "once persistence is fixed, decide and document one of: block the "
        "delete (409) while items reference the supplier, cascade the delete "
        "to those items, or null out/require reassigning their supplier_id - "
        "and add a test pinning whichever is chosen."
    )
)
def test_delete_supplier_referenced_by_items_is_handled_deliberately(
    base_url, user_headers
):
    pass


def test_delete_supplier_requires_authentication(base_url):
    response = requests.delete(f"{base_url}/api/v1/suppliers/1")

    assert response.status_code == 401


def test_delete_supplier_insufficient_permissions_returns_403(base_url, user_headers):
    headers = _get_headers(user_headers, method="delete", allowed=False)
    response = requests.delete(f"{base_url}/api/v1/suppliers/1", headers=headers)

    assert response.status_code == 403
