from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from disease_prediction import predictor
from datetime import datetime
import json
import numpy as np

app = Flask(__name__, template_folder="templates")
app.secret_key = 'supersecretkey'
socketio = SocketIO(app, cors_allowed_origins="*")

# MongoDB setup
client = MongoClient("mongodb+srv://Arman:Motor9-Jumbo5-Antiquely7-Edition6-Undergrad7@snapdx.2ihkj4k.mongodb.net/?retryWrites=true&w=majority&appName=SnapDx")
db = client["snapdx"]
users_collection = db["users"]
patients_collection = db["patients"]
diagnoses_collection = db["diagnoses"]
messages_collection = db["messages"]


def build_room_id(doctor_email: str, patient_key: str) -> str:
    """Create a stable room id between doctor and patient.
    patient_key should be email if available, else phone, else patient_id string.
    """
    return f"{doctor_email.strip().lower()}__{patient_key.strip().lower()}"

@app.route('/')
def index():
    return render_template("landing.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        user = users_collection.find_one({"email": email, "role": role})

        if user and check_password_hash(user['password'], password):
            session['email'] = email
            session['role'] = role
            session['name'] = user.get('name', 'User')  # Get name from user data, default to 'User'
            if role == 'doctor':
                return redirect(url_for('doctor_home'))
            else:
                return redirect(url_for('paitent_chatbot'))
        else:
            flash('Invalid credentials or role mismatch')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        if users_collection.find_one({"email": email, "role": role}):
            flash('User already exists with this email and role.')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        users_collection.insert_one({
            "name": name,
            "email": email,
            "password": hashed_password,
            "role": role
        })
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/doctor/home")
def doctor_home():
    if 'email' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))
    user_name = session.get('name', 'Doctor')
    return render_template("doctor/home.html", user_name=user_name, user_email=session.get('email'))

@app.route("/doctor/about")
def doctor_about():
    if 'email' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))
    user_name = session.get('name', 'Doctor')
    return render_template("doctor/about.html", user_name=user_name, user_email=session.get('email'))

@app.route("/doctor/chat")
def doctor_chat():
    if 'email' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))
    user_name = session.get('name', 'Doctor')
    return render_template("doctor/chat.html", user_name=user_name, user_email=session.get('email'))

@app.route("/doctor/diagnose")
def doctor_diagnose():
    if 'email' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))
    user_name = session.get('name', 'Doctor')
    return render_template("doctor/diagnose.html", user_name=user_name, user_email=session.get('email'))

@app.route("/doctor/history")
def doctor_history():
    if 'email' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))
    user_name = session.get('name', 'Doctor')
    return render_template("doctor/history.html", user_name=user_name, user_email=session.get('email'))

@app.route("/doctor/working")
def doctor_working():
    if 'email' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))
    user_name = session.get('name', 'Doctor')
    return render_template("doctor/how_it_works.html", user_name=user_name, user_email=session.get('email'))

@app.route("/patient/chatbot")
def paitent_chatbot():
    return render_template("paitent/chatbot.html", user_email=session.get('email'))

@app.route("/patient/chat")
def paitent_chat():
    if 'email' not in session or session.get('role') != 'patient':
        return redirect(url_for('login'))
    user_name = session.get('name', 'Patient')
    return render_template("paitent/chat.html", user_name=user_name, user_email=session.get('email'))

