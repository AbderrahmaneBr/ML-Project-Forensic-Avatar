"""Tests for image upload endpoints."""
import io
from unittest.mock import patch


def test_upload_image_no_conversation(client):
    """Test upload fails without valid conversation."""
    fake_conversation_id = "00000000-0000-0000-0000-000000000000"

    # Create a fake image file
    image_content = b"fake image content"
    files = {"file": ("test.jpg", io.BytesIO(image_content), "image/jpeg")}

    response = client.post(
        "/api/v1/upload/",
        files=files,
        data={"conversation_id": fake_conversation_id}
    )
    assert response.status_code == 404
    assert "Conversation not found" in response.json()["detail"]


def test_upload_invalid_file_type(client, sample_conversation):
    """Test upload rejects non-image files."""
    conversation_id = sample_conversation["id"]

    # Create a fake non-image file
    files = {"file": ("test.txt", io.BytesIO(b"text content"), "text/plain")}

    response = client.post(
        "/api/v1/upload/",
        files=files,
        data={"conversation_id": conversation_id}
    )
    assert response.status_code == 400
    assert "File type not allowed" in response.json()["detail"]


@patch("app.api.upload.upload_file")
def test_upload_image_success(mock_upload, client, sample_conversation):
    """Test successful image upload."""
    mock_upload.return_value = "images/test-uuid.jpg"

    conversation_id = sample_conversation["id"]
    image_content = b"fake jpeg content"
    files = {"file": ("evidence.jpg", io.BytesIO(image_content), "image/jpeg")}

    response = client.post(
        "/api/v1/upload/",
        files=files,
        data={"conversation_id": conversation_id}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Image uploaded successfully"
    assert "image" in data
    assert data["image"]["filename"] == "evidence.jpg"
    assert data["image"]["conversation_id"] == conversation_id


@patch("app.api.upload.upload_file")
def test_upload_allowed_types(mock_upload, client, sample_conversation):
    """Test all allowed image types are accepted."""
    mock_upload.return_value = "images/test.jpg"
    conversation_id = sample_conversation["id"]

    allowed_types = [
        ("test.jpg", "image/jpeg"),
        ("test.png", "image/png"),
        ("test.webp", "image/webp"),
        ("test.tiff", "image/tiff"),
    ]

    for filename, content_type in allowed_types:
        files = {"file": (filename, io.BytesIO(b"content"), content_type)}
        response = client.post(
            "/api/v1/upload/",
            files=files,
            data={"conversation_id": conversation_id}
        )
        assert response.status_code == 200, f"Failed for {content_type}"


@patch("app.api.upload.delete_file")
@patch("app.api.upload.upload_file")
def test_delete_image(mock_upload, mock_delete, client, sample_conversation):
    """Test deleting an uploaded image."""
    mock_upload.return_value = "images/test.jpg"

    # First upload an image
    conversation_id = sample_conversation["id"]
    files = {"file": ("test.jpg", io.BytesIO(b"content"), "image/jpeg")}
    upload_response = client.post(
        "/api/v1/upload/",
        files=files,
        data={"conversation_id": conversation_id}
    )
    image_id = upload_response.json()["image"]["id"]

    # Now delete it
    response = client.delete(f"/api/v1/upload/{image_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Image deleted successfully"
    mock_delete.assert_called_once()


def test_delete_image_not_found(client):
    """Test 404 when deleting non-existent image."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.delete(f"/api/v1/upload/{fake_id}")
    assert response.status_code == 404
