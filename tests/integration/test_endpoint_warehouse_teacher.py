import requests


def test_get_warehouse(base_url, user_headers):
    # Send a GET request to the API
    headers = user_headers(resource="warehouses", method="get", allowed=True)
    response = requests.get(f"{base_url}/api/v1/warehouses", headers=headers)

    # Get the status code and response data
    status_code = response.status_code

    # Verify that the status code is 200 (OK)
    assert status_code == 200
