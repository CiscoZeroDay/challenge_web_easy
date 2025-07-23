from flask import Flask, request, session, render_template, redirect, jsonify, send_from_directory
from functools import wraps
import random
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
app.secret_key = "ctf-secret"


# Nouvelle syntaxe correcte pour flask-limiter >= 3.x
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per minute"]
)
limiter.init_app(app)

USER_EMAIL = "cisco@dataprotect.ma"
USER_PASSWORD = "password123"

# ------------------ Décorateurs de sécurité ------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

def otp_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/")
        if not session.get("otp_verified"):
            return redirect("/otp")
        return f(*args, **kwargs)
    return decorated_function

# ------------------ Routes principales ------------------

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if email == USER_EMAIL and password == USER_PASSWORD:
            session.clear()  
            session['logged_in'] = True
            return redirect("/otp")
        return "Invalid credentials", 401
    return render_template("login.html")

@app.route("/otp")
@login_required
def otp():
    return render_template("otp.html")

@app.route("/api/send_otp")
@login_required
def send_otp():
    otp = str(random.randint(1000, 9999))  
    session['otp'] = otp
    return jsonify({
        "status": "otp_sent",
        "otp": otp  
    })

@app.route("/verify_otp", methods=["POST"])
@login_required
def verify_otp():
    submitted = request.form.get("otp")
    if submitted == session.get("otp"):
        session['otp_verified'] = True
        return redirect("/dashboard")
    return "Invalid OTP", 403

@app.route("/dashboard")
@otp_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/download_rapport")
@otp_required
def download_rapport():
    return send_from_directory(directory="files", path="rapport_de_Stage.pdf", as_attachment=True)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
