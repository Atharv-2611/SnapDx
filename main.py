from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from disease_prediction import predictor
from datetime import datetime
import json
import numpy as np
import os

# LangChain + Gemini (Google Generative AI)
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
except Exception as _:
    ChatGoogleGenerativeAI = None
    SystemMessage = None
    HumanMessage = None
    AIMessage = None

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
ai_messages_collection = db["ai_messages"]


def build_room_id(doctor_email: str, patient_key: str) -> str:
    """Create a stable room id between doctor and patient.
    patient_key should be email if available, else phone, else patient_id string.
    """
    return f"{doctor_email.strip().lower()}__{patient_key.strip().lower()}"


def get_llm():
    """Return a configured LangChain Chat model for Gemini. Lazy init to avoid import errors when not installed."""
    if ChatGoogleGenerativeAI is None:
        raise RuntimeError("LangChain Google Generative AI is not installed. Please install 'langchain-google-genai'.")
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise RuntimeError("Missing GOOGLE_API_KEY environment variable for Gemini.")
    # Instantiate model (lightweight client; safe to create per call)
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        temperature=0.3,
        max_output_tokens=800,
    )

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
    return render_template("paitent/chat.html", user_email=session.get('email'))

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


@app.route("/api/ai/start", methods=["POST"])
def ai_start():
    """Start an AI consultation. Optionally provide report_id. Returns conversation_id and optional report_data.

    Body (optional): { "report_id": "SNAP..." }
    """
    if 'email' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    try:
        data = request.get_json(force=True)
        report_id = (data or {}).get('report_id', '').strip() if data is not None else ''
        requester_email = session.get('email')

        if not report_id:
            # General AI chat without report context
            conversation_id = f"ai__{(requester_email or 'guest').strip().lower()}__general"
            return jsonify({'success': True, 'conversation_id': conversation_id})

        # Report-based context
        diagnosis = diagnoses_collection.find_one({'report_id': report_id})
        if not diagnosis:
            return jsonify({'success': False, 'error': 'Report not found'}), 404

        # Optional: ensure the requesting patient matches the diagnosis patient (if email exists)
        diagnosis_patient_email = diagnosis.get('patient_email')
        if diagnosis_patient_email and requester_email and diagnosis_patient_email.lower() != requester_email.lower():
            return jsonify({'success': False, 'error': 'Report does not belong to this account'}), 403

        # Fetch patient details if available
        patient_doc = None
        try:
            if diagnosis.get('patient_id'):
                patient_doc = patients_collection.find_one({'_id': diagnosis['patient_id']})
        except Exception:
            patient_doc = None

        # Build report data for UI
        patient_name = diagnosis.get('patient_name') or (patient_doc or {}).get('name') or 'Patient'
        patient_age = (patient_doc or {}).get('age', '')
        patient_gender = (patient_doc or {}).get('gender', '')
        primary_diagnosis = diagnosis.get('disease_name') or diagnosis.get('disease_type', '')
        confidence = diagnosis.get('confidence_percentage') or diagnosis.get('probability') or 0
        try:
            confidence_int = int(round(float(confidence)))
        except Exception:
            confidence_int = 0
        severity = (
            'Mild' if confidence_int < 60 else 'Moderate' if confidence_int < 85 else 'Severe'
        )

        report_data = {
            'patientName': patient_name,
            'patientAge': patient_age,
            'patientGender': patient_gender,
            'primaryDiagnosis': primary_diagnosis,
            'confidence': confidence_int,
            'severity': severity,
            'detectedConditions': [],
            'keyFindings': [],
            'treatmentSuggestions': [],
            'precautions': [],
            'medications': [],
        }

        conversation_id = f"ai__{(requester_email or 'guest').strip().lower()}__{report_id.strip().lower()}"

        return jsonify({'success': True, 'conversation_id': conversation_id, 'report_data': report_data})
    except Exception as e:
        print(f"AI start error: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@app.route("/api/ai/messages", methods=["GET"]) 
def ai_get_messages():
    """Fetch AI chat history for a conversation_id."""
    if 'email' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    conversation_id = request.args.get('conversation_id', '').strip()
    if not conversation_id:
        return jsonify({'success': False, 'error': 'Missing conversation_id'}), 400
    try:
        docs = list(ai_messages_collection.find({'conversation_id': conversation_id}).sort('timestamp', 1).limit(200))
        for d in docs:
            d['_id'] = str(d['_id'])
            d['timestamp'] = d['timestamp'].isoformat()
        return jsonify({'success': True, 'messages': docs})
    except Exception as e:
        print(f"Error fetching AI messages: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@app.route("/api/ai/message", methods=["POST"])
def ai_message():
    """Send a user message and get AI response via LangChain + Gemini. Persists both sides to MongoDB.

    Expected body: { "conversation_id": str, "message": str }
    """
    if 'email' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    try:
        payload = request.get_json(force=True)
        conversation_id = (payload or {}).get('conversation_id', '').strip()
        user_message_text = (payload or {}).get('message', '').strip()
        if not conversation_id or not user_message_text:
            return jsonify({'success': False, 'error': 'Missing conversation_id or message'}), 400

        # Persist user message
        user_msg_doc = {
            'conversation_id': conversation_id,
            'sender': 'user',
            'sender_email': session.get('email'),
            'text': user_message_text,
            'timestamp': datetime.now(),
        }
        ai_messages_collection.insert_one(user_msg_doc)

        # Extract report_id from conversation_id convention
        try:
            _, email_part, report_id_part = conversation_id.split('__', 2)
            report_id = report_id_part.upper()
        except Exception:
            report_id = ''

        # Fetch diagnosis context for system prompt
        diagnosis = diagnoses_collection.find_one({'report_id': report_id}) if report_id else None
        patient_doc = None
        try:
            if diagnosis and diagnosis.get('patient_id'):
                patient_doc = patients_collection.find_one({'_id': diagnosis['patient_id']})
        except Exception:
            patient_doc = None

        # Compose system prompt with available context
        system_context_lines = [
            "You are SnapDx AI Assistant. Provide empathetic, evidence-based health information.",
            "Do not provide a diagnosis. Encourage follow-up with their doctor.",
        ]
        if diagnosis:
            system_context_lines.append("-- PATIENT & REPORT CONTEXT --")
            if patient_doc:
                system_context_lines.append(f"Name: {patient_doc.get('name', diagnosis.get('patient_name', 'Patient'))}")
                if patient_doc.get('age'):
                    system_context_lines.append(f"Age: {patient_doc.get('age')}")
                if patient_doc.get('gender'):
                    system_context_lines.append(f"Gender: {patient_doc.get('gender')}")
            else:
                system_context_lines.append(f"Name: {diagnosis.get('patient_name', 'Patient')}")
            primary_dx = diagnosis.get('disease_name') or diagnosis.get('disease_type') or ''
            if primary_dx:
                system_context_lines.append(f"Primary diagnosis: {primary_dx}")
            if diagnosis.get('confidence_percentage') is not None:
                system_context_lines.append(f"Confidence: {diagnosis.get('confidence_percentage')}%")

        system_prompt = "\n".join(system_context_lines)

        # Build message sequence from recent history
        history_msgs = list(ai_messages_collection.find({'conversation_id': conversation_id}).sort('timestamp', 1).limit(10))
        chat_messages = [SystemMessage(content=system_prompt)]
        for m in history_msgs:
            if m.get('sender') == 'user':
                chat_messages.append(HumanMessage(content=m.get('text', '')))
            elif m.get('sender') == 'ai':
                chat_messages.append(AIMessage(content=m.get('text', '')))
        # Add the current user message last (already in history, but include explicitly to the model)
        if not history_msgs or history_msgs[-1].get('text') != user_message_text:
            chat_messages.append(HumanMessage(content=user_message_text))

        # Call Gemini via LangChain
        try:
            llm = get_llm()
            ai_response_message = llm.invoke(chat_messages)
            ai_text = getattr(ai_response_message, 'content', '') or ''
            if not ai_text:
                ai_text = "I'm here to help. Could you please clarify your question?"
        except Exception as e:
            print(f"Gemini call failed: {e}")
            ai_text = (
                "I'm having trouble reaching my AI service right now. Please try again later, "
                "and contact your doctor for urgent concerns."
            )

        # Persist AI message
        ai_msg_doc = {
            'conversation_id': conversation_id,
            'sender': 'ai',
            'text': ai_text,
            'timestamp': datetime.now(),
        }
        ai_messages_collection.insert_one(ai_msg_doc)

        return jsonify({'success': True, 'response': ai_text})
    except Exception as e:
        print(f"AI message error: {e}")
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
        # Get all diagnoses for the logged-in doctor
        diagnoses = list(diagnoses_collection.find(
            {'doctor_email': session['email']}
        ).sort('created_at', -1))
        
        print(f"Found {len(diagnoses)} diagnoses for doctor {session['email']}")
        
        # Group by phone number to get unique patients
        unique_patients = {}
        for diagnosis in diagnoses:
            # Try to get phone from diagnosis first, then from patient record
            phone = diagnosis.get('patient_phone', '')
            
            # If no phone in diagnosis, try to get from patient record
            if not phone:
                patient = patients_collection.find_one({'_id': diagnosis['patient_id']})
                if patient:
                    phone = patient.get('phone', '')
            
            # Use patient_id as fallback if no phone available
            if not phone:
                phone = f"patient_{str(diagnosis['patient_id'])}"
            
            if phone not in unique_patients:
                # Get patient details from patients collection
                patient = patients_collection.find_one({'_id': diagnosis['patient_id']})
                if patient:
                    unique_patients[phone] = {
                        'patient_id': str(patient['_id']),
                        'name': patient.get('name', 'Unknown Patient'),
                        'phone': phone,
                        'email': patient.get('email', ''),
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
                    unique_patients[phone] = {
                        'patient_id': str(diagnosis['patient_id']),
                        'name': diagnosis.get('patient_name', 'Unknown Patient'),
                        'phone': phone,
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
            elif phone in unique_patients:
                # Increment diagnosis count for existing patient
                unique_patients[phone]['total_diagnoses'] += 1
                
                # Update with more recent diagnosis if this one is newer
                current_date = diagnosis['created_at']
                existing_date = datetime.fromisoformat(unique_patients[phone]['last_diagnosis_date'].replace('Z', '+00:00'))
                if current_date > existing_date:
                    unique_patients[phone].update({
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
        
        print(f"Returning {len(patients_list)} unique patients")
        
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
        # Fetch diagnoses where this patient's email was recorded
        diagnoses = list(diagnoses_collection.find({'patient_email': patient_email}).sort('created_at', -1))

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
        return jsonify({'success': True, 'doctors': doctors_list})
    except Exception as e:
        print(f"Error fetching chat doctors: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

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
        return
    join_room(room_id)
    emit('system', {'message': 'Joined room', 'room_id': room_id})

@socketio.on('leave')
def handle_leave(data):
    room_id = data.get('room_id')
    if not room_id:
        return
    leave_room(room_id)

@socketio.on('chat_message')
def handle_chat_message(data):
    try:
        room_id = data.get('room_id')
        text = data.get('text', '').strip()
        sender_email = data.get('sender_email')
        sender_role = data.get('sender_role')
        if not room_id or not text or not sender_email:
            return
        message_doc = {
            'room_id': room_id,
            'text': text,
            'sender_email': sender_email,
            'sender_role': sender_role,
            'timestamp': datetime.now()
        }
        messages_collection.insert_one(message_doc)
        # Broadcast to room
        emit('chat_message', {
            'room_id': room_id,
            'text': text,
            'sender_email': sender_email,
            'sender_role': sender_role,
            'timestamp': message_doc['timestamp'].isoformat()
        }, room=room_id)
    except Exception as e:
        print(f"Error handling chat_message: {e}")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8888)
