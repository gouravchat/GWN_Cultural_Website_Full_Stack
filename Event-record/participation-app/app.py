import logging
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import os
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

app = Flask(__name__)
CORS(app)

# Ensure the data directory exists
db_folder = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(db_folder, exist_ok=True)
db_path = os.path.join(db_folder, 'participation.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Participation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    user_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    email_id = db.Column(db.String(120), nullable=True)
    event_id = db.Column(db.Integer, nullable=False, index=True)
    event_date = db.Column(db.Date, nullable=True)
    tower = db.Column(db.String(50), nullable=False)
    flat_no = db.Column(db.String(50), nullable=False)
    total_payable = db.Column(db.Float, nullable=False, default=0.0)
    amount_paid = db.Column(db.Float, nullable=False, default=0.0)
    payment_remaining = db.Column(db.Float, nullable=False, default=0.0)
    additional_contribution = db.Column(db.Float, default=0.0)
    contribution_comments = db.Column(db.Text, nullable=True)
    veg_heads = db.Column(db.Integer, default=0)
    non_veg_heads = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='confirmed', nullable=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

@app.route('/participation', methods=['GET'])
def get_participations():
    logging.info("Fetching all participation records.")
    participations = Participation.query.all()
    return jsonify([
        {
            'id': p.id,
            'user_id': p.user_id,
            'user_name': p.user_name,
            'phone_number': p.phone_number,
            'email_id': p.email_id,
            'event_id': p.event_id,
            'event_date': p.event_date.isoformat() if p.event_date else None,
            'tower': p.tower,
            'flat_no': p.flat_no,
            'total_payable': p.total_payable,
            'amount_paid': p.amount_paid,
            'payment_remaining': p.payment_remaining,
            'additional_contribution': p.additional_contribution,
            'contribution_comments': p.contribution_comments,
            'veg_heads': p.veg_heads,
            'non_veg_heads': p.non_veg_heads,
            'status': p.status,
            'registered_at': p.registered_at.isoformat() if p.registered_at else None,
            'updated_at': p.updated_at.isoformat() if p.updated_at else None
        } for p in participations
    ])

@app.route('/participation/<int:participation_id>', methods=['GET'])
def get_participation(participation_id):
    logging.info(f"Fetching participation record with id={participation_id}")
    participation = Participation.query.get(participation_id)
    if participation is None:
        logging.warning(f"Participation record with id={participation_id} not found.")
        return jsonify({'error': 'Participation not found'}), 404
    return jsonify({
        'id': participation.id,
        'user_id': participation.user_id,
        'user_name': participation.user_name,
        'phone_number': participation.phone_number,
        'email_id': participation.email_id,
        'event_id': participation.event_id,
        'event_date': participation.event_date.isoformat() if participation.event_date else None,
        'tower': participation.tower,
        'flat_no': participation.flat_no,
        'total_payable': participation.total_payable,
        'amount_paid': participation.amount_paid,
        'payment_remaining': participation.payment_remaining,
        'additional_contribution': participation.additional_contribution,
        'contribution_comments': participation.contribution_comments,
        'veg_heads': participation.veg_heads,
        'non_veg_heads': participation.non_veg_heads,
        'status': participation.status,
        'registered_at': participation.registered_at.isoformat() if participation.registered_at else None,
        'updated_at': participation.updated_at.isoformat() if participation.updated_at else None
    })

@app.route('/participation', methods=['POST'])
def create_participation():
    data = request.get_json()
    logging.info(f"Received request to create participation: {data}")
    user_id = data.get('user_id')
    user_name = data.get('user_name')
    phone_number = data.get('phone_number')
    email_id = data.get('email_id')
    event_id = data.get('event_id')
    event_date = data.get('event_date')
    tower = data.get('tower')
    flat_no = data.get('flat_no')
    total_payable = data.get('total_payable', 0.0)
    amount_paid = data.get('amount_paid', 0.0)
    payment_remaining = data.get('payment_remaining', 0.0)
    additional_contribution = data.get('additional_contribution', 0.0)
    contribution_comments = data.get('contribution_comments', '')
    veg_heads = data.get('veg_heads', 0)
    non_veg_heads = data.get('non_veg_heads', 0)
    status = data.get('status', 'confirmed')

    if not user_id or not user_name or not event_id or not tower or not flat_no:
        logging.error("Missing required fields in participation creation.")
        return jsonify({'error': 'Missing required fields'}), 400

    if event_date:
        try:
            event_date = datetime.strptime(event_date, '%Y-%m-%d').date()
        except ValueError:
            logging.error("Invalid date format for event_date.")
            return jsonify({'error': 'Invalid date format, should be YYYY-MM-DD'}), 400
    else:
        event_date = None

    new_participation = Participation(
        user_id=user_id,
        user_name=user_name,
        phone_number=phone_number,
        email_id=email_id,
        event_id=event_id,
        event_date=event_date,
        tower=tower,
        flat_no=flat_no,
        total_payable=total_payable,
        amount_paid=amount_paid,
        payment_remaining=payment_remaining,
        additional_contribution=additional_contribution,
        contribution_comments=contribution_comments,
        veg_heads=veg_heads,
        non_veg_heads=non_veg_heads,
        status=status
    )
    db.session.add(new_participation)
    db.session.commit()
    logging.info(f"Created participation record with id={new_participation.id}")
    return jsonify({
        'id': new_participation.id,
        'user_id': user_id,
        'user_name': user_name,
        'phone_number': phone_number,
        'email_id': email_id,
        'event_id': event_id,
        'event_date': event_date.isoformat() if event_date else None,
        'tower': tower,
        'flat_no': flat_no,
        'total_payable': total_payable,
        'amount_paid': amount_paid,
        'payment_remaining': payment_remaining,
        'additional_contribution': additional_contribution,
        'contribution_comments': contribution_comments,
        'veg_heads': veg_heads,
        'non_veg_heads': non_veg_heads,
        'status': status
    }), 201

@app.route('/participation/<int:participation_id>', methods=['PUT'])
def update_participation(participation_id):
    data = request.get_json()
    logging.info(f"Received request to update participation id={participation_id}: {data}")
    participation = Participation.query.get(participation_id)
    if participation is None:
        logging.warning(f"Participation record with id={participation_id} not found for update.")
        return jsonify({'error': 'Participation not found'}), 404

    participation.user_id = data.get('user_id', participation.user_id)
    participation.user_name = data.get('user_name', participation.user_name)
    participation.phone_number = data.get('phone_number', participation.phone_number)
    participation.email_id = data.get('email_id', participation.email_id)
    participation.event_id = data.get('event_id', participation.event_id)
    participation.tower = data.get('tower', participation.tower)
    participation.flat_no = data.get('flat_no', participation.flat_no)
    participation.total_payable = data.get('total_payable', participation.total_payable)
    participation.amount_paid = data.get('amount_paid', participation.amount_paid)
    participation.payment_remaining = data.get('payment_remaining', participation.payment_remaining)
    participation.additional_contribution = data.get('additional_contribution', participation.additional_contribution)
    participation.contribution_comments = data.get('contribution_comments', participation.contribution_comments)
    participation.veg_heads = data.get('veg_heads', participation.veg_heads)
    participation.non_veg_heads = data.get('non_veg_heads', participation.non_veg_heads)
    participation.status = data.get('status', participation.status)

    event_date = data.get('event_date', None)
    if event_date and isinstance(event_date, str):
        try:
            event_date = datetime.strptime(event_date, '%Y-%m-%d').date()
            participation.event_date = event_date
        except ValueError:
            logging.error("Invalid date format for event_date in update.")
            return jsonify({'error': 'Invalid date format for event_date, should be YYYY-MM-DD'}), 400

    db.session.commit()
    logging.info(f"Updated participation record with id={participation.id}")
    return jsonify({
        'id': participation.id,
        'user_id': participation.user_id,
        'user_name': participation.user_name,
        'phone_number': participation.phone_number,
        'email_id': participation.email_id,
        'event_id': participation.event_id,
        'event_date': participation.event_date.isoformat() if participation.event_date else None,
        'tower': participation.tower,
        'flat_no': participation.flat_no,
        'total_payable': participation.total_payable,
        'amount_paid': participation.amount_paid,
        'payment_remaining': participation.payment_remaining,
        'additional_contribution': participation.additional_contribution,
        'contribution_comments': participation.contribution_comments,
        'veg_heads': participation.veg_heads,
        'non_veg_heads': participation.non_veg_heads,
        'status': participation.status
    })

@app.route('/participation/<int:participation_id>', methods=['DELETE'])
def delete_participation(participation_id):
    logging.info(f"Received request to delete participation id={participation_id}")
    participation = Participation.query.get(participation_id)
    if participation is None:
        logging.warning(f"Participation record with id={participation_id} not found for deletion.")
        return jsonify({'error': 'Participation not found'}), 404
    db.session.delete(participation)
    db.session.commit()
    logging.info(f"Deleted participation record with id={participation_id}")
    return jsonify({'message': 'Participation deleted'})

@app.route('/participation/user/<int:user_id>', methods=['GET'])
def get_participations_by_user(user_id):
    logging.info(f"Fetching participation records for user_id={user_id}")
    participations = Participation.query.filter_by(user_id=user_id).all()
    if not participations:
        logging.warning(f"No participation records found for user_id={user_id}")
        return jsonify({'error': 'No participation records found for this user_id'}), 404
    return jsonify([
        {
            'id': p.id,
            'user_id': p.user_id,
            'user_name': p.user_name,
            'phone_number': p.phone_number,
            'email_id': p.email_id,
            'event_id': p.event_id,
            'event_date': p.event_date.isoformat() if p.event_date else None,
            'tower': p.tower,
            'flat_no': p.flat_no,
            'total_payable': p.total_payable,
            'amount_paid': p.amount_paid,
            'payment_remaining': p.payment_remaining,
            'additional_contribution': p.additional_contribution,
            'contribution_comments': p.contribution_comments,
            'veg_heads': p.veg_heads,
            'non_veg_heads': p.non_veg_heads,
            'status': p.status,
            'registered_at': p.registered_at.isoformat() if p.registered_at else None,
            'updated_at': p.updated_at.isoformat() if p.updated_at else None
        } for p in participations
    ])

@app.route('/participation/event/<int:event_id>', methods=['GET'])
def get_participations_by_event(event_id):
    logging.info(f"Fetching participation records for event_id={event_id}")
    participations = Participation.query.filter_by(event_id=event_id).all()
    if not participations:
        logging.warning(f"No participation records found for event_id={event_id}")
        return jsonify({'error': 'No participation records found for this event_id'}), 404
    return jsonify([
        {
            'id': p.id,
            'user_id': p.user_id,
            'user_name': p.user_name,
            'phone_number': p.phone_number,
            'email_id': p.email_id,
            'event_id': p.event_id,
            'event_date': p.event_date.isoformat() if p.event_date else None,
            'tower': p.tower,
            'flat_no': p.flat_no,
            'total_payable': p.total_payable,
            'amount_paid': p.amount_paid,
            'payment_remaining': p.payment_remaining,
            'additional_contribution': p.additional_contribution,
            'contribution_comments': p.contribution_comments,
            'veg_heads': p.veg_heads,
            'non_veg_heads': p.non_veg_heads,
            'status': p.status,
            'registered_at': p.registered_at.isoformat() if p.registered_at else None,
            'updated_at': p.updated_at.isoformat() if p.updated_at else None
        } for p in participations
    ])

if __name__ == '__main__':
    logging.info("Creating database tables if not exist.")
    with app.app_context():
        db.create_all()
    logging.info("Starting Flask app on port 5005")
    app.run(debug=True, port=5005)

# list out all the endpoints here

# 1. `GET /participation` - Fetch all participation records
# 2. `GET /participation/<int:participation_id>` - Fetch a specific participation record by ID
# 3. `POST /participation` - Create a new participation record
# 4. `PUT /participation/<int:participation_id>` - Update a specific participation record by ID
# 5. `DELETE /participation/<int:participation_id>` - Delete a specific participation record by ID
# 6. `GET /participation/user/<int:user_id>` - Fetch participation records for a specific user by user ID
# 7. `GET /participation/event/<int:event_id>` - Fetch participation records