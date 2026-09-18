import json
import socketserver
import sys
import threading
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
API_DIR = REPO_ROOT / "api"
DATA_DIR = REPO_ROOT / "data"

# The api/ package uses top-level imports (e.g. "from providers import
# auth_provider") that only resolve with api/ on sys.path, so import the
# server module in-process rather than shelling out to `python main.py`.
# This also keeps the server's code inside the pytest process, which is what
# lets pytest-cov measure it (a subprocess killed via Popen.terminate()
# would never flush its coverage data, especially on Windows).
sys.path.insert(0, str(API_DIR))
import main as api_main  # noqa: E402


def _load_users():
    with open(DATA_DIR / "user.json", "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def api_server():
    httpd = socketserver.TCPServer(("localhost", 0), api_main.ApiRequestHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    yield f"http://localhost:{httpd.server_address[1]}"

    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=5)


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
