from flask import Flask, request, session, render_template, redirect, jsonify, send_from_directory
from functools import wraps
import random
import logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from limits.errors import RateLimitExceeded


app = Flask(__name__)
app.secret_key = "ctf-secret"

# Logger
logging.basicConfig(level=logging.INFO)

# Limiter configuration
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per minute"]  # limites générales (peu strictes)
)
limiter.init_app(app)

USER_EMAIL = "cisco@dataprotect.ma"
USER_PASSWORD = "password123"

# ------------------ Gestion des erreurs ------------------

@app.errorhandler(429)
def ratelimit_handler(e):
    return "⛔ Trop de tentatives. Réessaye dans quelques minutes.", 429
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
        return "Identifiants invalides", 401
    return render_template("login.html")

@app.route("/otp")
@login_required
def otp():
    return render_template("otp.html")

@app.route("/api/send_otp")
@login_required
def send_otp():
    otp = str(random.randint(10000000, 99999999))  # 🔐 OTP à 8 chiffres
    session['otp'] = otp
    return jsonify({
        "status": "otp_sent",
        "otp": otp  # 💡 Affiché ici uniquement pour test/demo
    })

@app.route("/verify_otp", methods=["POST"])
@login_required
@limiter.limit("5 per minute")  # 🔒 Limite stricte pour OTP
def verify_otp():
    submitted = request.form.get("otp")
    if submitted == session.get("otp"):
        session['otp_verified'] = True
        return redirect("/dashboard")
    logging.info(f"❌ OTP invalide tenté depuis {request.remote_addr}")
    return "OTP invalide", 403

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
