import os
import logging
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError, OperationalError
from datetime import datetime, date

# --- Basic Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(name)s:%(message)s')

# Rename 'app' to 'participation_service_app' for clarity
participation_service_app = Flask(__name__)

# --- Configuration ---
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')
if not os.path.exists(db_path):
    participation_service_app.logger.info(f"Creating data directory at: {db_path}")
    os.makedirs(db_path)

db_file_path = os.path.join(db_path, 'participant_records.db') # Renamed DB file
participation_service_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_file_path
participation_service_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Rename 'db' to 'database' for clarity
database = SQLAlchemy(participation_service_app)

# --- Database Model ---
# Renamed 'Participation' model to 'ParticipantInfo'
class ParticipantInfo(database.Model):
    # Renamed table name from 'participations' to 'participant_records'
    __tablename__ = 'participant_records'
    
    id = database.Column(database.Integer, primary_key=True)
    user_id = database.Column(database.Integer, nullable=False, index=True)
    user_name = database.Column(database.String(100), nullable=False)
    phone_number = database.Column(database.String(20), nullable=True)
    email_id = database.Column(database.String(120), nullable=True)
    event_id = database.Column(database.Integer, nullable=False, index=True)
    event_date = database.Column(database.Date, nullable=True)
    flat_detail = database.Column(database.String(100), nullable=False)
    tower_number = database.Column(database.String(50), nullable=False)
    wing = database.Column(database.String(50), nullable=True)
    flat_type = database.Column(database.String(10), nullable=True)
    floor_number = database.Column(database.Integer, nullable=False)
    cover_charge_paid = database.Column(database.Float, nullable=False, default=0.0)
    additional_contribution = database.Column(database.Float, default=0.0)
    payment_remaining = database.Column(database.Float, nullable=False, default=0.0)
    veg_heads = database.Column(database.Integer, default=0)
    non_veg_heads = database.Column(database.Integer, default=0)
    status = database.Column(database.String(50), default='confirmed', nullable=False)
    registered_at = database.Column(database.DateTime, default=datetime.utcnow)
    updated_at = database.Column(database.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (database.UniqueConstraint('event_id', 'flat_detail', name='uq_event_flat_participation'),)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'phone_number': self.phone_number,
            'email_id': self.email_id,
            'event_id': self.event_id,
            'event_date': self.event_date.isoformat() if self.event_date else None,
            'flat_detail': self.flat_detail,
            'tower_number': self.tower_number,
            'wing': self.wing,
            'flat_type': self.flat_type,
            'floor_number': self.floor_number,
            'cover_charge_paid': self.cover_charge_paid,
            'additional_contribution': self.additional_contribution,
            'payment_remaining': self.payment_remaining,
            'veg_heads': self.veg_heads,
            'non_veg_heads': self.non_veg_heads,
            'status': self.status,
            'registered_at': self.registered_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

# --- API Endpoints with Robust Error Handling ---
# Renamed endpoint to be more explicit, though '/participations' is also fine RESTfully.
@participation_service_app.route('/participant-records', methods=['POST'])
def create_participant_record():
    participation_service_app.logger.info("Received request for POST /participant-records")
    request_payload = request.get_json()
    if not request_payload:
        return jsonify({"error": "No input data provided"}), 400

    required_fields = ['user_id', 'user_name', 'event_id', 'tower_number', 'floor_number']
    missing_fields = [field for field in required_fields if field not in request_payload or request_payload[field] is None]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    tower = request_payload['tower_number']
    wing = request_payload.get('wing', 'NA')
    flat_type = request_payload.get('flat_type', 'N/A')
    floor = request_payload['floor_number']
    flat_detail_str = f"{tower}-{wing}-{flat_type}-{floor}"

    event_date_str = request_payload.get('event_date')
    parsed_event_date = None
    if event_date_str:
        try:
            parsed_event_date = date.fromisoformat(event_date_str)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid event_date format. Use YYYY-MM-DD."}), 400
            
    try:
        participation_service_app.logger.info("Attempting to create new ParticipantInfo object")
        new_record = ParticipantInfo(
            user_id=request_payload['user_id'], user_name=request_payload['user_name'],
            phone_number=request_payload.get('phone_number'), email_id=request_payload.get('email_id'),
            event_id=request_payload['event_id'], event_date=parsed_event_date,
            flat_detail=flat_detail_str, tower_number=request_payload['tower_number'],
            wing=wing, flat_type=flat_type, floor_number=request_payload['floor_number'],
            cover_charge_paid=float(request_payload.get('cover_charge_paid', 0.0)),
            additional_contribution=float(request_payload.get('additional_contribution', 0.0)),
            payment_remaining=float(request_payload.get('payment_remaining', 0.0)),
            veg_heads=int(request_payload.get('veg_heads', 0)), non_veg_heads=int(request_payload.get('non_veg_heads', 0)),
            status=request_payload.get('status', 'confirmed')
        )
        database.session.add(new_record)
        database.session.commit()
        participation_service_app.logger.info(f"Successfully created participant record with ID: {new_record.id}")
        return jsonify({"message": "Participant record created successfully", "participant_info": new_record.to_dict()}), 201
    except IntegrityError as e:
        database.session.rollback()
        if 'uq_event_flat_participation' in str(e.orig):
             return jsonify({"error": "This flat is already registered for this event."}), 409
        participation_service_app.logger.error(f"Database integrity error: {e}")
        return jsonify({"error": "Database error: Could not save record due to a conflict.", "details": str(e)}), 400
    except Exception as e:
        database.session.rollback()
        participation_service_app.logger.error(f"Unhandled error creating participant record: {e}")
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500

@participation_service_app.route('/users/<int:user_id>/participant-records', methods=['GET'])
def get_records_by_user(user_id):
    participation_service_app.logger.info(f"Received request for GET /users/{user_id}/participant-records")
    try:
        participant_records = ParticipantInfo.query.filter_by(user_id=user_id).order_by(ParticipantInfo.event_date.desc(), ParticipantInfo.registered_at.desc()).all()
        participation_service_app.logger.info(f"Query successful, found {len(participant_records)} records for user {user_id}.")
        return jsonify([p.to_dict() for p in participant_records]), 200
    except Exception as e:
        participation_service_app.logger.error(f"Database error on GET /users/{user_id}/participant-records: {e}")
        return jsonify({"error": "A database error occurred.", "details": str(e)}), 500

@participation_service_app.route('/events/<int:event_id>/participant-records', methods=['GET'])
def get_records_by_event(event_id):
    participation_service_app.logger.info(f"Received request for GET /events/{event_id}/participant-records")
    try:
        participant_records = ParticipantInfo.query.filter_by(event_id=event_id).order_by(ParticipantInfo.tower_number, ParticipantInfo.floor_number, ParticipantInfo.flat_type).all()
        participation_service_app.logger.info(f"Query successful, found {len(participant_records)} records for event {event_id}.")
        return jsonify([p.to_dict() for p in participant_records]), 200
    except Exception as e:
        participation_service_app.logger.error(f"Database error on GET /events/{event_id}/participant-records: {e}")
        return jsonify({"error": "A database error occurred.", "details": str(e)}), 500

@participation_service_app.route('/participant-records/<int:record_id>', methods=['GET'])
def get_record_by_id(record_id):
    participation_service_app.logger.info(f"Received request for GET /participant-records/{record_id}")
    try:
        participant_record = ParticipantInfo.query.get(record_id)
        if not participant_record:
            return jsonify({"error": "Participant record not found"}), 404
        return jsonify(participant_record.to_dict()), 200
    except Exception as e:
        participation_service_app.logger.error(f"Database error on GET /participant-records/{record_id}: {e}")
        return jsonify({"error": "A database error occurred.", "details": str(e)}), 500

@participation_service_app.route('/participant-records/<int:record_id>', methods=['PUT'])
def update_record(record_id):
    participation_service_app.logger.info(f"Received request for PUT /participant-records/{record_id}")
    try:
        participant_record = ParticipantInfo.query.get(record_id)
        if not participant_record:
            return jsonify({"error": "Participant record not found"}), 404
        
        request_payload = request.get_json()
        if not request_payload:
            return jsonify({"error": "No update data provided"}), 400

        for key, value in request_payload.items():
            if hasattr(participant_record, key) and key not in ['id', 'user_id', 'event_id', 'registered_at', 'flat_detail']:
                if value is not None:
                    if key == 'event_date':
                        setattr(participant_record, key, date.fromisoformat(value))
                    elif key in ['cover_charge_paid', 'additional_contribution', 'payment_remaining']:
                        setattr(participant_record, key, float(value))
                    elif key in ['veg_heads', 'non_veg_heads', 'floor_number']:
                        setattr(participant_record, key, int(value))
                    else:
                        setattr(participant_record, key, value)
        
        participant_record.updated_at = datetime.utcnow()
        database.session.commit()
        participation_service_app.logger.info(f"Successfully updated record ID: {record_id}")
        return jsonify({"message": "Participant record updated successfully", "participant_info": participant_record.to_dict()}), 200
    except ValueError as e:
        database.session.rollback()
        return jsonify({"error": "Invalid data format for one or more fields.", "details": str(e)}), 400
    except Exception as e:
        database.session.rollback()
        participation_service_app.logger.error(f"Error updating record {record_id}: {e}")
        return jsonify({"error": "An internal server error occurred during update.", "details": str(e)}), 500

@participation_service_app.route('/participant-records/<int:record_id>', methods=['DELETE'])
def delete_record(record_id):
    participation_service_app.logger.info(f"Received request for DELETE /participant-records/{record_id}")
    try:
        participant_record = ParticipantInfo.query.get(record_id)
        if not participant_record:
            return jsonify({"error": "Participant record not found"}), 404
        
        database.session.delete(participant_record)
        database.session.commit()
        participation_service_app.logger.info(f"Successfully deleted record ID: {record_id}")
        return jsonify({"message": "Participant record deleted successfully"}), 200
    except Exception as e:
        database.session.rollback()
        participation_service_app.logger.error(f"Error deleting record {record_id}: {e}")
        return jsonify({"error": "An internal server error occurred during deletion.", "details": str(e)}), 500

@participation_service_app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "ParticipationService"}), 200

# --- Database Initialization ---
def initialize_database():
    with participation_service_app.app_context():
        try:
            participation_service_app.logger.info(f"Initializing database at: {participation_service_app.config['SQLALCHEMY_DATABASE_URI']}")
            database.create_all()
            participation_service_app.logger.info("Participation Service database tables created/ensured.")
        except OperationalError as e:
            participation_service_app.logger.error(f"CRITICAL: Could not connect to or create database. Check path and permissions. Error: {e}")
        except Exception as e:
            participation_service_app.logger.error(f"CRITICAL: An unexpected error occurred during database initialization: {e}")

if __name__ == '__main__':
    initialize_database()
    participation_service_app.run(host='0.0.0.0', port=os.environ.get('PORT', 5005), debug=True)
