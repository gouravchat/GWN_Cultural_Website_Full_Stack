# test_app.py
import requests
import json
import time

# Base URL for your Flask application
BASE_URL = "http://127.0.0.1:5001"

def test_create_user_success():
    """
    Test Case P-001: Successful User Creation
    """
    print("\n--- Test Case P-001: Successful User Creation ---")
    url = f"{BASE_URL}/users"
    headers = {"Content-Type": "application/json"}
    payload = {
        "first_name": "Suparna",
        "middle_name": "Kumari",
        "last_name": "basak",
        "phone_number": "8972734567",
        "email_id": "basak.suparna@example.com",
        "password": "securepass123",
        "tower_number": "T2",
        "wing": "Left",
        "number": "11",
        "type_val": "Owner"
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 201
        assert "message" in response.json() and "user_id" in response.json()
        print("Test P-001 PASSED")
    except requests.exceptions.ConnectionError:
        print("Test P-001 FAILED: Could not connect to the Flask app. Is it running?")
    except AssertionError:
        print("Test P-001 FAILED: Unexpected status code or response content.")
    except Exception as e:
        print(f"Test P-001 FAILED: An unexpected error occurred - {e}")

def test_create_user_missing_field():
    """
    Test Case P-002: Missing Required Field (last_name)
    """
    print("\n--- Test Case P-002: Missing Required Field (last_name) ---")
    url = f"{BASE_URL}/users"
    headers = {"Content-Type": "application/json"}
    payload = {
        "first_name": "Jane",
        "phone_number": "0987654321",
        "email_id": "jane.smith@example.com",
        "password": "anotherpassword",
        "tower_number": "T2",
        "wing": "B",
        "number": "202",
        "type_val": "Tenant"
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 400
        assert "error" in response.json() and "Missing required fields" in response.json()["error"]
        print("Test P-002 PASSED")
    except requests.exceptions.ConnectionError:
        print("Test P-002 FAILED: Could not connect to the Flask app. Is it running?")
    except AssertionError:
        print("Test P-002 FAILED: Unexpected status code or response content.")
    except Exception as e:
        print(f"Test P-002 FAILED: An unexpected error occurred - {e}")

def test_create_user_duplicate_phone():
    """
    Test Case P-003: Duplicate Phone Number
    (Assumes P-001 has run and created user 1234567890)
    """
    print("\n--- Test Case P-003: Duplicate Phone Number ---")
    url = f"{BASE_URL}/users"
    headers = {"Content-Type": "application/json"}
    payload = {
        "first_name": "Peter",
        "last_name": "Jones",
        "phone_number": "1234567890", # This phone number already exists from P-001
        "email_id": "peter.jones@example.com",
        "password": "password456",
        "tower_number": "T3",
        "wing": "C",
        "number": "303",
        "type_val": "Owner"
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 409
        assert "error" in response.json() and "User with phone number 1234567890 already exists" in response.json()["error"]
        print("Test P-003 PASSED")
    except requests.exceptions.ConnectionError:
        print("Test P-003 FAILED: Could not connect to the Flask app. Is it running?")
    except AssertionError:
        print("Test P-003 FAILED: Unexpected status code or response content.")
    except Exception as e:
        print(f"Test P-003 FAILED: An unexpected error occurred - {e}")

def test_create_user_duplicate_email():
    """
    Test Case P-004: Duplicate Email ID
    (Assumes P-001 has run and created user john.doe@example.com)
    """
    print("\n--- Test Case P-004: Duplicate Email ID ---")
    url = f"{BASE_URL}/users"
    headers = {"Content-Type": "application/json"}
    payload = {
        "first_name": "Alice",
        "last_name": "Brown",
        "phone_number": "1122334455",
        "email_id": "john.doe@example.com", # This email already exists from P-001
        "password": "password789",
        "tower_number": "T4",
        "wing": "D",
        "number": "404",
        "type_val": "Tenant"
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 409
        assert "error" in response.json() and "User with email ID john.doe@example.com already exists" in response.json()["error"]
        print("Test P-004 PASSED")
    except requests.exceptions.ConnectionError:
        print("Test P-004 FAILED: Could not connect to the Flask app. Is it running?")
    except AssertionError:
        print("Test P-004 FAILED: Unexpected status code or response content.")
    except Exception as e:
        print(f"Test P-004 FAILED: An unexpected error occurred - {e}")

def test_create_user_empty_json():
    """
    Test Case P-005: Empty JSON Body
    """
    print("\n--- Test Case P-005: Empty JSON Body ---")
    url = f"{BASE_URL}/users"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, data=json.dumps({})) # Send an empty JSON object
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 400
        assert "error" in response.json() and "Missing required fields" in response.json()["error"] # Flask's get_json() might return None, leading to this specific error
        print("Test P-005 PASSED")
    except requests.exceptions.ConnectionError:
        print("Test P-005 FAILED: Could not connect to the Flask app. Is it running?")
    except AssertionError:
        print("Test P-005 FAILED: Unexpected status code or response content.")
    except Exception as e:
        print(f"Test P-005 FAILED: An unexpected error occurred - {e}")

def test_create_user_invalid_json_format():
    """
    Test Case P-006: Invalid JSON Format
    """
    print("\n--- Test Case P-006: Invalid JSON Format ---")
    url = f"{BASE_URL}/users"
    headers = {"Content-Type": "application/json"}
    invalid_json_data = '{ "first_name": "Test", "last_name": "User", ' # Malformed JSON
    try:
        response = requests.post(url, headers=headers, data=invalid_json_data)
        print(f"Status Code: {response.status_code}")
        # Note: Flask's error for invalid JSON might be a generic 400 with HTML or a specific JSON error.
        # We'll check for 400.
        assert response.status_code == 400
        print("Test P-006 PASSED (Expected 400 for invalid JSON)")
    except requests.exceptions.ConnectionError:
        print("Test P-006 FAILED: Could not connect to the Flask app. Is it running?")
    except AssertionError:
        print("Test P-006 FAILED: Unexpected status code.")
    except Exception as e:
        print(f"Test P-006 FAILED: An unexpected error occurred - {e}")

def test_create_user_optional_field():
    """
    Test Case P-007: Optional Field (middle_name) not provided
    """
    print("\n--- Test Case P-007: Optional Field (middle_name) not provided ---")
    url = f"{BASE_URL}/users"
    headers = {"Content-Type": "application/json"}
    payload = {
        "first_name": "NoMiddle",
        "last_name": "Name",
        "phone_number": "5551112222",
        "email_id": "nomiddle@example.com",
        "password": "nopassword",
        "tower_number": "T5",
        "wing": "E",
        "number": "505",
        "type_val": "Owner"
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 201
        assert "message" in response.json() and "user_id" in response.json()
        print("Test P-007 PASSED")
    except requests.exceptions.ConnectionError:
        print("Test P-007 FAILED: Could not connect to the Flask app. Is it running?")
    except AssertionError:
        print("Test P-007 FAILED: Unexpected status code or response content.")
    except Exception as e:
        print(f"Test P-007 FAILED: An unexpected error occurred - {e}")


def test_get_user_success():
    """
    Test Case G-001: Get user details by phone number (successful)
    (Assumes user 1234567890 exists from P-001)
    """
    print("\n--- Test Case G-001: Get user details by phone number (successful) ---")
    phone_number = "1234567890"
    url = f"{BASE_URL}/users/{phone_number}"
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200
        assert "phone_number" in response.json() and response.json()["phone_number"] == phone_number
        assert "password" not in response.json() # Ensure password is not exposed
        print("Test G-001 PASSED")
    except requests.exceptions.ConnectionError:
        print("Test G-001 FAILED: Could not connect to the Flask app. Is it running?")
    except AssertionError:
        print("Test G-001 FAILED: Unexpected status code or response content.")
    except Exception as e:
        print(f"Test G-001 FAILED: An unexpected error occurred - {e}")

def test_get_user_non_existent():
    """
    Test Case G-002: Get user details for a non-existent phone number
    """
    print("\n--- Test Case G-002: Get user details for a non-existent phone number ---")
    phone_number = "9999999999" # Should not exist
    url = f"{BASE_URL}/users/{phone_number}"
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 404
        assert "error" in response.json() and "User not found" in response.json()["error"]
        print("Test G-002 PASSED")
    except requests.exceptions.ConnectionError:
        print("Test G-002 FAILED: Could not connect to the Flask app. Is it running?")
    except AssertionError:
        print("Test G-002 FAILED: Unexpected status code or response content.")
    except Exception as e:
        print(f"Test G-002 FAILED: An unexpected error occurred - {e}")

def test_get_another_existing_user():
    """
    Test Case G-003: Get user details for another existing user (from P-007)
    (Assumes user 5551112222 exists from P-007)
    """
    print("\n--- Test Case G-003: Get user details for another existing user ---")
    phone_number = "5551112222"
    url = f"{BASE_URL}/users/{phone_number}"
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200
        assert "phone_number" in response.json() and response.json()["phone_number"] == phone_number
        print("Test G-003 PASSED")
    except requests.exceptions.ConnectionError:
        print("Test G-003 FAILED: Could not connect to the Flask app. Is it running?")
    except AssertionError:
        print("Test G-003 FAILED: Unexpected status code or response content.")
    except Exception as e:
        print(f"Test G-003 FAILED: An unexpected error occurred - {e}")

def test_get_all_users():
    """
    Test Case G-004: Get all user details
    (Assumes some users have been created by previous POST tests)
    """
    print("\n--- Test Case G-004: Get all user details ---")
    url = f"{BASE_URL}/users" # This now targets the new GET /users endpoint
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200
        assert isinstance(response.json(), list) # Expect a list of users
        # You can add more assertions here, e.g., check if the list is not empty
        # and if specific users created earlier are present.
        if response.json():
            print(f"Found {len(response.json())} users.")
            # Example: Check if a specific user is in the list
            found_john = any(user['phone_number'] == '1234567890' for user in response.json())
            assert found_john, "User John Doe (1234567890) not found in all users list."
        else:
            print("No users found in the database.")
        print("Test G-004 PASSED")
    except requests.exceptions.ConnectionError:
        print("Test G-004 FAILED: Could not connect to the Flask app. Is it running?")
    except AssertionError:
        print("Test G-004 FAILED: Unexpected status code or response content.")
    except Exception as e:
        print(f"Test G-004 FAILED: An unexpected error occurred - {e}")

def show_current_db_entries():
    """
    Utility function to fetch and display all current entries in the database.
    """
    print("\n--- Current Database Entries ---")
    url = f"{BASE_URL}/users"
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            users = response.json()
            if users:
                print(f"Total users found: {len(users)}")
                for i, user in enumerate(users):
                    print(f"  User {i+1}: {json.dumps(user, indent=2)}")
            else:
                print("No entries currently in the database.")
        else:
            print(f"Failed to retrieve entries: {response.json()}")
    except requests.exceptions.ConnectionError:
        print("Could not connect to the Flask app. Is it running?")
    except Exception as e:
        print(f"An error occurred while fetching entries: {e}")


def main():
    print("Starting API tests...")
    # It's good practice to ensure the app is running before testing.
    # You might want to add a small delay or a retry mechanism here.
    # For now, assume the Flask app is already started.

    # Run POST tests
    test_create_user_success()
    test_create_user_missing_field()
    test_create_user_duplicate_phone()
    test_create_user_duplicate_email()
    test_create_user_empty_json()
    test_create_user_invalid_json_format()
    test_create_user_optional_field()

    # Give a small delay to ensure database operations are complete before GET requests
    time.sleep(1)

    # Run GET tests
    test_get_user_success()
    test_get_user_non_existent()
    test_get_another_existing_user()
    test_get_all_users() # Call the new test case

    # Show current database entries after all tests
    show_current_db_entries()

    print("\nAll API tests completed.")

if __name__ == "__main__":
    main()
