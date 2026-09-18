import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
API_DIR = REPO_ROOT / "api"
DATA_DIR = REPO_ROOT / "data"
BASE_URL = "http://localhost:3000"


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
    )

    deadline = time.time() + 10
    while time.time() < deadline:
        if process.poll() is not None:
            output = process.stdout.read().decode(errors="replace")
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
def user_headers():
    """Factory fixture to pick a user (and thus API_KEY) matching given criteria.

    Select by app name:
        user_headers(app="facility_management")

    Select by permission, e.g. a user allowed/forbidden to POST orders:
        user_headers(resource="orders", method="post", allowed=True)

    Criteria can be combined; the first matching user is returned.
    """
    users = _load_users()

    def _user_headers(app=None, resource=None, method="get", allowed=True):
        for user in users:
            if app is not None and user.get("app") != app:
                continue
            if resource is not None:
                perms = user.get("endpoint_access", {}).get(resource, {})
                if perms.get(method, False) != allowed:
                    continue
            return {"API_KEY": user["api_key"]}
        raise LookupError(
            f"No user found for app={app!r} resource={resource!r} "
            f"method={method!r} allowed={allowed!r}"
        )

    return _user_headers
