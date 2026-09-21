"""
Shared building blocks for synthesizing test users that cover a specific
permission permutation (a resource + set of allowed CRUD methods).

Used by:
  - tests/integration/conftest.py's `user_headers` fixture, which instead
    synthesizes a user on demand, only for the exact (resource, method,
    allowed) combination a test actually asks for, and cleans it up
    afterward. See that fixture's docstring for why on-demand is the
    default now.
"""

import itertools
import uuid

# Must match the resources api/main.py dispatches on (paths[0]) and that
# auth_provider.has_access checks endpoint_access against.
RESOURCES = [
    "warehouses",
    "locations",
    "transfers",
    "items",
    "item_lines",
    "item_groups",
    "item_types",
    "suppliers",
    "orders",
    "clients",
    "shipments",
    "inventories",
]
METHODS = ["get", "post", "put", "delete"]

GENERATED_APP_PREFIX = "perm_test_"


def _blank_access():
    return {r: {m: False for m in METHODS} for r in RESOURCES}


def make_user_for_combo(resource, combo):
    """A user with exactly `combo` (a 4-tuple of bools, in METHODS order) as
    its access to `resource`, and no access to anything else."""
    bits = "".join("1" if flag else "0" for flag in combo)
    endpoint_access = _blank_access()
    endpoint_access[resource] = dict(zip(METHODS, combo))
    return {
        "api_key": f"perm-{resource}-{bits}",
        "app": f"{GENERATED_APP_PREFIX}{resource}_{bits}",
        "endpoint_access": endpoint_access,
    }


def make_user_for_permutation(resource, method, allowed):
    """A user granting exactly `method` on `resource` per `allowed`, denied
    everywhere else. Tagged with a random suffix so repeated on-demand
    generation (e.g. across test runs) never collides on api_key/app."""
    tag = f"{resource}_{method}_{'allow' if allowed else 'deny'}"
    endpoint_access = _blank_access()
    endpoint_access[resource][method] = allowed
    unique = uuid.uuid4().hex[:8]
    return {
        "api_key": f"perm-{tag}-{unique}",
        "app": f"{GENERATED_APP_PREFIX}{tag}_{unique}",
        "endpoint_access": endpoint_access,
    }


def all_combos():
    return itertools.product([False, True], repeat=len(METHODS))
