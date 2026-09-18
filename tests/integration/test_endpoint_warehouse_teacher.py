import pytest
import requests


@pytest.fixture
def _data():
    return {
        # "url": "http://localhost:3000/api/v1/",
        "api_key": "d4s2a0b0a1n4a0l0y7t",
    }


def test_get_warehouse(base_url, _data):
    # Send a GET request to the API
    response = requests.get(
        f"{base_url}/api/v1/warehouses", headers={"API_KEY": _data["api_key"]}
    )

    # Get the status code and response data
    status_code = response.status_code

    # Verify that the status code is 200 (OK)
    assert status_code == 200
