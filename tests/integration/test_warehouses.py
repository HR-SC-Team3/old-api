import requests


def test_get_warehouses_returns_list(base_url, user_headers):
    headers = user_headers(resource="warehouses", method="get", allowed=True)
    response = requests.get(f"{base_url}/api/v1/warehouses", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) > 0
    assert "id" in body[0]
