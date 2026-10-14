"""
/item_groups endpoint tests: GET (collection), GET /{id}, POST, PUT /{id},
DELETE /{id}, GET /{id}/items.

These tests exercise the checklist for "As a developer I want to know what
each endpoint does" (sub-issues: GET /item_groups, POST /item_groups,
GET /item_groups/{id}, PUT /item_groups/{id}, DELETE /item_groups/{id},
GET /item_groups/{id}/items). Several tests are written against the
*documented*/expected behavior and are marked `xfail(strict=True)` where the
live server currently does something else. This pins the actual, observed
behavior so it shows up clearly in test output and turns into a loud XPASS
failure the moment someone "fixes" it, prompting an update to these notes
rather than a silent behavior change.

The file is split into `# region` blocks below, one per endpoint, plus a
shared-helpers region at the top, collapse/expand them in an editor that
supports region folding to jump straight to one endpoint's tests.

Root cause notes shared across the whole resource (identical in shape to
`/suppliers`, see test_suppliers.py):

* `ApiRequestHandler.do_GET` splits the raw request path on "/" without
  ever stripping the query string. Any request with a "?..." on it turns
  `paths[0]` into e.g. "item_groups?page=1" instead of "item_groups",
  which is not a key in `endpoint_access`, so a fully-authorized user is
  rejected with 403 instead of the query string being honoured or ignored.
* `item_group_id = int(paths[1])` (GET/PUT/DELETE by id, and the nested
  `/items` route) is never guarded, so a non-numeric id raises an uncaught
  `ValueError` caught only by the generic `except Exception:
  send_response(500)` wrapper in each verb's handler. Actual: 500.
  Expected: 400.
* `ItemGroups.get_item_group()` returns `None` for an unknown id with no
  existence check, and `main.py` serializes that straight back with a 200.
  A single-resource GET for an unknown id is therefore 200 with body
  `null` instead of 404.
* `ItemGroups.update_item_group()`/`remove_item_group()` are silent no-ops
  when the id doesn't match anything, and their handlers always respond
  200 regardless of whether anything actually changed.

Notable inconsistency (GET /item_groups/{id}/items region):
`Items.get_items_for_item_group()` returns a bare list of item **ids**
(`[2, 3, 4, ...]`), unlike `Items.get_items_for_supplier()` which returns
full item objects for `GET /suppliers/{id}/items`. Two structurally
identical "nested relationship GET" endpoints on the same API return
completely different shapes for the same kind of relationship.
"""

import json
import time
from pathlib import Path

import pytest
import requests

from schemas import ItemGroup

REPO_ROOT = Path(__file__).resolve().parents[2]
ITEM_GROUPS_MODEL_SOURCE = (
    REPO_ROOT / "api" / "models" / "item_groups.py"
).read_text(encoding="utf-8")


# region Shared helpers
def _url(base_url, path=""):
    return f"{base_url}/api/v1/item_groups{path}"


def _get_headers(user_headers, method="get", allowed=True):
    return user_headers(resource="item_groups", method=method, allowed=allowed)


def _first_item_group(base_url, user_headers):
    headers = _get_headers(user_headers)
    body = requests.get(_url(base_url), headers=headers).json()
    assert body, "fixture data/item_group.json is expected to be non-empty"
    return body[0]


# endregion


# region GET /item_groups (collection)
def test_get_item_groups_returns_200_with_valid_response(base_url, user_headers):
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
        ItemGroup.model_validate(raw)


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
    ), f"GET /item_groups took {elapsed:.2f}s, which is unreasonably slow"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "do_GET splits the raw request path on '/' without ever stripping "
        "the query string. Any request with a '?...' on it turns paths[0] "
        "into e.g. 'item_groups?page=1' instead of 'item_groups', which is "
        "not a key in endpoint_access, so a fully-authorized user is "
        "rejected with 403 instead of the query string being honoured or "
        "ignored."
    ),
)
@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"page": 1}, id="pagination-page"),
        pytest.param({"limit": 5}, id="pagination-limit"),
        pytest.param({"name": "Vers"}, id="filter-name"),
        pytest.param({"sort": "name"}, id="sort-name"),
        pytest.param({"page": -1}, id="invalid-negative-page"),
        pytest.param({"totally_unknown_key": "x"}, id="unknown-key"),
    ],
)
def test_query_params_are_honoured_or_gracefully_ignored(
    base_url, user_headers, params
):
    headers = _get_headers(user_headers)
    response = requests.get(_url(base_url), headers=headers, params=params)

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_query_params_currently_return_403(base_url, user_headers):
    """Pins the *actual* behavior described above."""
    headers = _get_headers(user_headers)
    response = requests.get(_url(base_url), headers=headers, params={"page": 1})

    assert response.status_code == 403
    assert response.text == ""


