from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app import app, activities


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        original_state = deepcopy(activities)

        yield test_client

        activities.clear()
        activities.update(deepcopy(original_state))


# AAA pattern: Arrange, Act, Assert


def test_root_redirects_to_static_index(client):
    # Arrange
    expected_location = "/static/index.html"

    # Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == expected_location

def test_get_activities_returns_catalog(client):
    # Arrange
    # no special setup required

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    payload = response.json()
    assert "Chess Club" in payload
    assert "participants" in payload["Chess Club"]


def test_get_activities_returns_activity_details(client):
    # Arrange
    activity_name = "Chess Club"

    # Act
    response = client.get("/activities")

    # Assert
    activity = response.json()[activity_name]
    assert response.status_code == 200
    assert set(activity) == {"description", "schedule", "max_participants", "participants"}
    assert isinstance(activity["participants"], list)


def test_signup_adds_student_to_activity(client):
    # Arrange
    activity_name = "Chess Club"
    email = "newstudent@mergington.edu"

    # Act
    response = client.post(f"/activities/{activity_name}/signup?email={email}")

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == f"Signed up {email} for {activity_name}"
    assert email in activities[activity_name]["participants"]


def test_signup_rejects_duplicate_email(client):
    # Arrange
    activity_name = "Chess Club"
    email = "michael@mergington.edu"

    # Act
    response = client.post(f"/activities/{activity_name}/signup?email={email}")

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"


def test_signup_rejects_unknown_activity(client):
    # Arrange
    activity_name = "Not Real"
    email = "newstudent@mergington.edu"

    # Act
    response = client.post(f"/activities/{activity_name}/signup?email={email}")

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_rejects_student_registered_for_another_activity(client):
    # Arrange
    activity_name = "Soccer Team"
    email = "michael@mergington.edu"

    # Act
    response = client.post(
        f"/activities/{activity_name}/signup", params={"email": email}
    )

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for another activity"
    assert email not in activities[activity_name]["participants"]


def test_signup_rejects_when_activity_is_full(client):
    # Arrange
    activity_name = "Basketball Team"
    email = "newstudent@mergington.edu"
    activities[activity_name]["participants"] = [
        f"student{i}@mergington.edu" for i in range(activities[activity_name]["max_participants"])
    ]

    # Act
    response = client.post(f"/activities/{activity_name}/signup?email={email}")

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Activity is full"


def test_unregister_removes_student_from_activity(client):
    # Arrange
    activity_name = "Chess Club"
    email = "daniel@mergington.edu"

    # Act
    response = client.delete(f"/activities/{activity_name}/participants?email={email}")

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == f"Unregistered {email} from {activity_name}"
    assert email not in activities[activity_name]["participants"]


def test_unregister_rejects_non_member(client):
    # Arrange
    activity_name = "Chess Club"
    email = "not-a-member@mergington.edu"

    # Act
    response = client.delete(f"/activities/{activity_name}/participants?email={email}")

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"


def test_signup_then_unregister_allows_resignup(client):
    # Arrange
    activity_name = "Soccer Team"
    email = "newstudent@mergington.edu"

    # Act
    signup_response = client.post(
        f"/activities/{activity_name}/signup", params={"email": email}
    )
    unregister_response = client.delete(
        f"/activities/{activity_name}/participants", params={"email": email}
    )
    resign_response = client.post(
        f"/activities/{activity_name}/signup", params={"email": email}
    )

    # Assert
    assert signup_response.status_code == 200
    assert unregister_response.status_code == 200
    assert resign_response.status_code == 200
    assert email in activities[activity_name]["participants"]


def test_unregister_rejects_unknown_activity(client):
    # Arrange
    activity_name = "Not Real"
    email = "newstudent@mergington.edu"

    # Act
    response = client.delete(
        f"/activities/{activity_name}/participants", params={"email": email}
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_requires_email(client):
    # Arrange
    activity_name = "Soccer Team"

    # Act
    response = client.post(f"/activities/{activity_name}/signup")

    # Assert
    assert response.status_code == 422


def test_unregister_requires_email(client):
    # Arrange
    activity_name = "Soccer Team"

    # Act
    response = client.delete(f"/activities/{activity_name}/participants")

    # Assert
    assert response.status_code == 422
