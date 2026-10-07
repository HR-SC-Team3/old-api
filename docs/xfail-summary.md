# xfail summary

Every `xfail`-marked integration test documents a place where the current API deviates from
the expected/spec behavior. Almost all of them trace back to a dozen root causes that repeat
across resources.

List them (without running) with the collection plugin:

```python
# list_xfails.py
def pytest_collection_modifyitems(items):
    for item in items:
        for m in item.iter_markers("xfail"):
            reason = m.kwargs.get("reason") or (m.args[1] if len(m.args) > 1 else "")
            print(f"XFAIL | {item.nodeid} | {reason}")
```

```powershell
$env:PYTHONPATH="."; pytest --collect-only -q -p list_xfails | Select-String "^XFAIL"
```

Whether a test *xpasses* is only known by running: `pytest -rxX -q`.

## Root causes

| # | Problem | Current behavior | Expected | Resources affected |
|---|---|---|---|---|
| 1 | Unknown id on GET/PUT/DELETE | 200 (`null` body on GET, silent no-op on PUT/DELETE) | 404 | clients, orders, item_types, item_groups, item_lines, items*, locations, shipments, suppliers, transfers, warehouses |
| 2 | Malformed id (`int(paths[1])` unguarded) | 500 | 400 | every resource above, on GET, PUT and DELETE |
| 3 | POST response | 201, empty body, no id, no `Location` header | Created resource returned | clients, orders, item_groups, item_lines, items, locations, suppliers, transfers, warehouses, inventories |
| 4 | No input validation on POST/PUT | 201/200 for missing fields, wrong types, unexpected fields, duplicate ids, bad foreign keys | 400, 409 or 422 | almost everything; foreign keys in items, locations, transfers, inventories |
| 5 | Malformed JSON body | 500 | 400 | clients, orders, item_groups, item_lines, items, suppliers, transfers, warehouses |
| 6 | Content-Type never checked | `text/plain` accepted as JSON (inventories and locations give 500) | 400, 415 or 422 | item_groups, item_lines, items, suppliers, transfers, warehouses, inventories, locations |
| 7 | Query string not stripped in `do_GET` | `paths[0]` becomes e.g. `"suppliers?page=1"`, so 403 for a fully authorized user | Honor or ignore the params | item_groups, items, locations, shipments, suppliers, transfers, warehouses |
| 8 | Unknown parent on sub-resource (`/{id}/items`, `/orders`, `/inventory`) | 200 with `[]` (shipment items give 500) | 404 | item_groups, item_lines, item_types, items, suppliers, transfers, shipments |
| 9 | Error response bodies | Empty body, no `Content-Type` | Consistent JSON error schema | item_groups, item_lines, items, suppliers, transfers |

\* For `items`, PUT on an unknown id gives 500 rather than 200.

## One-off issues

- **Sub-resource shape:** `/item_groups/{id}/items` and `/item_types/{id}/items` return bare
  ids, while `/suppliers/{id}/items` returns full objects. The shipment orders endpoints also
  return a format that does not match the expected order objects.
- **Inventories:** pagination, filtering and sorting are not documented in the OpenAPI spec;
  an empty result should be 404 per the spec but the API returns a different status.
- **item_lines / items:** filtering, sorting and pagination are not supported.
- **Shipments:** POST always returns 500, so every "POST shipment..." validation test fails
  for that reason. `GET /shipments` takes ~2.74s against a 0.5s target (accepted for the old
  API).
- **Delete persistence:** a deleted resource is still returned by GET for item_lines, items,
  locations and shipments. For warehouses, `save()` uses a freshly loaded `Warehouses`
  instance, so the delete is never persisted.
- **Transfers:**
  - Committing an already-processed transfer applies the stock movement twice.
  - Committing an unknown id gives 500; a malformed id also gives 500.
  - POST with no `id` persists the bad row and then 500s on the notification log, corrupting
    the collection.
- **Item groups:** deleting a group that items still reference leaves dangling
  `item_group_id`s (neither blocked nor cascaded).
- **Locations / shipments "does_not_leak_internal_data" tests:** same underlying cause as the
  404 and malformed-id cases (200 or 500 instead of 404 or 400).

## Reason text to clean up

- `test_shipment.py::test_put_shipment_order_nonexistent_parent_return_404`: reason says
  "format doesn't match", a copy of the GET reason.
- `test_shipment.py::test_put_shipment_items_nonexistent_parent_return_404`: reason says
  "GET shipment items..." in a PUT test.
- `test_locations.py::test_put_location_rejects_invalid_foreign_key`: reason says "returning
  201" but it is a PUT.
- `test_locations.py::test_delete_location_removes_resource`: "200 instead of 400 at the
  first part" is unclear.
- `test_items.py::test_delete_item_resource_is_actually_gone`: reason is partly in Dutch.
- Typos: "returnng", "tht", "reurn", "Returnt", "immendiately".
