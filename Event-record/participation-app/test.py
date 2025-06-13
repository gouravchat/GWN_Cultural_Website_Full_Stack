import unittest
import json
from app import app, db, Participation

class ParticipationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_create_participation(self):
        payload = {
            "user_id": 1,
            "user_name": "Test User",
            "phone_number": "1234567890",
            "email_id": "test@example.com",
            "event_id": 101,
            "event_date": "2024-06-10",
            "tower": "A",
            "flat_no": "101",
            "total_payable": 100.0,
            "amount_paid": 50.0,
            "payment_remaining": 50.0,
            "additional_contribution": 10.0,
            "contribution_comments": "Test comment",
            "veg_heads": 2,
            "non_veg_heads": 1,
            "status": "confirmed"
        }
        response = self.app.post('/participation', data=json.dumps(payload), content_type='application/json')
        try:
            self.assertEqual(response.status_code, 201)
            data = json.loads(response.data)
            self.assertEqual(data['user_name'], "Test User")
            print("test_create_participation: PASSED")
        except AssertionError as e:
            print("test_create_participation: FAILED")
            raise e

    def test_get_participations(self):
        self.test_create_participation()
        response = self.app.get('/participation')
        try:
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(isinstance(data, list))
            self.assertGreaterEqual(len(data), 1)
            print("test_get_participations: PASSED")
        except AssertionError as e:
            print("test_get_participations: FAILED")
            raise e

    def test_get_participation(self):
        self.test_create_participation()
        response = self.app.get('/participation/1')
        try:
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['user_id'], 1)
            print("test_get_participation: PASSED")
        except AssertionError as e:
            print("test_get_participation: FAILED")
            raise e

    def test_update_participation(self):
        self.test_create_participation()
        update_payload = {
            "user_name": "Updated User",
            "amount_paid": 100.0,
            "payment_remaining": 0.0
        }
        response = self.app.put('/participation/1', data=json.dumps(update_payload), content_type='application/json')
        try:
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['user_name'], "Updated User")
            self.assertEqual(data['amount_paid'], 100.0)
            self.assertEqual(data['payment_remaining'], 0.0)
            print("test_update_participation: PASSED")
        except AssertionError as e:
            print("test_update_participation: FAILED")
            raise e

    def test_delete_participation(self):
        self.test_create_participation()
        response = self.app.delete('/participation/1')
        try:
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['message'], "Participation deleted")
            # Confirm deletion
            response = self.app.get('/participation/1')
            self.assertEqual(response.status_code, 404)
            print("test_delete_participation: PASSED")
        except AssertionError as e:
            print("test_delete_participation: FAILED")
            raise e

    def test_get_participations_by_user(self):
        self.test_create_participation()
        response = self.app.get('/participation/user/1')
        try:
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(isinstance(data, list))
            self.assertGreaterEqual(len(data), 1)
            self.assertEqual(data[0]['user_id'], 1)
            print("test_get_participations_by_user: PASSED")
        except AssertionError as e:
            print("test_get_participations_by_user: FAILED")
            raise e

    def test_get_participations_by_event(self):
        self.test_create_participation()
        response = self.app.get('/participation/event/101')
        try:
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(isinstance(data, list))
            self.assertGreaterEqual(len(data), 1)
            self.assertEqual(data[0]['event_id'], 101)
            print("test_get_participations_by_event: PASSED")
        except AssertionError as e:
            print("test_get_participations_by_event: FAILED")
            raise e

if __name__ == '__main__':
    unittest.main()