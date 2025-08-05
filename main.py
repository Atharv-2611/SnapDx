from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder="templates")
app.secret_key = 'supersecretkey'

# MongoDB setup
client = MongoClient("mongodb+srv://atharv:$4Jeu67EW8DkJsA@snapdx.1ohabx8.mongodb.net/?retryWrites=true&w=majority&appName=snapdx")
db = client["snapdx"]
users_collection = db["users"]

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
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        if users_collection.find_one({"email": email, "role": role}):
            flash('User already exists with this email and role.')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        users_collection.insert_one({
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
    return render_template("doctor/home.html")

@app.route("/doctor/about")
def doctor_about():
    return render_template("doctor/about.html")

@app.route("/doctor/chat")
def doctor_chat():
    return render_template("doctor/chat.html")

@app.route("/doctor/diagnose")
def doctor_diagnose():
    return render_template("doctor/diagnose.html")

@app.route("/doctor/history")
def doctor_history():
    return render_template("doctor/history.html")

@app.route("/doctor/working")
def doctor_working():
    return render_template("doctor/how_it_works.html")

@app.route("/patient/chatbot")
def paitent_chatbot():
    return render_template("paitent/chatbot.html")

@app.route("/patient/chat")
def paitent_chat():
    return render_template("paitent/chat.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0",port=8888)
