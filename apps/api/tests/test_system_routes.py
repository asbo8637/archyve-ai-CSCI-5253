def test_healthcheck_returns_service_status(api_client) -> None:
    response = api_client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "storage_root" in response.json()
