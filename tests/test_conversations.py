"""Tests for conversation management endpoints."""


def test_create_conversation(client):
    """Test creating a new conversation."""
    response = client.post(
        "/api/v1/conversations/",
        json={"name": "Murder Investigation", "description": "Downtown incident"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Murder Investigation"
    assert data["description"] == "Downtown incident"
    assert "id" in data
    assert "created_at" in data


def test_create_conversation_minimal(client):
    """Test creating a conversation with only required fields."""
    response = client.post(
        "/api/v1/conversations/",
        json={"name": "Minimal Conversation"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal Conversation"
    assert data["description"] is None


def test_create_conversation_empty_name(client):
    """Test that empty name is rejected."""
    response = client.post(
        "/api/v1/conversations/",
        json={"name": ""}
    )
    assert response.status_code == 422  # Validation error


def test_get_conversation(client, sample_conversation):
    """Test retrieving a conversation by ID."""
    conversation_id = sample_conversation["id"]
    response = client.get(f"/api/v1/conversations/{conversation_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == conversation_id
    assert data["name"] == "Test Conversation"


def test_get_conversation_not_found(client):
    """Test 404 for non-existent conversation."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/conversations/{fake_id}")
    assert response.status_code == 404


def test_get_all_conversations(client):
    """Test retrieving all conversations."""
    # Create multiple conversations
    client.post("/api/v1/conversations/", json={"name": "Conversation 1"})
    client.post("/api/v1/conversations/", json={"name": "Conversation 2"})
    client.post("/api/v1/conversations/", json={"name": "Conversation 3"})

    response = client.get("/api/v1/conversations/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_get_all_conversations_empty(client):
    """Test retrieving conversations when none exist."""
    response = client.get("/api/v1/conversations/")
    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_get_conversations_with_images(client, sample_conversation):
    """Test that conversations include linked images."""
    response = client.get("/api/v1/conversations/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "images" in data[0]
    assert data[0]["images"] == []  # No images uploaded yet


def test_update_conversation(client, sample_conversation):
    """Test updating a conversation."""
    conversation_id = sample_conversation["id"]
    response = client.patch(
        f"/api/v1/conversations/{conversation_id}",
        json={"name": "Updated Name", "description": "Updated description"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "Updated description"


def test_delete_conversation(client, sample_conversation):
    """Test deleting a conversation."""
    conversation_id = sample_conversation["id"]
    response = client.delete(f"/api/v1/conversations/{conversation_id}")
    assert response.status_code == 200

    # Verify it's gone
    response = client.get(f"/api/v1/conversations/{conversation_id}")
    assert response.status_code == 404


def test_get_messages_empty(client, sample_conversation):
    """Test getting messages from a conversation with no messages."""
    conversation_id = sample_conversation["id"]
    response = client.get(f"/api/v1/conversations/{conversation_id}/messages")
    assert response.status_code == 200
    data = response.json()
    assert data == []
