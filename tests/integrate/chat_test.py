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
    def client(self):
        return TestClient(app)

    def test_prediction_chat_stream(self):
        client = self.client()
        payload["streaming"] = True
        payload["reasoning"] = True
        res = client.post("/api/chat/prediction", json=payload, headers=headers)
        for event in res.iter_lines():
            assert event is not None
            assert '"mode":"error"' not in event

    def test_prediction_chat_no_stream_reason(self):
        client = self.client()
        payload["streaming"] = False
        payload["reasoning"] = True
        res = client.post("/api/chat/prediction", json=payload, headers=headers)
        data = res.json()
        assert res.status_code == 200
        assert all(key in data for key in ["text", "chatId", "sessionId", "agentReasoning"])
        assert len(data["agentReasoning"]) > 0

    def test_prediction_chat_no_stream_no_reason(self):
        client = self.client()
        payload["streaming"] = False
        payload["reasoning"] = False
        res = client.post("/api/chat/prediction", json=payload, headers=headers)
        data = res.json()
        assert res.status_code == 200
        assert all(key in data for key in ["text", "chatId", "sessionId", "agentReasoning"])
        assert len(data["agentReasoning"]) == 0

    def test_prediction_1_image(self):
        client = self.client()
        payload = {
            "question": "",
            "sessionId": session_id,
            "attachments": ["https://www.scg-smartdigital.com/wp-content/uploads/2023/12/8852422116515.webp"],
            "username": username,
            "streaming": False,
            "reasoning": True,
        }
        res = client.post("/api/chat/prediction", json=payload, headers=headers)
        data = res.json()
        assert res.status_code == 200
        assert all(key in data for key in ["text", "chatId", "sessionId", "agentReasoning"])
        assert len(data["agentReasoning"]) > 0

    def test_prediction_1_image_text(self):
        client = self.client()
        payload = {
            "question": "ราคาเท่าไหร่",
            "sessionId": session_id,
            "attachments": [
                "https://scg-digital-prod-dam-product.s3.ap-southeast-1.amazonaws.com/085bd951cbce4c8490f887e40f803c33.png"
            ],
            "username": username,
            "streaming": False,
            "reasoning": True,
        }
        res = client.post("/api/chat/prediction", json=payload, headers=headers)
        data = res.json()
        assert res.status_code == 200
        assert all(key in data for key in ["text", "chatId", "sessionId", "agentReasoning"])
        assert len(data["agentReasoning"]) > 0

    def test_prediction_2_image(self):
        client = self.client()
        payload = {
            "question": "",
            "sessionId": session_id,
            "attachments": [
                "https://www.scgdigital.com/_next/image?url=https%3A%2F%2Fd2sfvqdmhak4f9.cloudfront.net%2Fproduct%252F311816%252Fimages%252F298573%252F1209616-01.jpg&w=1920&q=75",
                "https://www.scgdigital.com/_next/image?url=https%3A%2F%2Fd2sfvqdmhak4f9.cloudfront.net%2Fproduct%252F316673%252Fimages%252F305139%252F1199906-01.jpg&w=1920&q=75",
            ],
            "username": username,
            "streaming": False,
            "reasoning": True,
        }
        res = client.post("/api/chat/prediction", json=payload, headers=headers)
        data = res.json()
        assert res.status_code == 200
        assert all(key in data for key in ["text", "chatId", "sessionId", "agentReasoning"])
        assert len(data["agentReasoning"]) > 0

    def test_get_chat_session_csv(self):
        client = self.client()
        res = client.get(f"/api/chat/{session_id}?format=csv", headers=headers)
        assert res.status_code == 200
        assert res.headers["Content-Type"] == "text/csv; charset=utf-8"
        assert res.text.startswith('"id","role","content"')  # Adjust based on expected CSV content

    def test_get_chat_session_history(self):
        client = self.client()
        res = client.get(f"/api/chat/{session_id}/history?limit=100&order=desc", headers=headers)
        assert res.status_code == 200
        assert res.headers["Content-Type"] == "application/json"
        assert isinstance(res.json(), list)  # Assuming the response is a list of chat history

    def test_delete_chat_session(self):
        client = self.client()
        res = client.delete(f"/api/chat/{session_id}", headers=headers)
        assert res.status_code == 200
        assert "affected" in res.json().get("detail", "")
