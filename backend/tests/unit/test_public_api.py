import pytest
from app import create_app


@pytest.mark.parametrize(
    "path", ["/api/v1/health/live", "/api/v1/demo/manifest", "/api/v1/demo/files", "/api/v1/demo/answers/submission"]
)
def test_public_routes_without_provider(path):
    app = create_app({"TESTING": True, "RATELIMIT_ENABLED": False, "GEMINI_API_KEY": ""})
    response = app.test_client().get(path)
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store"


def test_upload_capacity_error_has_actionable_message():
    from flask import request

    app = create_app({"TESTING": True, "RATELIMIT_ENABLED": False, "MAX_CONTENT_LENGTH": 16})

    @app.post("/test-capacity")
    def capacity():
        return request.get_data()

    response = app.test_client().post("/test-capacity", data=b"x" * 17)
    assert response.status_code == 413
    assert response.json["error"]["code"] == "upload_too_large"
    assert "100 MiB" in response.json["error"]["message"]
