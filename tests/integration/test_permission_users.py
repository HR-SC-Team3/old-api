"""
Guarantees the invariant the `user_headers` fixture (conftest.py) relies on:
every (resource, method, allowed) combination must resolve to a user,
so a future test can always find a matching API key instead of hitting
user_headers's LookupError.

Most of these combinations aren't covered by any hand-authored app in
data/user.json (they model plausible apps, not exhaustive coverage -- e.g.
no seeded app ever had DELETE on "orders"), so exercising them here also
exercises `user_headers`'s on-demand generation path: it synthesizes a user
for the exact permutation requested, appends it to data/user.json (the live
auth_provider re-reads that file with no caching, so this works against a
running server too), and removes it again once each test finishes. See
scripts/permission_users.py for the shared generation logic.

These tests don't need the live API server: `user_headers` reads/writes
data/user.json directly.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import permission_users  # noqa: E402


@pytest.mark.parametrize("resource", permission_users.RESOURCES)
@pytest.mark.parametrize("method", permission_users.METHODS)
@pytest.mark.parametrize("allowed", [True, False])
def test_user_headers_covers_every_permutation(user_headers, resource, method, allowed):
    headers = user_headers(resource=resource, method=method, allowed=allowed)
    assert "API_KEY" in headers
