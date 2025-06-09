import requests
import json
import time

# Base URLs for your Docker Compose services
APP_FRONTEND_URL = "http://localhost:5000"
DB_API_URL = "http://localhost:5001"
AUTH_API_URL = "http://localhost:5002"
EVENTS_API_URL = "http://localhost:5005" # Assuming this is for events data

def run_test_case(name, url, method, payload=None, expected_status=200, expected_substring=None, headers=None):
    """
    Helper function to run a single API test case and print results.
    """
    print(f"\n--- Running Test: {name} ---")
    
    if headers is None:
        headers = {"Content-Type": "application/json"}
    
    try:
        if method.upper() == 'POST':
            response = requests.post(url, headers=headers, data=json.dumps(payload) if payload else None)
        elif method.upper() == 'GET':
            response = requests.get(url, headers=headers)
        elif method.upper() == 'PUT':
            response = requests.put(url, headers=headers, data=json.dumps(payload) if payload else None)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        print(f"URL: {url}")
        print(f"Method: {method}")
        if payload:
            print(f"Payload: {payload}")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        assert response.status_code == expected_status, \
            f"Test '{name}' FAILED: Expected status {expected_status}, got {response.status_code}. Response: {response.text}"
        
        if expected_substring:
            assert expected_substring in response.text, \
                f"Test '{name}' FAILED: Expected '{expected_substring}' in response, but not found. Response: {response.text}"
        
        print(f"Test '{name}' PASSED.")
        return response
    except requests.exceptions.RequestException as e:
        print(f"Test '{name}' FAILED: Request failed - {e}")
        return None
    except AssertionError as e:
        print(e)
        return None
    except Exception as e:
        print(f"An unexpected error occurred during test '{name}': {e}")
        return None

