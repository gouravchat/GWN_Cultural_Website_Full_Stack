import unittest
import json
import os
from datetime import datetime, timedelta
from app import app, db, Event # Import app, db, and Event from your app.py

class EventServiceTestCase(unittest.TestCase):

    def setUp(self):
        """Set up test environment before each test."""
        app.config['TESTING'] = True
        # Use a temporary in-memory SQLite database for testing
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        with app.app_context():
            db.create_all() # Create tables for the in-memory database

    def tearDown(self):
        """Clean up test environment after each test."""
        with app.app.context():
            db.session.remove()
            db.drop_all() # Drop all tables to ensure a clean slate for the next test

    # Test for creating an event
    def test_create_event_success(self):
        """Test creating a new event successfully."""
        event_data = {
            "name": "Tech Meetup",
            "details": "A monthly gathering for tech enthusiasts.",
            # Ensure time and close_date are in a format parsable by fromisoformat if needed in backend
            "time": (datetime.utcnow() + timedelta(days=30)).isoformat(timespec='minutes'),
            "close_date": (datetime.utcnow() + timedelta(days=15)).isoformat(timespec='minutes'),
            "venue": "Innovation Hub",
            "coverCharges": 10.50,
            "coverChargesType": "per_head"
        }
        response = self.app.post('/events',
                                 data=json.dumps(event_data),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn("Event created successfully", data["message"])
        self.assertEqual(data["event"]["name"], "Tech Meetup")

    def test_create_event_missing_required_field(self):
        """Test creating an event with a missing required field (e.g., 'name')."""
        event_data = {
            # "name": "Missing Name Event", # Name is intentionally missing
            "details": "Details for missing name event.",
            "time": (datetime.utcnow() + timedelta(days=30)).isoformat(timespec='minutes'),
            "close_date": (datetime.utcnow() + timedelta(days=15)).isoformat(timespec='minutes'),
            "venue": "Test Venue",
            "coverCharges": 0.0,
            "coverChargesType": "per_head"
        }
        response = self.app.post('/events',
                                 data=json.dumps(event_data),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("Missing required field: name", data["error"])

    def test_create_event_invalid_charge_type(self):
        """Test creating an event with an invalid coverChargesType."""
        event_data = {
            "name": "Bad Charge Type",
            "details": "Details.",
            "time": (datetime.utcnow() + timedelta(days=30)).isoformat(timespec='minutes'),
            "close_date": (datetime.utcnow() + timedelta(days=15)).isoformat(timespec='minutes'),
            "venue": "Venue",
            "coverCharges": 10.0,
            "coverChargesType": "per_dog" # Invalid type
        }
        response = self.app.post('/events',
                                 data=json.dumps(event_data),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("Invalid value for 'coverChargesType'.", data["error"])

    # Test for getting all events
    def test_get_all_events_empty(self):
        """Test getting all events when no events exist."""
        response = self.app.get('/events')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data, []) # Expect an empty list

    def test_get_all_events_with_data(self):
        """Test getting all events when events exist."""
        with app.app_context():
            event1 = Event(
                name="Conference",
                time_str=(datetime.utcnow() + timedelta(days=10)).isoformat(timespec='minutes'),
                close_date_str=(datetime.utcnow() + timedelta(days=5)).isoformat(timespec='minutes'),
                venue="Convention Center",
                details="Annual tech conference."
            )
            event2 = Event(
                name="Workshop",
                time_str=(datetime.utcnow() + timedelta(days=20)).isoformat(timespec='minutes'),
                close_date_str=(datetime.utcnow() + timedelta(days=10)).isoformat(timespec='minutes'),
                venue="Training Room",
                details="Hands-on coding workshop."
            )
            db.session.add_all([event1, event2])
            db.session.commit()

        response = self.app.get('/events')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["name"], "Conference")
        self.assertEqual(data[1]["name"], "Workshop")

    def test_expired_events_are_removed_on_get_all(self):
        """Test that expired events are removed before getting all events."""
        with app.app_context():
            # Create an active event
            active_event = Event(
                name="Active Event",
                time_str=(datetime.utcnow() + timedelta(days=10)).isoformat(timespec='minutes'),
                close_date_str=(datetime.utcnow() + timedelta(days=5)).isoformat(timespec='minutes'),
                venue="Active Venue",
                details="Active details."
            )
            db.session.add(active_event)

            # Create an expired event (close_date is in the past)
            expired_event = Event(
                name="Expired Event",
                time_str=(datetime.utcnow() - timedelta(days=5)).isoformat(timespec='minutes'),
                close_date_str=(datetime.utcnow() - timedelta(days=1)).isoformat(timespec='minutes'),
                venue="Expired Venue",
                details="Expired details."
            )
            db.session.add(expired_event)
            db.session.commit()

        response = self.app.get('/events')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1) # Only the active event should remain
        self.assertEqual(data[0]["name"], "Active Event")

        # Verify that the expired event is truly removed from the DB
        with app.app_context():
            remaining_events = Event.query.all()
            self.assertEqual(len(remaining_events), 1)
            self.assertEqual(remaining_events[0].name, "Active Event")

    # Test for the root route (index.html)
    def test_root_route_serves_html(self):
        """Test that the root route '/' serves the index.html content."""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<!DOCTYPE html>", response.data) # Check for HTML doctype
        self.assertIn(b"<h1>Event Management System</h1>", response.data) # Check for a specific tag

    # Test for static file serving
    def test_serve_static_css(self):
        """Test serving a static CSS file."""
        # Create a dummy static CSS file for testing
        static_folder = app.root_path + '/static' # Get the full path to the static folder
        os.makedirs(static_folder, exist_ok=True)
        dummy_css_path = os.path.join(static_folder, 'test_style.css')
        with open(dummy_css_path, 'w') as f:
            f.write('body { background-color: #f0f0f0; }')

        response = self.app.get('/static/test_style.css')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'body { background-color: #f0f0f0; }')
        self.assertEqual(response.content_type, 'text/css')

        # Clean up the dummy file
        os.remove(dummy_css_path)


if __name__ == '__main__':
    unittest.main()