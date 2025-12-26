"""Tests for case management endpoints."""


def test_create_case(client):
    """Test creating a new case."""
    response = client.post(
        "/api/v1/cases/",
        json={"name": "Murder Investigation", "description": "Downtown incident"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Murder Investigation"
    assert data["description"] == "Downtown incident"
    assert "id" in data
    assert "created_at" in data


def test_create_case_minimal(client):
    """Test creating a case with only required fields."""
    response = client.post(
        "/api/v1/cases/",
        json={"name": "Minimal Case"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Minimal Case"
    assert data["description"] is None


def test_create_case_empty_name(client):
    """Test that empty name is rejected."""
    response = client.post(
        "/api/v1/cases/",
        json={"name": ""}
    )
    assert response.status_code == 422  # Validation error


def test_get_case(client, sample_case):
    """Test retrieving a case by ID."""
    case_id = sample_case["id"]
    response = client.get(f"/api/v1/cases/{case_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == case_id
    assert data["name"] == "Test Case"


def test_get_case_not_found(client):
    """Test 404 for non-existent case."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/cases/{fake_id}")
    assert response.status_code == 404


def test_get_all_cases(client):
    """Test retrieving all cases."""
    # Create multiple cases
    client.post("/api/v1/cases/", json={"name": "Case 1"})
    client.post("/api/v1/cases/", json={"name": "Case 2"})
    client.post("/api/v1/cases/", json={"name": "Case 3"})

    response = client.get("/api/v1/cases/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_get_all_cases_empty(client):
    """Test retrieving cases when none exist."""
    response = client.get("/api/v1/cases/")
    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_get_cases_with_images(client, sample_case):
    """Test that cases include linked images."""
    response = client.get("/api/v1/cases/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "images" in data[0]
    assert data[0]["images"] == []  # No images uploaded yet
