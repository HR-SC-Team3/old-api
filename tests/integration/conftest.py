import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
API_DIR = REPO_ROOT / "api"
BASE_URL = "http://localhost:3000"

# Belongs to a user with GET access to /warehouses (see data/user.json).
API_KEY = "d4s2a0b0a1n4a0l0y7t"


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
            requests.get(f"{BASE_URL}/api/v1/warehouses", headers={"API_KEY": API_KEY}, timeout=1)
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
def auth_headers():
    return {"API_KEY": API_KEY}