def convert_numpy_types(obj):
    """Convert NumPy types to Python native types for MongoDB serialization"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj

@app.route("/api/diagnose", methods=['POST'])
def diagnose_disease():
    """Handle disease diagnosis request"""
    if 'email' not in session or session.get('role') != 'doctor':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        # Get form data
        data = request.get_json()
        
        # Extract patient information
        patient_name = data.get('patient_name')
        patient_age = data.get('patient_age')
        patient_gender = data.get('patient_gender')
        patient_phone = data.get('patient_phone')
        patient_email = data.get('patient_email')
        disease_type = data.get('disease_type')
        images = data.get('images', [])  # Base64 encoded images
        
        if not all([patient_name, patient_age, patient_gender, patient_phone, disease_type]):
            return jsonify({'success': False, 'error': 'Missing required patient information'})
        
        if not images:
            return jsonify({'success': False, 'error': 'No images provided'})
        
        # Save patient information
        patient_data = {
            'name': patient_name,
            'age': int(patient_age),
            'gender': patient_gender,
            'phone': patient_phone,
            'email': patient_email,
            'created_by': session['email'],
            'created_at': datetime.now()
        }
        
        patient_result = patients_collection.insert_one(patient_data)
        patient_id = patient_result.inserted_id
        
        # Perform disease prediction
        prediction_result = predictor.predict_multiple_images(images, disease_type)
        
        if not prediction_result['success']:
            return jsonify({'success': False, 'error': prediction_result['error']})
        
        # Convert NumPy types to Python native types
        prediction_result = convert_numpy_types(prediction_result)
        
        # Save diagnosis information
        diagnosis_data = {
            'patient_id': patient_id,
            'patient_name': patient_name,
            'patient_phone': patient_phone,  # Add patient phone to diagnosis
            'patient_email': patient_email,
            'disease_type': disease_type,
            'has_disease': prediction_result['has_disease'],
            'probability': prediction_result['probability'],
            'confidence_percentage': prediction_result['confidence_percentage'],
            'disease_name': prediction_result['disease_name'],
            'total_images': prediction_result['total_images'],
            'individual_results': prediction_result['individual_results'],
            'doctor_email': session['email'],
            'doctor_name': session.get('name', 'Doctor'),
            'created_at': datetime.now(),
            'report_id': f"SNAP{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        diagnosis_result = diagnoses_collection.insert_one(diagnosis_data)
        diagnosis_id = diagnosis_result.inserted_id
        
        # Prepare response
        response_data = {
            'success': True,
            'diagnosis_id': str(diagnosis_id),
            'patient_id': str(patient_id),
            'report_id': diagnosis_data['report_id'],
            'prediction': {
                'has_disease': prediction_result['has_disease'],
                'disease_name': prediction_result['disease_name'],
                'confidence_percentage': prediction_result['confidence_percentage'],
                'probability': prediction_result['probability']
            },
            'patient_info': {
                'name': patient_data['name'],
                'age': patient_data['age'],
                'gender': patient_data['gender'],
                'phone': patient_data['phone'],
                'email': patient_data.get('email'),
                'created_by': patient_data['created_by'],
                'created_at': patient_data['created_at'].isoformat()
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Diagnosis error: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route("/api/report/<report_id>", methods=['GET'])
def get_report_by_id(report_id):
    """Get diagnosis report by report ID for patient chatbot"""
    try:
        # Find diagnosis by report_id
        diagnosis = diagnoses_collection.find_one({'report_id': report_id})
        
        if not diagnosis:
            return jsonify({'success': False, 'error': 'Report not found'}), 404
        
        # Get patient information
        patient = patients_collection.find_one({'_id': diagnosis['patient_id']})
        
        if not patient:
            return jsonify({'success': False, 'error': 'Patient information not found'}), 404
        
        # Prepare response data
        report_data = {
            'success': True,
            'report_id': diagnosis['report_id'],
            'patientName': patient['name'],
            'patientAge': patient['age'],
            'patientGender': patient['gender'],
            'primaryDiagnosis': diagnosis['disease_name'],
            'confidence': diagnosis['confidence_percentage'],
            'severity': 'Moderate' if diagnosis['has_disease'] else 'Normal',
            'detectedConditions': [
                diagnosis['disease_name'] if diagnosis['has_disease'] else 'Normal findings'
            ],
            'keyFindings': [
                f"AI detected {diagnosis['disease_name']}" if diagnosis['has_disease'] else "No abnormalities detected"
            ],
            'treatmentSuggestions': [
                "Follow doctor's prescribed treatment plan",
                "Complete full course of medications",
                "Attend follow-up appointments",
                "Monitor symptoms regularly"
            ],
            'precautions': [
                "Take medications as prescribed",
                "Avoid strenuous activities if advised",
                "Maintain good hygiene",
                "Get adequate rest",
                "Stay hydrated"
            ],
            'medications': [
                {
                    'name': 'Prescribed medication',
                    'dosage': 'As per doctor\'s prescription',
                    'frequency': 'As directed',
                    'duration': 'Complete full course',
                    'instructions': 'Follow doctor\'s instructions'
                }
            ],
            'doctor_name': diagnosis.get('doctor_name', 'Doctor'),
            'created_at': diagnosis['created_at'].isoformat(),
            'disease_type': diagnosis['disease_type'],
            'has_disease': diagnosis['has_disease'],
            'probability': diagnosis['probability']
        }
        
        return jsonify(report_data)
        
    except Exception as e:
        print(f"Error fetching report: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route("/api/diagnoses", methods=['GET'])
def get_diagnoses():
    """Get all diagnoses for the logged-in doctor"""
    if 'email' not in session or session.get('role') != 'doctor':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        diagnoses = list(diagnoses_collection.find(
            {'doctor_email': session['email']}
        ).sort('created_at', -1))
        
        # Convert ObjectId to string for JSON serialization
        for diagnosis in diagnoses:
            diagnosis['_id'] = str(diagnosis['_id'])
            diagnosis['patient_id'] = str(diagnosis['patient_id'])
            diagnosis['created_at'] = diagnosis['created_at'].isoformat()
        
        return jsonify({'success': True, 'diagnoses': diagnoses})
        
    except Exception as e:
        print(f"Error fetching diagnoses: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route("/api/recent-patients", methods=['GET'])
def get_recent_patients():
    """Get recent patients for the logged-in doctor (last 5)"""
    if 'email' not in session or session.get('role') != 'doctor':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        # Get the 5 most recent diagnoses
        recent_diagnoses = list(diagnoses_collection.find(
            {'doctor_email': session['email']}
        ).sort('created_at', -1).limit(5))
        
        # Convert ObjectId to string for JSON serialization
        for diagnosis in recent_diagnoses:
            diagnosis['_id'] = str(diagnosis['_id'])
            diagnosis['patient_id'] = str(diagnosis['patient_id'])
            diagnosis['created_at'] = diagnosis['created_at'].isoformat()
        
        return jsonify({'success': True, 'patients': recent_diagnoses})
        
    except Exception as e:
        print(f"Error fetching recent patients: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route("/api/chat-patients", methods=['GET'])
def get_chat_patients():
    """Get unique patients for chat by mobile number - diagnosed by logged-in doctor"""
    if 'email' not in session or session.get('role') != 'doctor':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        doctor_email = session['email']
        print(f"Looking for patients for doctor: {doctor_email}")
        
        # Get all diagnoses for the logged-in doctor
        diagnoses = list(diagnoses_collection.find(
            {'doctor_email': doctor_email}
        ).sort('created_at', -1))
        
        print(f"Found {len(diagnoses)} diagnoses for doctor {doctor_email}")
        
        # Group by patient identifier to get unique patients
        unique_patients = {}
        for diagnosis in diagnoses:
            # Try multiple ways to identify the patient
            patient_key = None
            
            # First try patient_email from diagnosis
            if diagnosis.get('patient_email'):
                patient_key = diagnosis['patient_email']
            # Then try patient_phone from diagnosis
            elif diagnosis.get('patient_phone'):
                patient_key = diagnosis['patient_phone']
            # Finally use patient_id as fallback
            else:
                patient_key = f"patient_{str(diagnosis['patient_id'])}"
            
            if patient_key not in unique_patients:
                # Get patient details from patients collection
                patient = patients_collection.find_one({'_id': diagnosis['patient_id']})
                if patient:
                    unique_patients[patient_key] = {
                        'patient_id': str(patient['_id']),
                        'name': patient.get('name', 'Unknown Patient'),
                        'phone': patient.get('phone', diagnosis.get('patient_phone', '')),
                        'email': patient.get('email', diagnosis.get('patient_email', '')),
                        'age': patient.get('age', ''),
                        'gender': patient.get('gender', ''),
                        'last_diagnosis': diagnosis.get('disease_name', ''),
                        'last_diagnosis_date': diagnosis['created_at'].isoformat(),
                        'total_diagnoses': 1,
                        'has_disease': diagnosis.get('has_disease', False),
                        'confidence': diagnosis.get('confidence_percentage', 0),
                        'disease_type': diagnosis.get('disease_type', ''),
                        'doctor_name': diagnosis.get('doctor_name', ''),
                        'report_id': diagnosis.get('report_id', '')
                    }
                else:
                    # If patient not found, use diagnosis data
                    unique_patients[patient_key] = {
                        'patient_id': str(diagnosis['patient_id']),
                        'name': diagnosis.get('patient_name', 'Unknown Patient'),
                        'phone': diagnosis.get('patient_phone', ''),
                        'email': diagnosis.get('patient_email', ''),
                        'age': '',
                        'gender': '',
                        'last_diagnosis': diagnosis.get('disease_name', ''),
                        'last_diagnosis_date': diagnosis['created_at'].isoformat(),
                        'total_diagnoses': 1,
                        'has_disease': diagnosis.get('has_disease', False),
                        'confidence': diagnosis.get('confidence_percentage', 0),
                        'disease_type': diagnosis.get('disease_type', ''),
                        'doctor_name': diagnosis.get('doctor_name', ''),
                        'report_id': diagnosis.get('report_id', '')
                    }
            elif patient_key in unique_patients:
                # Increment diagnosis count for existing patient
                unique_patients[patient_key]['total_diagnoses'] += 1
                
                # Update with more recent diagnosis if this one is newer
                current_date = diagnosis['created_at']
                existing_date = datetime.fromisoformat(unique_patients[patient_key]['last_diagnosis_date'].replace('Z', '+00:00'))
                if current_date > existing_date:
                    unique_patients[patient_key].update({
                        'last_diagnosis': diagnosis.get('disease_name', ''),
                        'last_diagnosis_date': diagnosis['created_at'].isoformat(),
                        'has_disease': diagnosis.get('has_disease', False),
                        'confidence': diagnosis.get('confidence_percentage', 0),
                        'disease_type': diagnosis.get('disease_type', ''),
                        'report_id': diagnosis.get('report_id', '')
                    })
        
        # Convert to list and sort by last diagnosis date
        patients_list = list(unique_patients.values())
        patients_list.sort(key=lambda x: x['last_diagnosis_date'], reverse=True)
        
        print(f"Returning {len(patients_list)} unique patients for doctor {doctor_email}")
        
        return jsonify({'success': True, 'patients': patients_list})
        
    except Exception as e:
        print(f"Error fetching chat patients: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route("/api/chat-doctors", methods=['GET'])
def get_chat_doctors():
    """For patients: list doctors they have a diagnosis with, based on patient email in session."""
    if 'email' not in session or session.get('role') == 'doctor':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    try:
        patient_email = session['email']
        print(f"Looking for doctors for patient: {patient_email}")
        
        # First try to find diagnoses by patient_email
        diagnoses = list(diagnoses_collection.find({'patient_email': patient_email}).sort('created_at', -1))
        print(f"Found {len(diagnoses)} diagnoses by patient_email")
        
        # If no diagnoses found by email, try to find by patient record
        if not diagnoses:
            # Find patient record first
            patient = patients_collection.find_one({'email': patient_email})
            if patient:
                # Find diagnoses by patient_id
                diagnoses = list(diagnoses_collection.find({'patient_id': patient['_id']}).sort('created_at', -1))
                print(f"Found {len(diagnoses)} diagnoses by patient_id")
        
        # If still no diagnoses, try to find by phone number
        if not diagnoses:
            patient = patients_collection.find_one({'email': patient_email})
            if patient and patient.get('phone'):
                # Find diagnoses by patient phone
                diagnoses = list(diagnoses_collection.find({'patient_phone': patient['phone']}).sort('created_at', -1))
                print(f"Found {len(diagnoses)} diagnoses by patient_phone")

        unique_doctors = {}
        for d in diagnoses:
            doc_email = d.get('doctor_email')
            if not doc_email:
                continue
            if doc_email not in unique_doctors:
                unique_doctors[doc_email] = {
                    'doctor_email': doc_email,
                    'doctor_name': d.get('doctor_name', 'Doctor'),
                    'last_diagnosis': d.get('disease_name', ''),
                    'last_diagnosis_date': d['created_at'].isoformat(),
                    'report_id': d.get('report_id', '')
                }
            else:
                # Keep the most recent
                if d['created_at'].isoformat() > unique_doctors[doc_email]['last_diagnosis_date']:
                    unique_doctors[doc_email]['last_diagnosis'] = d.get('disease_name', '')
                    unique_doctors[doc_email]['last_diagnosis_date'] = d['created_at'].isoformat()

        doctors_list = list(unique_doctors.values())
        doctors_list.sort(key=lambda x: x['last_diagnosis_date'], reverse=True)
        
        print(f"Returning {len(doctors_list)} unique doctors for patient {patient_email}")
        return jsonify({'success': True, 'doctors': doctors_list})
    except Exception as e:
        print(f"Error fetching chat doctors: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/debug/session', methods=['GET'])
def debug_session():
    """Debug endpoint to check session data"""
    return jsonify({
        'session_data': dict(session),
        'user_email': session.get('email'),
        'user_role': session.get('role'),
        'user_name': session.get('name')
    })

@app.route('/api/debug/diagnoses', methods=['GET'])
def debug_diagnoses():
    """Debug endpoint to check diagnoses data"""
    if 'email' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        user_email = session['email']
        user_role = session['role']
        
        if user_role == 'doctor':
            # Get diagnoses by this doctor
            diagnoses = list(diagnoses_collection.find({'doctor_email': user_email}).limit(10))
        else:
            # Get diagnoses for this patient
            diagnoses = list(diagnoses_collection.find({'patient_email': user_email}).limit(10))
        
        # Convert ObjectIds to strings
        for d in diagnoses:
            d['_id'] = str(d['_id'])
            d['patient_id'] = str(d['patient_id'])
            d['created_at'] = d['created_at'].isoformat()
        
        return jsonify({
            'success': True,
            'user_email': user_email,
            'user_role': user_role,
            'diagnoses_count': len(diagnoses),
            'diagnoses': diagnoses
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/messages', methods=['GET'])
def get_messages():
    if 'email' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    room_id = request.args.get('room_id')
    if not room_id:
        return jsonify({'success': False, 'error': 'Missing room_id'}), 400
    try:
        docs = list(messages_collection.find({'room_id': room_id}).sort('timestamp', 1).limit(200))
        for m in docs:
            m['_id'] = str(m['_id'])
            m['timestamp'] = m['timestamp'].isoformat()
        return jsonify({'success': True, 'messages': docs})
    except Exception as e:
        print(f"Error fetching messages: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# Socket.IO events
@socketio.on('join')
def handle_join(data):
    room_id = data.get('room_id')
    if not room_id:
        print("Join request missing room_id")
        return
    print(f"User joining room: {room_id}")
    join_room(room_id)
    emit('system', {'message': 'Joined room', 'room_id': room_id})
    print(f"User successfully joined room: {room_id}")

@socketio.on('leave')
def handle_leave(data):
    room_id = data.get('room_id')
    if not room_id:
        print("Leave request missing room_id")
        return
    print(f"User leaving room: {room_id}")
    leave_room(room_id)
    print(f"User successfully left room: {room_id}")

@socketio.on('chat_message')
def handle_chat_message(data):
    try:
        room_id = data.get('room_id')
        text = data.get('text', '').strip()
        sender_email = data.get('sender_email')
        sender_role = data.get('sender_role')
        
        print(f"=== CHAT MESSAGE DEBUG ===")
        print(f"Room ID: {room_id}")
        print(f"Text: {text}")
        print(f"Sender: {sender_email} ({sender_role})")
        print(f"========================")
        
        if not room_id or not text or not sender_email:
            print(f"Missing required data: room_id={room_id}, text={text}, sender_email={sender_email}")
            return
            
        message_doc = {
            'room_id': room_id,
            'text': text,
            'sender_email': sender_email,
            'sender_role': sender_role,
            'timestamp': datetime.now()
        }
        messages_collection.insert_one(message_doc)
        print(f"Message saved to database with ID: {message_doc['_id']}")
        
        # Broadcast to room
        emit('chat_message', {
            'room_id': room_id,
            'text': text,
            'sender_email': sender_email,
            'sender_role': sender_role,
            'timestamp': message_doc['timestamp'].isoformat()
        }, room=room_id)
        print(f"Message broadcasted to room: {room_id}")
        
    except Exception as e:
        print(f"Error handling chat_message: {e}")
        import traceback
        traceback.print_exc()

@socketio.on('typing')
def handle_typing(data):
    room_id = data.get('room_id')
    if room_id:
        emit('typing', data, room=room_id)

@socketio.on('stop_typing')
def handle_stop_typing(data):
    room_id = data.get('room_id')
    if room_id:
        emit('stop_typing', data, room=room_id)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8888)
