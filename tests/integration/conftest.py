import collections
import functools
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
API_DIR = REPO_ROOT / "api"
DATA_DIR = REPO_ROOT / "data"
SCRIPTS_DIR = REPO_ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
from permission_users import make_user_for_permutation  # noqa: E402

# Deliberately 127.0.0.1, not "localhost": resolving "localhost" added a
# consistent ~2s tax to every single request in this environment (confirmed
# by timing the same endpoint against both hosts back to back), almost
# certainly an IPv6-then-IPv4 dual-stack connect() fallback -- nothing to do
# with the server itself. Real clients hitting this API should do the same.
BASE_URL = "http://127.0.0.1:3000"

# The dev server (api/main.py) is a single-threaded socketserver.TCPServer
# that has been observed to wedge completely (both client and server left
# blocked on an established connection, no CPU activity on either side)
# after a few dozen sequential requests in a single test run, seemingly
# independent of which endpoints those requests hit. Without a timeout, a
# wedge like that hangs the whole test run indefinitely instead of failing
# the one test that hit it. Default a generous-but-finite timeout onto every
# `requests.get/post/put/delete` call made from the test suite so a wedge
# surfaces as a clear, fast test failure instead of a silent hang.
_DEFAULT_TIMEOUT = 10


def _with_default_timeout(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        kwargs.setdefault("timeout", _DEFAULT_TIMEOUT)
        return func(*args, **kwargs)

    return wrapper


for _method in ("get", "post", "put", "delete", "patch"):
    setattr(requests, _method, _with_default_timeout(getattr(requests, _method)))


def _load_users():
    with open(DATA_DIR / "user.json", "r") as f:
        return json.load(f)


# Any valid key, just to probe that the server has come up.
_PROBE_API_KEY = _load_users()[0]["api_key"]


@pytest.fixture(scope="session")
def api_server():
    process = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=API_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ, "API_TEST_MODE": "1"},
    )

    # BaseHTTPRequestHandler logs a line per request to stderr (redirected
    # into this same pipe) via log_message()/address_string(). Nothing
    # otherwise reads that pipe, so once enough requests accumulate the OS
    # pipe buffer fills up and the server's next log write blocks forever --
    # wedging the single-threaded server for the rest of the test session
    # (observed firsthand: after ~40-90 requests, both the client and server
    # sit at 0% CPU on an established-but-frozen connection). Continuously
    # draining the pipe in a background thread for the life of the process
    # avoids that deadlock; keep only a bounded tail of it for diagnostics.
    log_tail = collections.deque(maxlen=200)

    def _drain_output():
        for line in iter(process.stdout.readline, b""):
            log_tail.append(line)

    drain_thread = threading.Thread(target=_drain_output, daemon=True)
    drain_thread.start()

    deadline = time.time() + 10
    while time.time() < deadline:
        if process.poll() is not None:
            output = b"".join(log_tail).decode(errors="replace")
            raise RuntimeError(f"API server exited early:\n{output}")
        try:
            requests.get(
                f"{BASE_URL}/api/v1/warehouses",
                headers={"API_KEY": _PROBE_API_KEY},
                timeout=1,
            )
            break
        except requests.ConnectionError:
            time.sleep(0.2)
    else:
        process.terminate()
        raise RuntimeError("API server did not start in time")

    yield BASE_URL

    process.terminate()
    process.wait(timeout=5)


@pytest.fixture
def base_url(api_server):
    return api_server


@pytest.fixture
def preserve_data_files(base_url):
    """Snapshot data/*.json files before a mutating (POST/PUT/DELETE) test and
    restore their exact original bytes afterward, regardless of pass/fail.

    api/providers/data_provider.py now caches one pool instance per resource
    for the life of the server process (see its module docstring), so a
    mutation actually persists both on disk *and* in the server's in-memory
    cache for every later test in this session. Restoring the on-disk bytes
    alone isn't enough, the server also needs to be told to reload, via the
    test-only `/api/v1/_test/reset-cache` endpoint (only reachable when the
    server was started with API_TEST_MODE=1, which api_server does).
    """
    snapshots = {}

    def _track(*filenames):
        for name in filenames:
            path = DATA_DIR / name
            if path not in snapshots:
                snapshots[path] = path.read_bytes()

    yield _track

    for path, original in snapshots.items():
        path.write_bytes(original)

    if snapshots:
        requests.post(f"{base_url}/api/v1/_test/reset-cache")


@pytest.fixture
def user_headers():
    """Factory fixture to pick a user (and thus API_KEY) matching given criteria.

    Select by app name:
        user_headers(app="facility_management")

    Select by permission, e.g. a user allowed/forbidden to POST orders:
        user_headers(resource="orders", method="post", allowed=True)

    Criteria can be combined; the first matching user is returned.

    A `resource`+`method` query with no matching hand-authored user instead
    generates one on the fly via permission_users.make_user_for_permutation,
    appends it to data/user.json (auth_provider re-reads that file on every
    request, with no caching, so the live server picks it up immediately),
    and removes it again once the test is done.
    """
    users = _load_users()
    generated_api_keys = []

    def _user_headers(app=None, resource=None, method="get", allowed=True):
        for user in users:
            if app is not None and user.get("app") != app:
                continue
            if resource is not None:
                perms = user.get("endpoint_access", {}).get(resource, {})
                if perms.get(method, False) != allowed:
                    continue
            return {"API_KEY": user["api_key"]}

        if app is not None or resource is None:
            raise LookupError(
                f"No user found for app={app!r} resource={resource!r} "
                f"method={method!r} allowed={allowed!r}"
            )

        new_user = make_user_for_permutation(resource, method, allowed)
        with open(DATA_DIR / "user.json", "r") as f:
            all_users = json.load(f)
        all_users.append(new_user)
        with open(DATA_DIR / "user.json", "w") as f:
            json.dump(all_users, f, indent=4)
            f.write("\n")
        generated_api_keys.append(new_user["api_key"])
        return {"API_KEY": new_user["api_key"]}

    yield _user_headers

    if generated_api_keys:
        with open(DATA_DIR / "user.json", "r") as f:
            all_users = json.load(f)
        all_users = [u for u in all_users if u["api_key"] not in generated_api_keys]
        with open(DATA_DIR / "user.json", "w") as f:
            json.dump(all_users, f, indent=2)
            f.write("\n")
