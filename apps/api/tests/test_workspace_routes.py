from api_app.features.workspace import router as workspace_router


def test_bootstrap_returns_workspace_context(api_client, monkeypatch) -> None:
    monkeypatch.setattr(
        workspace_router,
        "get_settings",
        lambda: type(
            "Settings",
            (),
            {"app_name": "Archyve AI", "auth0_configured": True},
        )(),
    )

    response = api_client.get("/bootstrap")

    assert response.status_code == 200
    assert response.json() == {"app_name": "Archyve AI", "auth_enabled": True}