def test_user_flow():
    print("======================================================")
    print("      Starting User Registration, Login & Dashboard Flow Tests")
    print("======================================================")

    # --- 1. User Registration ---
    print("\n--- Testing User Registration ---")
    user_data = {
        "first_name": "Test",
        "last_name": "User",
        "phone_number": "1234567890",
        "email_id": "test.user@example.com",
        "password": "testpassword",
        "tower_number": "T1",
        "wing": "A",
        "number": "101",
        "type_val": "Flat",
        "user_role": "user"
    }
    
    # Ensure user is cleaned up before running the test
    print("\nAttempting to delete existing user for clean test...")
    run_test_case(
        "Delete existing user (if any)",
        f"{DB_API_URL}/users/{user_data['phone_number']}",
        "DELETE",
        expected_status=[200, 204, 404], # Accept 200, 204 for success, 404 if not found
        expected_substring=""
    )
    time.sleep(1) # Give a moment for cleanup

    register_response = run_test_case(
        "User Registration",
        f"{APP_FRONTEND_URL}/register",
        "POST",
        payload=user_data,
        expected_status=201, # Expect 201 Created
        expected_substring="User registered successfully"
    )
    if register_response is None:
        print("Registration test failed, cannot proceed with login.")
        return

    # --- 2. User Login ---
    print("\n--- Testing User Login ---")
    login_data = {
        "phone_number": user_data["phone_number"],
        "password": user_data["password"]
    }

    login_response = run_test_case(
        "User Login",
        f"{APP_FRONTEND_URL}/login",
        "POST",
        payload=login_data,
        expected_status=200,
        expected_substring=user_data["phone_number"] # Assuming phone number is in the login success response
    )
    if login_response is None:
        print("Login test failed, cannot proceed with dashboard flow.")
        return
    
    # Extract token if your auth_api returns one and it's needed for subsequent calls
    # For now, relying on phone_number as stored in localStorage in frontend.
    # If backend protected endpoints require a token in headers, you'd extract it here:
    # auth_token = login_response.json().get('token')
    # headers_with_auth = {"Content-Type": "application/json", "Authorization": f"Bearer {auth_token}"}

    # --- 3. User Dashboard & User Details Flow ---
    print("\n--- Testing User Dashboard & User Details Access ---")
    user_phone = user_data["phone_number"]
    
    # 3.1. Fetch User Details (Initial Dashboard Load)
    get_user_details_response = run_test_case(
        "Fetch User Details for Dashboard",
        f"{APP_FRONTEND_URL}/api/users/{user_phone}",
        "GET",
        expected_status=200,
        expected_substring=user_data["first_name"]
    )
    if get_user_details_response is None:
        print("Failed to fetch user details, cannot proceed with update test.")
        return

    # 3.2. Fetch All Events (Dashboard Initial Load)
    get_events_response = run_test_case(
        "Fetch All Events for Dashboard",
        f"{APP_FRONTEND_URL}/api/events",
        "GET",
        expected_status=200,
        expected_substring="events" # Assuming the response contains an 'events' key
    )
    if get_events_response is None:
        print("Failed to fetch events, cannot proceed with participation test.")
        # Proceed cautiously if no events, or add logic to create dummy event
        # For now, assuming events exist or the test gracefully handles no events.

    # 3.3. Update User Details
    print("\n--- Testing Update User Details ---")
    updated_user_data = {
        "first_name": "UpdatedTest",
        "last_name": "User",
        "email_id": "updated.test.user@example.com",
        "tower_number": "T2",
        "wing": "B",
        "number": "202",
        "type_val": "Flat",
        "user_role": "user"
    }

    update_user_response = run_test_case(
        "Update User Details",
        f"{APP_FRONTEND_URL}/api/users/{user_phone}",
        "PUT",
        payload=updated_user_data,
        expected_status=200,
        expected_substring="User details updated successfully" # Assuming this message from db_api or app.py
    )
    if update_user_response is None:
        print("Failed to update user details.")
        return

    # 3.4. Verify Updated User Details
    verify_updated_user_details_response = run_test_case(
        "Verify Updated User Details",
        f"{APP_FRONTEND_URL}/api/users/{user_phone}",
        "GET",
        expected_status=200,
        expected_substring="UpdatedTest" # Check if the first name is updated
    )
    if verify_updated_user_details_response is None:
        print("Failed to verify updated user details.")
        return
    assert "updated.test.user@example.com" in verify_updated_user_details_response.text, \
        "Email not updated correctly after user details update."
    print("Verification of updated user details PASSED.")

    # --- 4. User Participation in Event (Optional, if you want to test further) ---
    # This part requires an existing event to participate in.
    # You might need to create a dummy event via admin API or manually for this test to pass.
    # For simplicity, let's assume event ID 1 exists.
    print("\n--- Testing User Participation in an Event ---")
    
    # First, try to get events to pick an ID
    events_data = get_events_response.json().get('events') if get_events_response else []
    if not events_data:
        print("No events found to participate in. Skipping participation test.")
    else:
        event_to_participate_id = events_data[0]['id'] # Take the first event found
        participation_payload = {
            "user_id": user_phone,
            "event_id": event_to_participate_id,
            "num_veg_attendees": 1,
            "num_non_veg_attendees": 0,
            "contribution_amount": 100
        }

        # Attempt to participate
        participate_response = run_test_case(
            "User Participate in Event (POST)",
            f"{APP_FRONTEND_URL}/api/participations",
            "POST",
            payload=participation_payload,
            expected_status=[200, 201, 409], # 409 if already participated
            expected_substring="success" # or relevant success message
        )
        if participate_response and participate_response.status_code == 409:
            print("User already participated, attempting to update participation.")
            # If 409, try PUT for payment update
            update_participation_payload = {
                "num_veg_attendees": 2,
                "num_non_veg_attendees": 0,
                "contribution_amount": 200
            }
            run_test_case(
                "User Update Participation (PUT)",
                f"{APP_FRONTEND_URL}/api/participations/{user_phone}/{event_to_participate_id}/payment",
                "PUT",
                payload=update_participation_payload,
                expected_status=200,
                expected_substring="Payment details updated" # Assuming this message
            )
        elif participate_response is None:
            print("Participation test failed.")

    print("\n======================================================")
    print("      All User Flow Tests Completed")
    print("======================================================")

if __name__ == "__main__":
    test_user_flow()