import requests
import json
import unittest
import os

# The BASE_URL should point directly to your running Participation Service.
# This test bypasses Nginx to test the service in isolation.
BASE_URL = os.environ.get('PARTICIPATION_SERVICE_URL', 'http://localhost:5005')

# --- Global variable to store the ID of the record we create ---
created_record_id = None

class TestParticipationDB(unittest.TestCase):
    """
    A suite of tests focused specifically on the Participation DB service endpoints.
    """

    def test_1_health_check(self):
        """
        Tests the /health endpoint to ensure the service is running.
        """
        print("\n[TEST 1] Checking Service Health (/health)...")
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json().get('status'), 'healthy')
            print("SUCCESS: Health check passed.")
        except requests.ConnectionError as e:
            self.fail(f"Connection refused. Is the Participation Service running on port 5005? Error: {e}")

    def test_2_create_participation_record(self):
        """
        Tests creating a new record via the POST /participant-records endpoint.
        """
        print("\n[TEST 2] Creating a New Participation Record (POST /participant-records)...")
        global created_record_id

        # This payload mimics the structure sent by the ERS frontend.
        test_payload = {
            "eventId": 101,
            "userId": 123,
            "phoneNumber": "+919876543210",
            "email": "testuser@example.com",
            "totalAmount": 9000.00,
            "amountPaid": 8000.00,
            "remainingBalance": 1000.00,
            "registrationDetails": {
                "username": "testuser",
                "tower": "Alpine2 RW",
                "flatNo": "A-1501",
                "vegHeads": 1,
                "nonVegHeads": 1,
                "additionalContribution": 500.00,
                "contributionComments": "Unit test contribution"
            }
        }
        
        headers = {'Content-Type': 'application/json'}

        try:
            response = requests.post(
                f"{BASE_URL}/participant-records",
                headers=headers,
                data=json.dumps(test_payload),
                timeout=5
            )
            self.assertEqual(response.status_code, 201, f"Expected 201 (Created), but got {response.status_code}. Response: {response.text}")
            
            response_data = response.json()
            self.assertIn("participant_info", response_data)
            created_record_id = response_data['participant_info']['id']
            self.assertIsNotNone(created_record_id)
            
            print(f"SUCCESS: Record created with ID: {created_record_id}")
        except requests.ConnectionError as e:
            self.fail(f"Connection refused. Is the Participation Service running on port 5005? Error: {e}")

    def test_3_get_record_by_id(self):
        """
        Tests retrieving the newly created record by its ID.
        """
        print(f"\n[TEST 3] Fetching Record by ID (GET /participant-records/{created_record_id})...")
        self.assertIsNotNone(created_record_id, "Cannot run test: No record was created in the previous step.")
        
        try:
            response = requests.get(f"{BASE_URL}/participant-records/{created_record_id}", timeout=5)
            self.assertEqual(response.status_code, 200)
            
            record = response.json()
            self.assertEqual(record['id'], created_record_id)
            self.assertEqual(record['user_id'], 123)
            self.assertEqual(record['flat_no'], 'A-1501')
            print("SUCCESS: Record fetched correctly by ID.")
        except requests.ConnectionError as e:
            self.fail(f"Connection refused. Is the Participation Service running? Error: {e}")

    def test_4_get_records_by_user_id(self):
        """
        Tests retrieving records for a specific user.
        """
        print("\n[TEST 4] Fetching Records by User ID (GET /users/123/participant-records)...")
        try:
            response = requests.get(f"{BASE_URL}/users/123/participant-records", timeout=5)
            self.assertEqual(response.status_code, 200)
            
            records = response.json()
            self.assertIsInstance(records, list)
            self.assertGreater(len(records), 0, "Expected at least one record for user 123.")
            
            # Check if our created record is in the list
            found = any(r['id'] == created_record_id for r in records)
            self.assertTrue(found, f"Record with ID {created_record_id} not found in user's records.")
            print("SUCCESS: Records fetched correctly by User ID.")
        except requests.ConnectionError as e:
            self.fail(f"Connection refused. Is the Participation Service running? Error: {e}")

    def test_5_get_records_by_event_id(self):
        """
        Tests retrieving records for a specific event.
        """
        print("\n[TEST 5] Fetching Records by Event ID (GET /events/101/participant-records)...")
        try:
            response = requests.get(f"{BASE_URL}/events/101/participant-records", timeout=5)
            self.assertEqual(response.status_code, 200)
            
            records = response.json()
            self.assertIsInstance(records, list)
            self.assertGreater(len(records), 0, "Expected at least one record for event 101.")
            
            # Check if our created record is in the list
            found = any(r['id'] == created_record_id for r in records)
            self.assertTrue(found, f"Record with ID {created_record_id} not found in event's records.")
            print("SUCCESS: Records fetched correctly by Event ID.")
        except requests.ConnectionError as e:
            self.fail(f"Connection refused. Is the Participation Service running? Error: {e}")


if __name__ == '__main__':
    print("--- Starting Participation DB Service Endpoint Tests ---")
    # Using a test loader to run tests in a specific order
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestParticipationDB))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
