"""
Tests for the Mergington High School extracurricular activities API.

Tests follow the AAA (Arrange-Act-Assert) pattern:
- Arrange: Set up test data and preconditions
- Act: Execute the code being tested
- Assert: Verify the results
"""

import pytest
from fastapi import HTTPException


class TestRoot:
    def test_root_redirect(self, client):
        """Test that root endpoint redirects to static index.html"""
        # Act
        response = client.get("/", follow_redirects=False)
        
        # Assert
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    def test_get_activities_returns_all_activities(self, client):
        """Test that all activities are returned"""
        # Act
        response = client.get("/activities")
        activities = response.json()
        
        # Assert
        assert response.status_code == 200
        assert len(activities) == 9  # We have 9 activities
        assert "Chess Club" in activities
        assert "Programming Class" in activities
        assert "Gym Class" in activities

    def test_get_activities_structure(self, client):
        """Test that activities have correct structure"""
        # Act
        response = client.get("/activities")
        activities = response.json()
        activity = activities["Chess Club"]
        
        # Assert
        assert response.status_code == 200
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        assert isinstance(activity["participants"], list)

    def test_get_activities_participants(self, client):
        """Test that existing participants are returned"""
        # Arrange
        expected_participants = ["michael@mergington.edu", "daniel@mergington.edu"]
        
        # Act
        response = client.get("/activities")
        activities = response.json()
        chess_club = activities["Chess Club"]
        
        # Assert
        assert response.status_code == 200
        assert len(chess_club["participants"]) == 2
        for participant in expected_participants:
            assert participant in chess_club["participants"]


class TestSignupForActivity:
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        # Arrange
        email = "alice@mergington.edu"
        activity = "Basketball Team"
        
        # Act
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Assert
        assert response.status_code == 200
        assert f"Signed up {email} for {activity}" in response.json()["message"]

    def test_signup_activity_not_found(self, client):
        """Test signup for non-existent activity"""
        # Arrange
        email = "alice@mergington.edu"
        activity = "Non-Existent Club"
        
        # Act
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_duplicate_registration(self, client):
        """Test that duplicate registration is prevented"""
        # Arrange
        email = "michael@mergington.edu"
        activity = "Chess Club"
        
        # Act - Try to register someone already registered
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Assert
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_at_capacity(self, client):
        """Test that signup fails when activity is at max capacity"""
        # Arrange
        activity = "Basketball Team"
        response = client.get("/activities")
        activities_data = response.json()
        max_participants = activities_data[activity]["max_participants"]
        
        # Act - Sign up enough people to fill the activity
        for i in range(max_participants):
            email = f"student{i}@mergington.edu"
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200

        # Try to sign up one more person (should fail)
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": "overfull@mergington.edu"}
        )
        
        # Assert
        assert response.status_code == 400
        assert "maximum capacity" in response.json()["detail"]

    def test_signup_updates_participants_list(self, client):
        """Test that participant list is updated after signup"""
        # Arrange
        email = "artist@mergington.edu"
        activity = "Art Studio"
        
        # Act - Sign up for activity
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Verify participant was added
        response = client.get("/activities")
        activities = response.json()
        
        # Assert
        assert email in activities[activity]["participants"]


class TestUnregisterFromActivity:
    def test_unregister_success(self, client):
        """Test successful unregistration from activity"""
        # Arrange
        email = "michael@mergington.edu"
        activity = "Chess Club"
        
        # Act
        response = client.delete(
            f"/activities/{activity}/signup/{email}"
        )
        
        # Assert
        assert response.status_code == 200
        assert f"Unregistered {email} from {activity}" in response.json()["message"]

    def test_unregister_activity_not_found(self, client):
        """Test unregistration from non-existent activity"""
        # Arrange
        email = "someone@mergington.edu"
        activity = "Non-Existent Club"
        
        # Act
        response = client.delete(
            f"/activities/{activity}/signup/{email}"
        )
        
        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_participant_not_found(self, client):
        """Test unregistration for non-registered participant"""
        # Arrange
        email = "notregistered@mergington.edu"
        activity = "Chess Club"
        
        # Act
        response = client.delete(
            f"/activities/{activity}/signup/{email}"
        )
        
        # Assert
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_unregister_removes_from_list(self, client):
        """Test that participant is removed from list after unregistration"""
        # Arrange
        email = "michael@mergington.edu"
        activity = "Chess Club"
        
        # Verify they're registered initially
        response = client.get("/activities")
        activities = response.json()
        assert email in activities[activity]["participants"]
        
        # Act - Unregister
        response = client.delete(
            f"/activities/{activity}/signup/{email}"
        )
        assert response.status_code == 200
        
        # Assert - Verify they're removed
        response = client.get("/activities")
        activities = response.json()
        assert email not in activities[activity]["participants"]

    def test_unregister_opens_spot(self, client):
        """Test that unregistration opens up a spot for signup"""
        # Arrange
        activity = "Swimming Club"
        response = client.get("/activities")
        activities_data = response.json()
        max_participants = activities_data[activity]["max_participants"]

        # Fill the activity up to capacity
        for i in range(max_participants):
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": f"swimmer{i}@mergington.edu"}
            )
            assert response.status_code == 200

        # Attempt to add one more (should fail)
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": "overflow@mergington.edu"}
        )
        assert response.status_code == 400

        # Act - Remove one participant
        response = client.delete(
            f"/activities/{activity}/signup/swimmer0@mergington.edu"
        )
        assert response.status_code == 200

        # Assert - Now adding a new person should work
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": "newperson@mergington.edu"}
        )
        assert response.status_code == 200


class TestIntegration:
    def test_signup_and_unregister_flow(self, client):
        """Test complete signup and unregister flow"""
        # Arrange
        email = "test.student@mergington.edu"
        activity = "Drama Club"

        # Act - Sign up
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == 200

        # Assert - Verify signup
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]

        # Act - Unregister
        response = client.delete(
            f"/activities/{activity}/signup/{email}"
        )
        assert response.status_code == 200

        # Assert - Verify unregistration
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]

    def test_multiple_signups_tracking(self, client):
        """Test that multiple participant signups are tracked correctly"""
        # Arrange
        activity = "Debate Team"
        emails = [
            "debater1@mergington.edu",
            "debater2@mergington.edu",
            "debater3@mergington.edu"
        ]

        # Act - Sign up multiple people
        for email in emails:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200

        # Assert - Verify all were added
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        
        for email in emails:
            assert email in participants
        
        # Verify count
        assert len(participants) == len(emails)
