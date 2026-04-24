from api_app.main import app


def test_api_registers_expected_routes() -> None:
    paths = {route.path for route in app.routes}

    assert {
        "/auth/onboarding/create-company",
        "/auth/session",
        "/auth/session/select-company",
        "/bootstrap",
        "/documents",
        "/healthz",
    } <= paths
