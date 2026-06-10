from fastapi.testclient import TestClient

from main import app


class TestRouterOther:
    def client(self):
        return TestClient(app)

    def test_health_check(self):
        client = self.client()
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == "☕"

    def test_redoc(self):
        client = self.client()
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "ReDoc" in response.text