@pytest.mark.skip(
    reason=(
        "GET /item_groups has no implemented filtering, so there is no "
        "supported way to induce an empty result set without mutating the "
        "shared data/item_group.json fixture out from under other tests. "
        "Redesign suggestion: support a filter (e.g. ?name=) so this is "
        "testable."
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
    response = requests.get(_url(base_url), headers={"API_KEY": "not-a-real-key"})

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
    response = requests.get(f"{base_url}/api/v1/item_groups")

    assert response.status_code == 401
    assert response.headers.get("Content-Type", "").startswith("application/json")
    body = response.json()
    assert "error" in body


def test_error_response_leaks_no_internal_details(base_url):
    response = requests.get(f"{base_url}/api/v1/item_groups")

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


# region GET /item_groups/{id}


def test_get_item_group_by_id_returns_200_with_correct_resource(
    base_url, user_headers
):
    existing = _first_item_group(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(_url(base_url, f"/{existing['id']}"), headers=headers)

    assert response.status_code == 200
    assert response.json() == existing


def test_get_item_group_by_id_matches_documented_schema(base_url, user_headers):
    existing = _first_item_group(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(_url(base_url, f"/{existing['id']}"), headers=headers)

    ItemGroup.model_validate(response.json())


@pytest.mark.xfail(
    strict=True,
    reason=(
        "get_item_group() returns None for an unknown id, and main.py "
        "writes json.dumps(None) straight back with a 200, instead of a "
        "404. Actual: 200 with body `null`. Expected: 404."
    ),
)
def test_get_item_group_by_nonexistent_id_returns_404(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(_url(base_url, "/999999"), headers=headers)

    assert response.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason=(
        "item_group_id = int(paths[1]) is not guarded, so a non-numeric id "
        "raises an uncaught ValueError that bubbles up to the generic "
        "except Exception: send_response(500) in do_GET. "
        "Actual: 500 Internal Server Error. Expected: 400 Bad Request."
    ),
)
def test_get_item_group_by_malformed_id_returns_400(base_url, user_headers):
    headers = _get_headers(user_headers)
    response = requests.get(_url(base_url, "/not-an-id"), headers=headers)

    assert response.status_code == 400


def test_get_item_group_by_id_requires_authentication(base_url):
    response = requests.get(_url(base_url, "/1"))

    assert response.status_code == 401


def test_get_item_group_by_id_insufficient_permissions_returns_403(
    base_url, user_headers
):
    headers = _get_headers(user_headers, allowed=False)
    response = requests.get(_url(base_url, "/1"), headers=headers)

    assert response.status_code == 403


def test_get_item_group_by_id_response_content_type_is_json(base_url, user_headers):
    existing = _first_item_group(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(_url(base_url, f"/{existing['id']}"), headers=headers)

    assert response.headers.get("Content-Type", "").startswith("application/json")


def test_get_item_group_by_malformed_id_error_leaks_no_internal_details(
    base_url, user_headers
):
    headers = _get_headers(user_headers)
    response = requests.get(_url(base_url, "/not-an-id"), headers=headers)

    text_lower = response.text.lower()
    for leak_indicator in ("traceback", "exception", "valueerror", 'file "', "line "):
        assert leak_indicator not in text_lower


# endregion


# region POST /item_groups


@pytest.mark.xfail(
    strict=True,
    reason=(
        "POST /item_groups returns 201 with an empty body: no created "
        "resource, no generated id, nothing. Redesign suggestion: return "
        "the created resource (with its id) in the body."
    ),
)
def test_post_item_group_returns_created_resource_with_id(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    headers = _get_headers(user_headers, method="post")
    payload = {"name": "Test Group", "description": "A group for testing"}

    response = requests.post(_url(base_url), headers=headers, json=payload)

    assert response.status_code == 201
    body = response.json()
    assert "id" in body
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
def test_post_item_group_response_points_to_new_resource(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    headers = _get_headers(user_headers, method="post")
    response = requests.post(
        _url(base_url), headers=headers, json={"name": "Locate Me Group"}
    )

    assert response.status_code == 201
    assert "Location" in response.headers


@pytest.mark.xfail(
    strict=True,
    reason=(
        "No request validation exists at all: an empty/near-empty payload "
        "missing every documented required-looking field (name, "
        "description) is still accepted with 201. Expected: 400/422 "
        "listing the missing fields."
    ),
)
def test_post_item_group_missing_required_fields_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    headers = _get_headers(user_headers, method="post")

    response = requests.post(_url(base_url), headers=headers, json={})

    assert response.status_code in (400, 422)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Field values are stored as-is with no type checking: an `id` of "
        "type string is accepted with 201 instead of being rejected. "
        "Expected: 400/422 for a type mismatch against the documented "
        "integer id."
    ),
)
def test_post_item_group_invalid_field_type_is_rejected(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    headers = _get_headers(user_headers, method="post")

    response = requests.post(
        _url(base_url),
        headers=headers,
        json={"id": "not-an-int", "name": "Bad Type Group"},
    )

    assert response.status_code in (400, 422)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "There is no id uniqueness check anywhere in "
        "ItemGroups.add_item_group: POSTing a second item group with an id "
        "that already exists is accepted with 201 instead of a 409/400 "
        "conflict."
    ),
)
def test_post_item_group_duplicate_id_returns_conflict(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    existing = _first_item_group(base_url, user_headers)
    headers = _get_headers(user_headers, method="post")

    response = requests.post(
        _url(base_url),
        headers=headers,
        json={**existing, "name": "Duplicate of " + existing["name"]},
    )

    assert response.status_code == 409


def test_post_item_group_is_immediately_retrievable(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    headers = _get_headers(user_headers, method="post")
    payload = {"id": 555555, "name": "Retrievable Group", "description": "x"}

    create_response = requests.post(_url(base_url), headers=headers, json=payload)
    assert create_response.status_code == 201

    get_headers = _get_headers(user_headers)
    get_response = requests.get(_url(base_url, "/555555"), headers=get_headers)

    assert get_response.status_code == 200
    assert get_response.json() is not None
    assert get_response.json()["name"] == "Retrievable Group"


def test_post_item_group_missing_id_breaks_lookups_for_unmatched_ids(
    base_url, user_headers, preserve_data_files
):
    """
    Documents a real, observed side effect of the validation gap above.
    add_item_group() does not require an `id` field, so a payload without
    one is accepted (201) and appended as-is. get_item_group() indexes
    x["id"] unconditionally while scanning for a match, so once that
    id-less row is the last one in the collection, any lookup for an id
    that ISN'T found (i.e. that has to scan all the way to the end) raises
    an uncaught KeyError -- a 500 -- instead of the usual 200/null. Lookups
    for ids that already exist earlier in the collection are unaffected,
    since get_item_group() returns as soon as it finds a match.
    """
    preserve_data_files("item_group.json")
    headers = _get_headers(user_headers, method="post")

    post_response = requests.post(_url(base_url), headers=headers, json={})
    assert post_response.status_code == 201

    get_headers = _get_headers(user_headers)

    existing_id_response = requests.get(_url(base_url, "/1"), headers=get_headers)
    assert existing_id_response.status_code == 200

    unmatched_id_response = requests.get(
        _url(base_url, "/999999"), headers=get_headers
    )
    assert unmatched_id_response.status_code == 500


@pytest.mark.skip(
    reason=(
        "The ItemGroup schema has no foreign-key fields (id, name, "
        "description, created_at, updated_at) to validate on creation. N/A "
        "for this resource."
    )
)
def test_post_item_group_invalid_foreign_key_is_rejected(base_url, user_headers):
    pass


def test_post_item_group_requires_authentication(base_url):
    response = requests.post(_url(base_url), json={"name": "No Auth Group"})

    assert response.status_code == 401


def test_post_item_group_insufficient_permissions_returns_403(base_url, user_headers):
    headers = _get_headers(user_headers, method="post", allowed=False)
    response = requests.post(
        _url(base_url), headers=headers, json={"name": "Forbidden Group"}
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
def test_post_item_group_wrong_content_type_is_rejected(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    headers = {
        **_get_headers(user_headers, method="post"),
        "Content-Type": "text/plain",
    }

    response = requests.post(
        _url(base_url), headers=headers, data=json.dumps({"name": "Plain Text Group"})
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
def test_post_item_group_malformed_json_body_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    headers = {
        **_get_headers(user_headers, method="post"),
        "Content-Type": "application/json",
    }

    response = requests.post(_url(base_url), headers=headers, data="{not valid json")

    assert response.status_code in (400, 422)


def test_post_item_group_malformed_json_body_leaks_no_internal_details(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    headers = {
        **_get_headers(user_headers, method="post"),
        "Content-Type": "application/json",
    }

    response = requests.post(_url(base_url), headers=headers, data="{not valid json")

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


# region PUT /item_groups/{id}


def test_put_item_group_valid_payload_returns_200(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    existing = _first_item_group(base_url, user_headers)
    headers = _get_headers(user_headers, method="put")

    updated = {**existing, "name": "Updated Name Group"}
    response = requests.put(
        _url(base_url, f"/{existing['id']}"), headers=headers, json=updated
    )

    assert response.status_code == 200


def test_put_item_group_update_is_persisted(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    existing = _first_item_group(base_url, user_headers)
    headers = _get_headers(user_headers, method="put")

    updated = {**existing, "name": "Persisted Name Group"}
    put_response = requests.put(
        _url(base_url, f"/{existing['id']}"), headers=headers, json=updated
    )
    assert put_response.status_code == 200

    get_headers = _get_headers(user_headers)
    get_response = requests.get(
        _url(base_url, f"/{existing['id']}"), headers=get_headers
    )
    assert get_response.json()["name"] == "Persisted Name Group"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "update_item_group() loops over the data looking for a matching id "
        "and simply does nothing if none is found; handle_put_version_1 "
        "always sends 200 regardless. Actual: 200 for a nonexistent id. "
        "Expected: 404."
    ),
)
def test_put_item_group_nonexistent_id_returns_404(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    headers = _get_headers(user_headers, method="put")

    response = requests.put(
        _url(base_url, "/999999"),
        headers=headers,
        json={"id": 999999, "name": "Ghost Group"},
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
def test_put_item_group_malformed_id_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    headers = _get_headers(user_headers, method="put")

    response = requests.put(
        _url(base_url, "/not-an-id"), headers=headers, json={"name": "x"}
    )

    assert response.status_code == 400


def test_put_item_group_replaces_the_whole_record_per_source():
    """
    Not independently observable through the API today, but worth
    recording from reading the source directly: ItemGroups.update_item_group()
    does `self.data[i] = item_group`, i.e. a full replace of the stored
    record with whatever the client sent. Not a merge of only the provided
    fields. A client that PUTs a partial payload would silently drop every
    field it omitted.
    """
    assert "self.data[i] = item_group" in ITEM_GROUPS_MODEL_SOURCE


@pytest.mark.skip(
    reason=(
        "Same as POST: the ItemGroup schema has no foreign-key fields to "
        "validate on update. N/A for this resource."
    )
)
def test_put_item_group_invalid_foreign_key_is_rejected(base_url, user_headers):
    pass


def test_put_item_group_requires_authentication(base_url):
    response = requests.put(_url(base_url, "/1"), json={"name": "No Auth Group"})

    assert response.status_code == 401


def test_put_item_group_insufficient_permissions_returns_403(base_url, user_headers):
    headers = _get_headers(user_headers, method="put", allowed=False)
    response = requests.put(
        _url(base_url, "/1"), headers=headers, json={"name": "Forbidden Group"}
    )

    assert response.status_code == 403


# endregion


# region DELETE /item_groups/{id}


def test_delete_item_group_valid_id_returns_200(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    existing = _first_item_group(base_url, user_headers)
    headers = _get_headers(user_headers, method="delete")

    response = requests.delete(_url(base_url, f"/{existing['id']}"), headers=headers)

    assert response.status_code in (200, 204)


def test_delete_item_group_resource_is_actually_gone(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    existing = _first_item_group(base_url, user_headers)
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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "remove_item_group() is a silent no-op if the id doesn't match "
        "anything, and handle_delete_version_1 always sends 200 regardless. "
        "Actual: 200 for a nonexistent id. Expected: 404."
    ),
)
def test_delete_item_group_nonexistent_id_returns_404(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    headers = _get_headers(user_headers, method="delete")

    response = requests.delete(_url(base_url, "/999999"), headers=headers)

    assert response.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Same unguarded int(paths[1]) as GET/PUT by id. Actual: 500. "
        "Expected: 400."
    ),
)
def test_delete_item_group_malformed_id_returns_400(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    headers = _get_headers(user_headers, method="delete")

    response = requests.delete(_url(base_url, "/not-an-id"), headers=headers)

    assert response.status_code == 400


@pytest.mark.xfail(
    strict=True,
    reason=(
        "First DELETE is expected to remove the resource (200/204) and a "
        "second DELETE on the same, now-gone id is expected to 404. "
        "remove_item_group() is a silent no-op when the id isn't found, "
        "and handle_delete_version_1 always sends 200 regardless of "
        "whether anything was removed. The second delete still gets 200 "
        "instead of 404 because there is no existence check before "
        "responding."
    ),
)
def test_delete_item_group_repeated_delete_returns_404_not_200(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    existing = _first_item_group(base_url, user_headers)
    headers = _get_headers(user_headers, method="delete")

    first = requests.delete(_url(base_url, f"/{existing['id']}"), headers=headers)
    second = requests.delete(_url(base_url, f"/{existing['id']}"), headers=headers)

    assert first.status_code in (200, 204)
    assert second.status_code == 404


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Deleting an item group that items still reference (via "
        "item_group_id) is neither blocked nor cascaded: remove_item_group() "
        "unconditionally removes the group, and the referencing items are "
        "left with a dangling item_group_id. GET /item_groups/{id}/items "
        "for the now-deleted group still returns the same ids as before "
        "(the items themselves were never touched), silently breaking the "
        "documented parent/child relationship instead of returning a "
        "conflict or cascading the delete."
    ),
)
def test_delete_item_group_referenced_by_items_is_handled_deliberately(
    base_url, user_headers, preserve_data_files
):
    preserve_data_files("item_group.json")
    existing = _first_item_group(base_url, user_headers)
    headers = _get_headers(user_headers, method="delete")

    items_before = requests.get(
        _url(base_url, f"/{existing['id']}/items"), headers=_get_headers(user_headers)
    ).json()
    assert items_before, "fixture item group is expected to have items"

    response = requests.delete(_url(base_url, f"/{existing['id']}"), headers=headers)

    assert response.status_code in (400, 409)


def test_delete_item_group_requires_authentication(base_url):
    response = requests.delete(_url(base_url, "/1"))

    assert response.status_code == 401


def test_delete_item_group_insufficient_permissions_returns_403(
    base_url, user_headers
):
    headers = _get_headers(user_headers, method="delete", allowed=False)
    response = requests.delete(_url(base_url, "/1"), headers=headers)

    assert response.status_code == 403


# endregion


# region GET /item_groups/{id}/items


def test_get_item_group_items_returns_200(base_url, user_headers):
    existing = _first_item_group(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}/items"), headers=headers
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Items.get_items_for_item_group() projects each matching row down "
        "to just its bare item id (a list of ints), unlike the structurally "
        "identical GET /suppliers/{id}/items, which returns full item "
        "objects. A client cannot get item details from this endpoint "
        "without a second round trip per id. Expected (for consistency "
        "with /suppliers/{id}/items): a list of item objects."
    ),
)
def test_get_item_group_items_returns_item_objects_not_bare_ids(
    base_url, user_headers
):
    existing = _first_item_group(base_url, user_headers)
    headers = _get_headers(user_headers)

    response = requests.get(
        _url(base_url, f"/{existing['id']}/items"), headers=headers
    )
    items = response.json()
    assert items, "fixture item group is expected to have items"

    assert all(isinstance(item, dict) for item in items)


def test_get_item_group_items_ids_are_consistent_with_items_endpoint(
    base_url, user_headers
):
    """
    Pins the *actual* shape: a list of item ids, each of which really does
    belong to this item group when looked up individually via /items/{id}.
    """
    existing = _first_item_group(base_url, user_headers)
    item_group_headers = _get_headers(user_headers)
    item_headers = user_headers(resource="items", method="get", allowed=True)

    items_response = requests.get(
        _url(base_url, f"/{existing['id']}/items"), headers=item_group_headers
    )
    assert items_response.status_code == 200
    item_ids = items_response.json()
    assert item_ids, "fixture item group is expected to have items"

    for item_id in item_ids:
        assert isinstance(item_id, int)
        direct = requests.get(
            f"{base_url}/api/v1/items/{item_id}", headers=item_headers
        )
        assert direct.status_code == 200
        assert direct.json()["item_group_id"] == existing["id"]


@pytest.mark.xfail(
    strict=True,
    reason=(
        "get_items_for_item_group() filters Items by item_group_id with no "
        "existence check on the parent item group at all. A nonexistent "
        "parent id returns 200 with an empty array (indistinguishable from "
        "a real item group that simply has no items) instead of 404."
    ),
)
def test_get_item_group_items_nonexistent_parent_returns_404(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(_url(base_url, "/999999/items"), headers=headers)

    assert response.status_code == 404


def test_get_item_group_items_requires_authentication(base_url):
    response = requests.get(_url(base_url, "/1/items"))

    assert response.status_code == 401


def test_get_item_group_items_insufficient_permissions_returns_403(
    base_url, user_headers
):
    headers = _get_headers(user_headers, allowed=False)
    response = requests.get(_url(base_url, "/1/items"), headers=headers)

    assert response.status_code == 403


def test_get_item_group_items_response_content_type_is_json(base_url, user_headers):
    headers = _get_headers(user_headers)

    response = requests.get(_url(base_url, "/1/items"), headers=headers)

    assert response.headers.get("Content-Type", "").startswith("application/json")


# endregion
