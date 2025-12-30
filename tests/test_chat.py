"""Tests for chat endpoints."""
from unittest.mock import patch


def test_send_message_conversation_not_found(client):
    """Test chat fails with invalid conversation."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.post(
        f"/api/v1/conversations/{fake_id}/chat",
        json={"message": "Hello"}
    )
    assert response.status_code == 404
    assert "Conversation not found" in response.json()["detail"]


@patch("app.api.chat.chat")
def test_send_message_success(mock_chat, client, sample_conversation):
    """Test successful chat message."""
    mock_chat.return_value = "The evidence suggests foul play."

    conversation_id = sample_conversation["id"]
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/chat",
        json={"message": "What do you see in the evidence?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"]["role"] == "assistant"
    assert data["message"]["content"] == "The evidence suggests foul play."
    assert data["conversation_id"] == conversation_id


@patch("app.api.chat.chat")
def test_chat_saves_user_message(mock_chat, client, sample_conversation):
    """Test that user messages are saved to the conversation."""
    mock_chat.return_value = "Response"

    conversation_id = sample_conversation["id"]
    client.post(
        f"/api/v1/conversations/{conversation_id}/chat",
        json={"message": "Test message"}
    )

    # Get messages to verify user message was saved
    response = client.get(f"/api/v1/conversations/{conversation_id}/messages")
    data = response.json()

    # Should have user message and assistant message
    assert len(data) == 2
    assert data[0]["role"] == "user"
    assert data[0]["content"] == "Test message"
    assert data[1]["role"] == "assistant"


@patch("app.api.chat.chat")
def test_chat_maintains_history(mock_chat, client, sample_conversation):
    """Test that multiple messages build up history."""
    mock_chat.return_value = "Response"

    conversation_id = sample_conversation["id"]

    # Send multiple messages
    client.post(
        f"/api/v1/conversations/{conversation_id}/chat",
        json={"message": "First message"}
    )
    client.post(
        f"/api/v1/conversations/{conversation_id}/chat",
        json={"message": "Second message"}
    )

    # Get messages
    response = client.get(f"/api/v1/conversations/{conversation_id}/messages")
    data = response.json()

    # Should have 4 messages (2 user + 2 assistant)
    assert len(data) == 4
    assert data[0]["content"] == "First message"
    assert data[2]["content"] == "Second message"
