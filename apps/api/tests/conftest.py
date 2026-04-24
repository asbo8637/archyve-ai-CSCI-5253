from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from api_app.main import app


@pytest.fixture
def api_client() -> Generator[TestClient, None, None]:
    app.dependency_overrides.clear()

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
