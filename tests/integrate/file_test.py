import os

from fastapi.testclient import TestClient
from uuid_extensions import uuid7str

from main import app

session_id = f"unitttest_{uuid7str()}"
username = "test1"

payload = {
    "question": "ดีจ้า",
    "sessionId": session_id,
    "username": username,
    "streaming": False,
    "reasoning": True,
}
api_key = os.getenv("AGENTIC_API_KEY", "abcd_1234")


headers = {
    "user-agent": "pytest-integration@0.1",
    "x-cap-api-key": api_key,
    "x-cap-trace-id": uuid7str(),
}


class TestRouterChat:
    check_sum = None

    def client(self):
        return TestClient(app)

    def test_upload_file(self):
        client = self.client()
        file_path = "./tests/.example/roof.jpg"
        with open(file_path, "rb") as f:
            file_data = f.read()
            headers.update({"Content-Type": "image/jpeg"})
            res = client.post(f"/api/files/{session_id}", content=file_data, headers=headers)
            assert res.status_code == 200
            assert res.json() is not None

            # Extract session_id and check_sum from the response
            response_data = res.json()
            TestRouterChat.check_sum = response_data["checkSum"]

        assert TestRouterChat.check_sum is not None, "check_sum is not set"

    def test_get_file(self):
        client = self.client()
        del headers["x-cap-api-key"]
        res = client.get(f"/api/files/{session_id}/{TestRouterChat.check_sum}", headers=headers)

        assert res.status_code == 200
        assert res.content is not None

    def test_delete_chat_session(self):
        client = self.client()
        res = client.delete(f"/api/files/{session_id}/{TestRouterChat.check_sum}", headers=headers)
        assert res.status_code == 200
        assert res.json() is not None
        assert res.json().get("ok")
        assert res.json().get("detail") == "exists"
