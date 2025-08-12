from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from disease_prediction import predictor
from datetime import datetime
import json
import numpy as np

app = Flask(__name__, template_folder="templates")
app.secret_key = 'supersecretkey'

# MongoDB setup
client = MongoClient("mongodb+srv://Arman:Motor9-Jumbo5-Antiquely7-Edition6-Undergrad7@snapdx.2ihkj4k.mongodb.net/?retryWrites=true&w=majority&appName=SnapDx")
db = client["snapdx"]
users_collection = db["users"]
patients_collection = db["patients"]
diagnoses_collection = db["diagnoses"]

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
    return render_template("doctor/home.html", user_name=user_name)

@app.route("/doctor/about")
def doctor_about():
    if 'email' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))
    user_name = session.get('name', 'Doctor')
    return render_template("doctor/about.html", user_name=user_name)

@app.route("/doctor/chat")
def doctor_chat():
    if 'email' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))
    user_name = session.get('name', 'Doctor')
    return render_template("doctor/chat.html", user_name=user_name)

@app.route("/doctor/diagnose")
def doctor_diagnose():
    if 'email' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))
    user_name = session.get('name', 'Doctor')
    return render_template("doctor/diagnose.html", user_name=user_name)

@app.route("/doctor/history")
def doctor_history():
    if 'email' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))
    user_name = session.get('name', 'Doctor')
    return render_template("doctor/history.html", user_name=user_name)

@app.route("/doctor/working")
def doctor_working():
    if 'email' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))
    user_name = session.get('name', 'Doctor')
    return render_template("doctor/how_it_works.html", user_name=user_name)

@app.route("/patient/chatbot")
def paitent_chatbot():
    return render_template("paitent/chatbot.html")

@app.route("/patient/chat")
def paitent_chat():
    return render_template("paitent/chat.html")

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
                'created_by': patient_data['created_by'],
                'created_at': patient_data['created_at'].isoformat()
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Diagnosis error: {e}")
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


if __name__ == "__main__":
    app.run(host="0.0.0.0",port=8888)
