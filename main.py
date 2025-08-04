from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__, template_folder="templates")
app.secret_key = 'supersecretkey'

# Simulated user database
users = {
    'doctor@example.com': {'password': 'doc123', 'role': 'doctor'},
    'patient@example.com': {'password': 'pat123', 'role': 'patient'}
}

@app.route('/')
def index():
    return render_template("landing.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        user = users.get(email)

        if user and user['password'] == password and user['role'] == role:
            session['email'] = email
            session['role'] = role
            if role == 'doctor':
                return redirect(url_for('doctor_home'))
            else:
                return redirect(url_for('patient_chatbot'))
        else:
            flash('Invalid credentials or role mismatch')
            return redirect(url_for('login'))

    return render_template('login.html')

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
